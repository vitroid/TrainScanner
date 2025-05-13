all: trainscanner_ja.ts trainscanner_ja.qm trainscanner_fr.ts trainscanner_fr.qm

trainscanner_%.ts: ../trainscanner_gui.py ../converter/gui.py
	pylupdate6 --ts $@ $^

linguist:
	/usr/local/Cellar/qt/6.9.0/bin/Linguist trainscanner_ja.ts
	/usr/local/Cellar/qt/6.9.0/bin/Linguist trainscanner_fr.ts

qm: trainscanner_ja.qm trainscanner_fr.qm

trainscanner_%.qm: trainscanner_%.ts
	/usr/local/Cellar/qt/6.9.0/bin/lrelease trainscanner_$*.ts
