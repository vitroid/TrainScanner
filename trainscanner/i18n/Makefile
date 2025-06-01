QTPATH=/usr/local/Cellar/qt/6.9.0/bin
SRCS=../trainscanner_gui.py ../preprocess_gui.py ../stitch_gui.py ../converter/gui.py ../converter/hans_style.py ../converter/scroll.py ../converter/rect.py ../converter/helix.py ../converter/movie.py
all: trainscanner_ja.ts trainscanner_fr.ts

trainscanner_%.ts: $(SRCS) Makefile extract.py
	python3 extract.py --ts $@ $(SRCS)


linguist:
	$(QTPATH)/Linguist trainscanner_ja.ts
	$(QTPATH)/Linguist trainscanner_fr.ts

qm: trainscanner_ja.qm trainscanner_fr.qm

trainscanner_%.qm: trainscanner_%.ts
	$(QTPATH)/lrelease trainscanner_$*.ts
