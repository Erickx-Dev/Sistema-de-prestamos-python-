import sqlite3
from credito_app import config


def get_db_path() -> str:
    """Obtiene la ruta de la base de datos, creando el directorio si no existe."""
    db_path = config.DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Crea y retorna una conexión a la base de datos."""
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn
