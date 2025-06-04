# -*- mode: python ; coding: utf-8 -*-

import certifi
block_cipher = None

a = Analysis(
    ['llamate/__main__.py'],  # New entry point
    pathex=[],
    binaries=[],
    datas=[
        ('llamate/data/model_aliases.py', 'llamate/data'),  # Include model aliases data
        (certifi.where(), 'certifi'),
    ],
    hiddenimports=[
        'llamate.cli.commands.config',
        'llamate.cli.commands.init',
        'llamate.cli.commands.model',
        'llamate.cli.commands.serve',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='llamate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,  # Create a single file executable
)
