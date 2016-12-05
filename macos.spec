# -*- mode: python -*-

block_cipher = None


a = Analysis(['trainscanner_gui.py'],
             pathex=['/Users/matto/github/TrainScanner'],
             binaries=None, #[('/usr/local/lib/libopencv_videoio.3.1.dylib','libopencv_videoio.3.1.dylib')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             datas=[ ('i18n/trainscanner_ja.qm', 'i18n') ],
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='TrainScanner',
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='trainscanner.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='TrainScanner')
app = BUNDLE(coll,
             name='TrainScanner.app',
             icon='trainscanner.icns',
             bundle_identifier='jp.vitroid.trainscanner')
