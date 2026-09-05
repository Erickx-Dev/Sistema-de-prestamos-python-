import sqlite3
from credito_app.database.connection import get_connection, get_db_path

def crear_tablas(conn: sqlite3.Connection) -> None:
    """Crea las tablas de la base de datos si no existen."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL,
            documento TEXT NOT NULL UNIQUE,
            fecha_registro TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS creditos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            capital TEXT NOT NULL,
            tasa_mensual TEXT NOT NULL,
            plazo_meses INTEGER NOT NULL,
            total_intereses TEXT NOT NULL,
            total_pagar TEXT NOT NULL,
            frecuencia_pago TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'ACTIVO',
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cuotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credito_id INTEGER NOT NULL,
            numero_cuota INTEGER NOT NULL,
            fecha_vencimiento TEXT NOT NULL,
            monto TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'PENDIENTE',
            FOREIGN KEY (credito_id) REFERENCES creditos(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credito_id INTEGER NOT NULL,
            cuota_id INTEGER NOT NULL,
            fecha_pago TEXT NOT NULL,
            monto TEXT NOT NULL,
            FOREIGN KEY (credito_id) REFERENCES creditos(id),
            FOREIGN KEY (cuota_id) REFERENCES cuotas(id)
        )
    """)

def inicializar_base_datos(db_path: str | None = None) -> None:
    """Inicializa la base de datos creando las tablas necesarias."""
    conn = get_connection(db_path)
    try:
        crear_tablas(conn)
        conn.commit()
    finally:
        conn.close()
