# -*- mode: python ; coding: utf-8 -*-
# Application Windows d'IUC, compilée par PyInstaller dans dist/IUC (un dossier), puis
# installée par iuc.iss. Prérequis : interface compilée (npm run build dans frontend/).
#   pyinstaller --noconfirm packaging/IUC.spec
# Le pilote de Playwright est embarqué (hook de pyinstaller-hooks-contrib), pas Chromium :
# l'application utilise Chrome ou Edge déjà installés (app/desktop.py).

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
FRONTEND_DIST = ROOT / "frontend" / "dist"
if not (FRONTEND_DIST / "index.html").is_file():
    raise SystemExit("Interface non compilée : lance d'abord npm run build dans frontend/.")

a = Analysis(
    [str(ROOT / "packaging" / "iuc_app.py")],
    pathex=[str(ROOT / "backend")],
    # Interface compilée, et icône de la zone de notification (app/tray.py).
    datas=[(str(FRONTEND_DIST), "frontend/dist"), (str(ROOT / "packaging" / "iuc.ico"), ".")],
    # uvicorn charge ses boucles et protocoles par leur nom, pystray son moteur Windows ; app,
    # ses routes et services.
    hiddenimports=collect_submodules("uvicorn")
    + collect_submodules("pystray")
    + collect_submodules("app"),
    excludes=["tkinter", "pytest", "mypy", "ruff", "pip_audit"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IUC",
    icon=str(ROOT / "packaging" / "iuc.ico"),
    # Sans fenêtre de console : l'icône près de l'horloge rouvre l'interface ou quitte IUC.
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="IUC")
