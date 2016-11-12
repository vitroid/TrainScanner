all:

#for mac and windows
macapp:
	#pyinstaller --windowed --noconfirm -i trainscanner.icns --name TrainScanner gui5.py
	pyinstaller --noconfirm TrainScanner.spec
#icons are generated at /Users/matto/github/TrainScanner/trainscanner.icns
maczip:
	cd dist; zip -r trainscanner.x.y.macos.zip TrainScanner.app; md5 trainscanner.x.y.macos.zip | tee trainscanner.x.y.macos.zip.md5
