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

prepare_for_mac:
	-brew install python3
	brew install opencv3 --with-ffmpeg --with-tbb --with-python3 --HEAD
	brew link opencv3 --force
	pip2 uninstall setuptools
	pip2 install setuptools   #!!! it avoided the errors in pyinstaller
	pip2 install pyinstaller
#in reality there is no make on Windows by default.
winexe:
	pyinstaller.exe --noconfirm --onefile --windowed windows.spec
