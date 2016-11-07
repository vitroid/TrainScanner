all: gui4_ja.ts gui4_ja.qm
gui4_ja.ts: gui4.pro gui4.py
	pylupdate4 gui4.pro
	open /usr/local/Cellar/qt/4.8.7_2/Linguist.app
gui4_ja.qm:gui4_ja.ts
	lrelease gui4.pro
