# Script to register trainscanner to the Conda repository
# meta.yaml contains the minimal requirements.
# All the dependencies must be resolved by the Anaconda Environment file trainscanner-anaconda.yml
prepare:
	conda install conda-build
trainscanner:
	conda skeleton pypi trainscanner
build:
	conda build trainscanner
upload:
	~/anaconda/bin/anaconda login
	~/anaconda/bin/anaconda upload (bz2 file)
	echo restart the anaconda navigator

