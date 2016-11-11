all: gui5_ja.ts gui5_ja.qm
gui5_ja.ts: gui5.pro gui5.py
	pylupdate4 gui5.pro
	open /usr/local/Cellar/qt/4.8.7_2/Linguist.app
gui5_ja.qm:gui5_ja.ts
	lrelease gui5.pro

#for mac and windows
macapp:
	pyinstaller --windowed --noconfirm -i trainscanner.icns --name TrainScanner gui5.py
#icons are generated at /Users/matto/github/TrainScanner/trainscanner.icns
