#PYTHONEXE=trainscanner_gui.py pass1_gui.py stitch_gui.py shakereduction.py rect.py helix.py hans_style.py film.py add_instruction.py
#PYTHONLIB=canvas.py imagebar.py pass1.py imageselector2.py qrangeslider.py trainscanner.py stitch.py


all: #macapp install #macapp-personally
	echo There is no 'all' to be built for now.

##############################
#  PyPI
##############################
setup:
	./setup.py build
install:
	./setup.py install
uninstall:
	pip3 uninstall trainscanner
pypi:
distclean:
	-rm -rf dist build *.egg-info __pycache__
	make -C examples distclean

##############################
#  mac HomeBrew
##############################
#prepare for mac with homebrew environment
all-mac-brew:
	make prepare-mac-brew
	make macapp-brew
	make install-mac-brew
#python3.6 is incompat with pyinstaller
#To install the older python3.5.2_3:
#brew install https://raw.githubusercontent.com/Homebrew/homebrew-core/ec545d45d4512ace3570782283df4ecda6bb0044/Formula/python3.rb
prepare-mac-brew:
	brew install python3 #
	brew install pyqt5  # wants python3
	pip3 install pyinstaller
	brew install opencv3 --with-ffmpeg --with-tbb --with-python3 --HEAD
	brew link opencv3 --force

patch-mac-brew:
	patch /usr/local/lib/python3.6/site-packages/PyInstaller/depend/bindepend.py < bindepend.diff
macapp-brew: macapp
personal-macapp-brew: personal-macapp
install-macapp-brew: install-macapp

##############################
#  Common for macs
##############################
macapp: dist/TrainScanner.app dist/TrainConverter.app
install-macapp: dist/TrainScanner.app dist/TrainConverter.app
	cp $^ /Applications
dist/TrainScanner.app: $(wildcard *.py)
	echo PyInstaller is not available because it is incompatible with python3.6.
	pyinstaller --noconfirm macos.spec
dist/TrainConverter.app: $(wildcard *.py)
	echo PyInstaller is not available because it is incompatible with python3.6.
	pyinstaller --noconfirm converter_gui.macos.spec
zip-macapp.%: macapp
	cd dist; zip -r trainscanner.$*.macos.zip TrainScanner.app TS_converter.app; md5 trainscanner.$*.macos.zip | tee trainscanner.$*.macos.zip.md5
	-cp dist/trainscanner.$*.macos.zip* ~/Google\ Drive/TrainScanner/
personal-macapp: $(wildcard *.py) 
	pip3 install py2app
	-rm -rf build dist
	python3 trainscanner_gui-setup.py py2app -A      #alias mode. It is not portable
	python3 converter_gui-setup.py py2app -A      #alias mode. It is not portable

##############################
#  (Probably) common tasks
##############################
test1: test1.png
test1.png: test1.tsconf
	./stitch_gui.py @$<
test1.tsconf:
	./pass1_gui.py examples/sample.mov --log test1
_install:
	echo This software is not suitable for installation. Please use it in the present folder, or build the self-containing application.


#pip3 install pylru gi pillow















#for mac and windows
#icons are generated at /Users/matto/github/TrainScanner/trainscanner.icns

#This does not include the libraries in the App.
#patch will be made:
#/usr/local/lib/python3.5/site-packages/py2app/build_app.py: copy_dylib
#                if os.path.exists(link_dest) and not os.path.isdir(link_dest):
#                    pass
#                else:
#                    os.symlink(os.path.basename(dest), link_dest)
#/usr/local/lib/python3.5/site-packages/macholib
#                    fn = dyld_find(filename, env=self.env,
#                        executable_path=self.executable_path,
#                        loader_path=loader.filename)


#Mac App
#macdebug:
#	pyinstaller --noconfirm --debug --console macos.spec
#	pyinstaller --noconfirm --debug --console converter_gui.macos.spec

#Windows Exe
#Note: windows does not have make command. 
winexe:
	#install anaconda from https://www.continuum.io/
	#install wheel of opencv from http://www.lfd.uci.edu/%7Egohlke/pythonlibs/
	easy_install -U pip
	pip install --upgrade setuptools
	pip install pyinstaller
	pyinstaller.exe --noconfirm --onefile --windowed windows.spec


#brew install pygobject3 --with-python3
#brew install gst-python
#brew install gst-libav
#brew install gst-plugins-good  --with-jpeg
