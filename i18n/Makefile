all: gui5_ja.ts gui5_ja.qm
%_ja.ts: %.pro ../%.py
	pylupdate4 $*.pro
	open /usr/local/Cellar/qt/4.8.7_2/Linguist.app
%_ja.qm:%_ja.ts
	lrelease $*.pro
