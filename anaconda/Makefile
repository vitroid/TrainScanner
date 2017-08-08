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
HASH=py36h6a30d30_0
convert:
	conda convert --platform all /Users/matto/anaconda/conda-bld/osx-64/trainscanner-0.11-$(HASH).tar.bz2 -o convert/

upload:
#	~/anaconda/bin/anaconda login
	~/anaconda/bin/anaconda upload convert/win-64/trainscanner-0.11-$(HASH).tar.bz2
	~/anaconda/bin/anaconda upload convert/linux-64/trainscanner-0.11-$(HASH).tar.bz2
	~/anaconda/bin/anaconda upload /Users/matto/anaconda/conda-bld/osx-64/trainscanner-0.11-$(HASH).tar.bz2
	echo restart the anaconda navigator
clean:
	rm *~ */*~

# Make environment for Anaconda
anaconda-ubuntu:
	export PATH=~/anaconda3/bin:$$PATH
	conda create -yn trainscanner
	source activate trainscanner
	conda install -c vitroid trainscanner
	conda install -c menpo opencv3
	conda install pyqt=5.6
	pip install sk-video tiledimage
	conda env export > trainscanner-anaconda-ubuntu.yml
	source deactivate
anaconda-mac:
	export PATH=~/anaconda/bin:$$PATH
	conda create -yn trainscanner python=3.5
	source activate trainscanner
	conda install -c vitroid -y trainscanner
	conda install -c menpo -y opencv3
	conda install -y pyqt=5.6
	pip install sk-video tiledimage
	conda env export > trainscanner-anaconda-mac.yml
	source deactivate

