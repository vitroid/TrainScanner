all: gui2_ja.ts gui2_ja.qm
gui2_ja.ts: gui2.pro gui2.py
	pylupdate4 gui2.pro
	open /usr/local/Cellar/qt/4.8.7_2/Linguist.app
gui2_ja.qm:gui2_ja.ts
	lrelease gui2.pro
