import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from credito_app.config import BACKUPS_DIR
from credito_app.database.schema import crear_tablas
from credito_app.modules.excepciones import CrediNodaError

SQLITE_HEADER = b"SQLite format 3\x00"
REQUIRED_TABLES = {"clientes", "creditos", "cuotas", "pagos"}


class BackupError(CrediNodaError):
    """Excepción para errores durante la creación, validación o restauración de copias de seguridad."""

    pass


class BackupService:
    """
    Servicio para gestionar copias de seguridad (backups) y restauración en caliente
    de la base de datos SQLite del sistema CrediNoda.
    """

    def __init__(self, conn: sqlite3.Connection, backups_dir: Optional[Path] = None):
        self.conn = conn
        self.backups_dir = Path(backups_dir) if backups_dir else BACKUPS_DIR
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def crear_backup(self, destino: Optional[Path | str] = None, prefijo: str = "creditos_backup") -> Path:
        """
        Genera una copia de seguridad consistente en caliente de la base de datos activa
        utilizando la API nativa sqlite3.Connection.backup().
        """
        try:
            if destino is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                ruta_destino = self.backups_dir / f"{prefijo}_{timestamp}.db"
            else:
                ruta_destino = Path(destino)
                if ruta_destino.suffix.lower() != ".db":
                    ruta_destino = ruta_destino.with_suffix(".db")

            ruta_destino.parent.mkdir(parents=True, exist_ok=True)

            # Confirmar cambios pendientes antes de respaldar
            self.conn.commit()

            dest_conn = sqlite3.connect(str(ruta_destino))
            try:
                self.conn.backup(dest_conn)
            finally:
                dest_conn.close()

            return ruta_destino
        except Exception as e:
            raise BackupError(f"No se pudo crear la copia de seguridad: {e}") from e

    @staticmethod
    def validar_archivo_backup(ruta_archivo: Path | str) -> bool:
        """
        Verifica que el archivo indicado sea una base de datos SQLite íntegra
        y contenga las tablas requeridas por CrediNoda.
        """
        ruta = Path(ruta_archivo)
        if not ruta.exists() or not ruta.is_file():
            raise BackupError("El archivo de copia de seguridad no existe.")

        if ruta.stat().st_size < len(SQLITE_HEADER):
            raise BackupError("El archivo seleccionado está vacío o no es una base de datos SQLite válida.")

        with open(ruta, "rb") as f:
            header = f.read(len(SQLITE_HEADER))
        if header != SQLITE_HEADER:
            raise BackupError("El archivo seleccionado no tiene un formato SQLite válido.")

        check_conn = sqlite3.connect(str(ruta))
        try:
            cursor = check_conn.execute("PRAGMA integrity_check")
            resultado = cursor.fetchone()
            if not resultado or resultado[0] != "ok":
                raise BackupError("El archivo de base de datos está dañado (falló PRAGMA integrity_check).")

            tablas_cursor = check_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas_encontradas = {row[0] for row in tablas_cursor.fetchall()}
            faltantes = REQUIRED_TABLES - tablas_encontradas
            if faltantes:
                tablas_str = ", ".join(sorted(faltantes))
                raise BackupError(f"La base de datos no pertenece a CrediNoda (faltan tablas: {tablas_str}).")
        except BackupError:
            raise
        except Exception as e:
            raise BackupError(f"Error al inspeccionar el archivo de respaldo: {e}") from e
        finally:
            check_conn.close()

        return True

    def restaurar_backup(self, origen: Path | str) -> Path:
        """
        Valida un archivo de respaldo, genera una copia preventiva del estado actual
        y restaura los datos sobre la conexión activa en caliente.
        Retorna la ruta del respaldo preventivo generado antes de sobrescribir.
        """
        ruta_origen = Path(origen)
        self.validar_archivo_backup(ruta_origen)

        # 1. Crear respaldo preventivo automático antes de sobrescribir
        respaldo_preventivo = self.crear_backup(prefijo="pre_restauracion")

        # 2. Restaurar en caliente sobre la conexión activa
        try:
            self.conn.commit()
            # Desactivar temporalmente foreign_keys durante el volcado de páginas
            self.conn.execute("PRAGMA foreign_keys = OFF")
            src_conn = sqlite3.connect(str(ruta_origen))
            try:
                src_conn.backup(self.conn)
            finally:
                src_conn.close()

            self.conn.execute("PRAGMA foreign_keys = ON")
            # Asegurar migraciones de esquema (ej. columna en_mora)
            crear_tablas(self.conn)
            self.conn.commit()
            return respaldo_preventivo
        except Exception as e:
            raise BackupError(f"Error durante la restauración de la base de datos: {e}") from e

    def listar_backups(self) -> list[dict]:
        """
        Retorna la lista de archivos .db en el directorio de backups,
        ordenados del más reciente al más antiguo.
        """
        if not self.backups_dir.exists():
            return []

        archivos = []
        for archivo in self.backups_dir.glob("*.db"):
            if archivo.is_file():
                stat = archivo.stat()
                archivos.append(
                    {
                        "nombre": archivo.name,
                        "ruta": archivo,
                        "fecha": datetime.fromtimestamp(stat.st_mtime),
                        "tamano_kb": round(stat.st_size / 1024, 1),
                    }
                )
        archivos.sort(key=lambda x: x["fecha"], reverse=True)
        return archivos
