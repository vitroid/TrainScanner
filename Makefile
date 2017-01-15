all: macapp install #macapp-personally
	echo Done.

#for mac and windows
macapp: dist/TrainScanner.app dist/TS_Converter.app
dist/TrainScanner.app: $(wildcard *.py)
	pyinstaller --noconfirm macos.spec
dist/TS_Converter.app: $(wildcard *.py)
	pyinstaller --noconfirm converter_gui.macos.spec
install: dist/TrainScanner.app dist/TS_Converter.app
	cp $^ /Applications
#icons are generated at /Users/matto/github/TrainScanner/trainscanner.icns


#This does not include the libraries in the App.
macapp-personally: #prepare_for_mac_py3
	pip3 install py2app
	-rm -rf build dist
	python3 trainscanner_gui-setup.py py2app -A      #alias mode. It is not portable
	python3 converter_gui-setup.py py2app -A      #alias mode. It is not portable
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
macdebug:
	pyinstaller --noconfirm --debug --console macos.spec
	pyinstaller --noconfirm --debug --console converter_gui.macos.spec
maczip.%:
	cd dist; zip -r trainscanner.$*.macos.zip TrainScanner.app TS_converter.app; md5 trainscanner.$*.macos.zip | tee trainscanner.$*.macos.zip.md5
	-cp dist/trainscanner.$*.macos.zip* ~/Google\ Drive/TrainScanner/
patch_for_mac:
	patch /usr/local/lib/python3.5/site-packages/PyInstaller/depend/bindepend.py < bindepend.diff
prepare_for_mac_py3:
	brew install pyqt5  # wants python3
	pip3 install pyinstaller
	brew install opencv3 --with-ffmpeg --with-tbb --with-python3 --HEAD
	brew link opencv3 --force

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
