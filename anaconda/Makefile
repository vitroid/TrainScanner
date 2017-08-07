# Script to register trainscanner to the Conda repository
# meta.yaml contains the minimal requirements.
# All the dependencies must be resolved by the Anaconda Environment file trainscanner-anaconda.yml
prepare:
	conda install conda-build
	pip install tiledimage
trainscanner:
	conda skeleton pypi trainscanner
diff:
	touch old2/meta.yaml
	diff -up trainscanner/meta.yaml old2/meta.yaml > meta.diff
	cp old2/trainscanner.png trainscanner
patch:
	patch -p1 trainscanner/meta.yaml < meta.diff 
build:
	conda build trainscanner
convert:
	conda convert --platform all /home/jsmith/miniconda/conda-bld/linux-64/pyinstrument-0.13.1-py27_0.tar.bz2 -o outputdir/

upload:
#	~/anaconda/bin/anaconda login
	~/anaconda/bin/anaconda upload /Users/matto/anaconda/conda-bld/osx-64/trainscanner-0.10-py36hd921793_0.tar.bz2
	echo restart the anaconda navigator
clean:
	rm *~ */*~

