import sys
from decimal import Decimal
from pathlib import Path

# Tasa de interés mensual por defecto (12%)
DEFAULT_MONTHLY_RATE = Decimal("0.12")

# Factores para cálculo de número de cuotas
WEEKS_PER_MONTH = 4
FORTNIGHTS_PER_MONTH = 2

# Rutas de base de datos y recursos (soporte para ejecución desde fuente y PyInstaller .exe)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = BASE_DIR

DATABASE_DIR = BASE_DIR / "data"
DATABASE_NAME = "creditos.db"
DATABASE_PATH = DATABASE_DIR / DATABASE_NAME

BACKUPS_DIR = BASE_DIR / "backups"
ASSETS_DIR = BUNDLE_DIR / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"
ICON_PNG_PATH = ASSETS_DIR / "icon.png"
