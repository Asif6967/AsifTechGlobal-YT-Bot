# AsifTechGlobal.spec — PyInstaller build specification
# Run: pyinstaller AsifTechGlobal.spec

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Include Flask HTML templates
        ('templates', 'templates'),
        # Include default config files
        ('config.json',       '.'),
        ('oauth_config.json', '.'),
        # Bot files
        ('bot.py',            '.'),
        ('bot_mobile.py',     '.'),
        ('web_panel.py',      '.'),
    ],
    hiddenimports=[
        # Flask ecosystem
        'flask',
        'flask.templating',
        'flask_login',
        'werkzeug',
        'werkzeug.security',
        'werkzeug.middleware.proxy_fix',
        'jinja2',
        'jinja2.ext',
        'markupsafe',
        'click',
        'itsdangerous',
        # Authlib (OAuth)
        'authlib',
        'authlib.integrations.flask_client',
        'authlib.integrations.requests_client',
        'authlib.oauth2',
        'authlib.oauth2.rfc6749',
        'authlib.oauth2.rfc7523',
        'authlib.oidc',
        'authlib.oidc.core',
        # joserfc (authlib.jose replacement)
        'joserfc',
        'joserfc.jwk',
        'joserfc.jwt',
        'joserfc.jwe',
        'joserfc.jws',
        'joserfc.errors',
        'joserfc.registry',
        # Requests (for OAuth HTTP calls)
        'requests',
        'requests.adapters',
        'urllib3',
        'certifi',
        # Database
        'sqlite3',
        # Selenium (bot)
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.common.by',
        'selenium.webdriver.common.keys',
        'selenium.webdriver.common.action_chains',
        'webdriver_manager',
        'webdriver_manager.chrome',
        # Standard library extras
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'threading',
        'pathlib',
        'json',
        'logging',
        'shutil',
        'random',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'cv2',
        'scipy',
        'PyQt5',
        'PyQt6',
    ],
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
    a.zipfiles,
    a.datas,
    [],
    name='AsifTechGlobal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # Keep console window (shows server logs)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,             # Add icon.ico here if you have one
    uac_admin=True,        # Admin rights — firewall rule + mobile access ke liye
)
