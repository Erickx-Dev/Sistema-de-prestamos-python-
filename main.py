"""Punto de entrada de la aplicación CrediNoda."""

import sys
from pathlib import Path

# Garantizar que el paquete padre esté disponible al ejecutar directamente o con PyInstaller
_root_dir = str(Path(__file__).resolve().parent.parent)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from credito_app.ui.app import App  # noqa: E402


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
