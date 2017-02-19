all: trainscanner_ja.ts trainscanner_ja.qm
trainscanner_ja.ts: trainscanner.pro ../trainscanner/trainscanner_gui.py ../ts_conv/converter_gui.py
	pylupdate4 trainscanner.pro
	open /usr/local/Cellar/qt/4.8.7_2/Linguist.app
%_ja.qm:%_ja.ts
	lrelease $*.pro
