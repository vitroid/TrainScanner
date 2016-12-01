all:

#for mac and windows
macapp:
	#pyinstaller --windowed --noconfirm -i trainscanner.icns --name TrainScanner trainscanner_gui.py
	pyinstaller --noconfirm macos.spec
	pyinstaller --noconfirm converter_gui.macos.spec
#icons are generated at /Users/matto/github/TrainScanner/trainscanner.icns
macdebug:
	pyinstaller --noconfirm --debug --console macos.spec
	pyinstaller --noconfirm --debug --console converter_gui.macos.spec
maczip:
	cd dist; zip -r trainscanner.x.y.macos.zip TrainScanner.app TS_converter.app; md5 trainscanner.x.y.macos.zip | tee trainscanner.x.y.macos.zip.md5
patch_for_mac:
	patch /usr/local/lib/python3.5/site-packages/PyInstaller/depend/bindepend.py < bindepend.diff
prepare_for_mac:
	brew tap homebrew/boneyard #for old PyQt4
	brew install opencv3 --with-ffmpeg --with-tbb --with-python3 --HEAD
	brew link opencv3 --force
	pip2 uninstall setuptools
	pip2 install setuptools   #!!! it avoided the errors in pyinstaller
	pip2 install pyinstaller
prepare_for_mac_p3:
	brew install pyqt5  # wants python3
	pip3 install pyinstaller
	brew install opencv3 --with-ffmpeg --with-tbb --with-python3 --HEAD
	brew link opencv3 --force

#in reality there is no make on Windows by default.
winexe:
	pyinstaller.exe --noconfirm --onefile --windowed windows.spec
