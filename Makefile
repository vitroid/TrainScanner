#PYTHONEXE=trainscanner_gui.py pass1_gui.py stitch_gui.py shakereduction.py rect.py helix.py hans_style.py film.py add_instruction.py
#PYTHONLIB=canvas.py imagebar.py pass1.py imageselector2.py qrangeslider.py trainscanner.py stitch.py


all: #macapp install #macapp-personally
	echo There is no 'all' to be built for now.

##############################
#  PyPI
##############################
#%.rst: %.md
#	md2rst $<

setup:
	./setup.py build

install:
	./setup.py install

uninstall:
	pip uninstall -y trainscanner

check:
	./setup.py check
	./setup.py sdist bdist_wheel # upload
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*
pypi:
	twine upload dist/*
test1: test1.png
test1.png: test1.tsconf
	./stitch_gui.py @$<
test1.tsconf:
	./pass1_gui.py examples/sample.mov --log test1
distclean:
	-rm -rf dist build *.egg-info __pycache__ *.pyc
	make -C examples distclean
