# Script to register trainscanner to the Conda repository
# meta.yaml contains the minimal requirements.
# All the dependencies must be resolved by the Anaconda Environment file trainscanner-anaconda.yml
prepare:
	conda install conda-build
	pip install tiledimage
trainscanner:
	conda skeleton pypi trainscanner
	cp old/trainscanner.png trainscanner
#diff:
#	cp old/trainscanner.png trainscanner
#	touch old/meta.yaml
#	diff -up trainscanner/meta.yaml old/meta.yaml > meta.diff
patch:
	patch -p1 trainscanner/meta.yaml < meta.diff
build:
	conda build trainscanner
VER=0.12.0-py38h39e3cac_0
CONVERT_BASE=/usr/local/anaconda3
convert:
	conda convert --platform all $(CONVERT_BASE)/conda-bld/osx-64/trainscanner-$(VER).tar.bz2 -o convert/

ANACONDA=anaconda
upload:
#	~/anaconda/bin/anaconda login
	$(ANACONDA) upload convert/win-64/trainscanner-$(VER).tar.bz2
	$(ANACONDA) upload convert/linux-64/trainscanner-$(VER).tar.bz2
	$(ANACONDA) upload $(CONVERT_BASE)/conda-bld/osx-64/trainscanner-$(VER).tar.bz2
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
	pip install sk-video tiledimage videosequence
	conda env export > trainscanner-anaconda-ubuntu.yml
	source deactivate
anaconda-mac:
	export PATH=~/anaconda/bin:$$PATH
	conda create -yn trainscanner python=3.5
	source activate trainscanner
	conda install -c vitroid -y trainscanner
	conda install -c menpo -y opencv3
	conda install -y pyqt=5.6
	pip install sk-video tiledimage videosequence
	conda env export > trainscanner-anaconda-mac.yml
	source deactivate
