all:

#for mac and windows
macapp:
	#pyinstaller --windowed --noconfirm -i trainscanner.icns --name TrainScanner gui5.py
	pyinstaller --noconfirm TrainScanner.spec
#icons are generated at /Users/matto/github/TrainScanner/trainscanner.icns
