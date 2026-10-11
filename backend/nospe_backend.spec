from PyInstaller.utils.hooks import collect_data_files, collect_submodules


hiddenimports = (
    collect_submodules("app")
    + collect_submodules("twain")
    + collect_submodules("zeroconf")
    # WIA-Zugriff über COM (nur Windows-Build): Automation-Module von pywin32
    + ["win32com", "win32com.client", "pythoncom", "pywintypes"]
)
datas = collect_data_files("app") + collect_data_files("twain")


a = Analysis(
    ["run_backend.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="nospe-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
