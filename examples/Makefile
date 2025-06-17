all: sample.mov.png sample2.mov.png sample3.mov.png sample4.mov.png sample5.mov.png

%.mov.tsconf: %.mov
	cd ..; python -m trainscanner.pass1 --debug  examples/$< -l examples/$<
%.mov.png: %.mov.tsconf
	cd ..; python -m trainscanner.stitch --debug  examples/$*.mov -l examples/$*.mov --file examples/$*.mov.tsconf

distclean:
	-rm -rf *.pngs
	ls | fgrep -v Makefile | grep -v 'mov$$' | xargs rm

