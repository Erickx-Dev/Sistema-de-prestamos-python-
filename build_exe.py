"""
Script de compilación y empaquetado de CrediNoda para Windows.
Genera:
  1. dist/CrediNoda.exe (Ejecutable único independiente con icono oficial)
  2. dist/CrediNoda_Portable_Windows.zip (Paquete portable listo para distribuir)
"""

import shutil
import subprocess
import sys
from pathlib import Path


def verificar_pyinstaller():
    """Verifica si PyInstaller está instalado; de lo contrario, lo instala."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0.0"])


def compilar_ejecutable():
    verificar_pyinstaller()

    app_dir = Path(__file__).resolve().parent
    workspace_dir = app_dir.parent
    main_script = app_dir / "main.py"
    assets_dir = app_dir / "assets"
    icon_file = assets_dir / "icon.ico"
    dist_dir = app_dir / "dist"
    build_dir = app_dir / "build"

    if not main_script.exists():
        raise FileNotFoundError(f"No se encontró el punto de entrada: {main_script}")

    sep = ";" if sys.platform.startswith("win") else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noconsole",
        "--onefile",
        "--name",
        "CrediNoda",
        "--paths",
        str(workspace_dir),
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        "--specpath",
        str(app_dir),
        "--collect-all",
        "customtkinter",
    ]

    if icon_file.exists():
        cmd.extend(["--icon", str(icon_file)])

    if assets_dir.exists():
        cmd.extend(["--add-data", f"{assets_dir}{sep}assets"])

    cmd.append(str(main_script))

    print("=" * 65)
    print("Compilando CrediNoda.exe con PyInstaller...")
    print("=" * 65)
    subprocess.check_call(cmd)

    exe_path = dist_dir / "CrediNoda.exe"
    if not exe_path.exists():
        raise RuntimeError("La compilación finalizó pero no se encontró dist/CrediNoda.exe")

    # Preparar paquete portable
    portable_dir = dist_dir / "CrediNoda_Portable"
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    portable_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(exe_path, portable_dir / "CrediNoda.exe")

    for sub in ("data", "backups", "comprobantes"):
        folder = portable_dir / sub
        folder.mkdir(exist_ok=True)

    leeme = portable_dir / "LEEME.txt"
    leeme.write_text(
        "============================================================\n"
        "         CrediNoda - Sistema de Gestión de Créditos         \n"
        "============================================================\n\n"
        "INSTRUCCIONES DE USO:\n"
        "1. Ejecute 'CrediNoda.exe' con doble clic.\n"
        "2. La base de datos se guarda automáticamente en la carpeta 'data/creditos.db'.\n"
        "3. Los recibos en PDF se almacenan en la carpeta 'comprobantes/'.\n"
        "4. Las copias de seguridad se almacenan en la carpeta 'backups/'.\n"
        "5. Puede usar el botón 'Copia de Seguridad' en la barra lateral para\n"
        "   respaldar o restaurar su información en cualquier momento.\n",
        encoding="utf-8",
    )

    zip_base = dist_dir / "CrediNoda_Portable_Windows"
    zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=str(portable_dir))

    print("\n" + "=" * 65)
    print("EMPAQUETADO COMPLETADO EXITOSAMENTE")
    print(f" -> Ejecutable: {exe_path}")
    print(f" -> Paquete ZIP Portable: {zip_path}")
    print("=" * 65)
    return exe_path, Path(zip_path)


if __name__ == "__main__":
    compilar_ejecutable()
