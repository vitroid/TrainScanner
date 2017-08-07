# Script to register trainscanner to the Conda repository
# meta.yaml contains the minimal requirements.
# All the dependencies must be resolved by the Anaconda Environment file trainscanner-anaconda.yml
prepare:
	conda install conda-build
	pip install tiledimage
trainscanner:
	conda skeleton pypi --pypi-url "https://mirror-ord.pypi.io" trainscanner
diff:
	touch old2/meta.yaml
	diff -up trainscanner/meta.yaml old2/meta.yaml > meta.diff
	cp old2/trainscanner.png trainscanner
patch:
	patch -p1 trainscanner/meta.yaml < meta.diff 
build:
	conda build trainscanner
convert:
	conda convert --platform all /Users/matto/anaconda/conda-bld/osx-64/trainscanner-0.11-py36he0c8fd0_0.tar.bz2 -o build/

upload:
#	~/anaconda/bin/anaconda login
	~/anaconda/bin/anaconda upload build/win-64/trainscanner-0.11-py36he0c8fd0_0.tar.bz2
	~/anaconda/bin/anaconda upload build/linux-64/trainscanner-0.11-py36he0c8fd0_0.tar.bz2
	~/anaconda/bin/anaconda upload /Users/matto/anaconda/conda-bld/osx-64/trainscanner-0.11-py36he0c8fd0_0.tar.bz2
	echo restart the anaconda navigator
clean:
	rm *~ */*~

# Make environment for Anaconda
anaconda:
	export PATH=/home/vitroid/anaconda3/bin:$PATH
	conda create -yn trainscanner
	source activate trainscanner
	conda install -c vitroid trainscanner
	conda install -c menpo opencv3
	conda install pyqt=5.6
	pip install sk-video tiledimage
	conda env export > trainscanner-anaconda-ubuntu.yml
	source deactivate

