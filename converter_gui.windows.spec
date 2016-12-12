# -*- mode: python -*-

block_cipher = None


a = Analysis(['converter_gui.py'],
             pathex=['C:\\Users\\riron\\Documents\\GitHub\\TrainScanner'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='TSConverter',
          debug=False,
          strip=False,
          upx=True,
          icon="TrainScanner.ico",
          console=False )
