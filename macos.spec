# -*- mode: python -*-

block_cipher = None


a = Analysis(['gui5.py'],
             pathex=['/Users/matto/github/TrainScanner'],
             binaries=[('/usr/local/Cellar/opencv3/HEAD-88ef8c9_4/lib/libopencv_imgcodecs.3.1.0.dylib', 'libopencv_imgcodecs.3.1.0.dylib')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             datas=[ ('i18n/gui5_ja.qm', 'i18n') ],
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
