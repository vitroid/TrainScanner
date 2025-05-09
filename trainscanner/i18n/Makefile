all: trainscanner_ja.ts trainscanner_ja.qm

trainscanner_ja.ts: ../trainscanner_gui.py ../converter/converter_gui.py
	pylupdate6 --ts $@ ../trainscanner_gui.py ../converter/converter_gui.py

linguist:
	/usr/local/Cellar/qt/6.9.0/bin/Linguist trainscanner_ja.ts

qm: trainscanner_ja.qm

trainscanner_ja.qm: trainscanner_ja.ts
	/usr/local/Cellar/qt/6.9.0/bin/lrelease trainscanner_ja.ts
