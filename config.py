from decimal import Decimal
from pathlib import Path

# Tasa de interés mensual por defecto (12%)
DEFAULT_MONTHLY_RATE = Decimal("0.12")

# Factores para cálculo de número de cuotas
WEEKS_PER_MONTH = 4
FORTNIGHTS_PER_MONTH = 2

# Rutas de base de datos y recursos
BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "data"
DATABASE_NAME = "creditos.db"
DATABASE_PATH = DATABASE_DIR / DATABASE_NAME
ASSETS_DIR = BASE_DIR / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"
ICON_PNG_PATH = ASSETS_DIR / "icon.png"

