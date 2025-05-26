VENV-PYTHON=venv/bin/python
VENV-PIP=venv/bin/pip

VERSION := $(shell venv/bin/pip show trainscanner | grep ^Version | awk '{print $$2}')
ARCH := $(shell uname -m)
LANG := ja

APP_NAME := TrainScanner
APP_EN_BUNDLE := build/$(APP_NAME).app
APP_JA_BUNDLE := build/$(APP_NAME)_ja.app
ZIP_NAME_EN := $(APP_NAME)-v$(VERSION)-macOS-$(ARCH)-en.zip
ZIP_NAME_JA := $(APP_NAME)-v$(VERSION)-macOS-$(ARCH)-ja.zip

GHTAG := v$(VERSION)

# all: github-release
all: $(ZIP_NAME_JA) $(ZIP_NAME_EN) 

app: $(APP_EN_BUNDLE) $(APP_JA_BUNDLE)
$(APP_EN_BUNDLE): TrainScanner.icns $(VENV-PYTHON)
	$(VENV-PYTHON) setup.py bdist_mac

$(APP_JA_BUNDLE): $(APP_EN_BUNDLE)
	cp -a build/TrainScanner.app build/TrainScanner_ja.app
	sed -e "s@<string>English</string>@<string>Japanese</string>@" build/TrainScanner.app/Contents/Info.plist > build/TrainScanner_ja.app/Contents/Info.plist

TrainScanner.icns: Shinkansen_jrw.png
	rm -rf TrainScanner.iconset
	mkdir TrainScanner.iconset
	sips -z 16 16     Shinkansen_jrw.png --out TrainScanner.iconset/icon_16x16.png
	sips -z 32 32     Shinkansen_jrw.png --out TrainScanner.iconset/icon_16x16@2x.png
	sips -z 32 32     Shinkansen_jrw.png --out TrainScanner.iconset/icon_32x32.png
	sips -z 64 64     Shinkansen_jrw.png --out TrainScanner.iconset/icon_32x32@2x.png
	sips -z 128 128   Shinkansen_jrw.png --out TrainScanner.iconset/icon_128x128.png
	sips -z 256 256   Shinkansen_jrw.png --out TrainScanner.iconset/icon_128x128@2x.png
	sips -z 256 256   Shinkansen_jrw.png --out TrainScanner.iconset/icon_256x256.png
	sips -z 512 512   Shinkansen_jrw.png --out TrainScanner.iconset/icon_256x256@2x.png
	sips -z 512 512   Shinkansen_jrw.png --out TrainScanner.iconset/icon_512x512.png
	iconutil -c icns TrainScanner.iconset

$(VENV-PYTHON):
	python -m venv venv
	$(VENV-PIP) install cx_Freeze~=8.3 ..


# For GitHub Release


$(ZIP_NAME_JA): $(APP_JA_BUNDLE)
	@echo "Zipping $< to $@)"
	rm -f $@
	ditto -c -k --sequesterRsrc --keepParent $< $@

$(ZIP_NAME_EN): $(APP_EN_BUNDLE)
	@echo "Zipping $< to $@)"
	rm -f $@
	ditto -c -k --sequesterRsrc --keepParent $< $@

github-release: $(ZIP_NAME_JA) $(ZIP_NAME_EN) 
	echo CodeSignしていないのでリリースできません。
	# gh release create $(GHTAG) $^ \
	# 	--title "TrainScanner $(VERSION)" \
	# 	--notes "日本語版と英語版を同時リリース"




clean:
	-rm -rf TrainScanner.iconset
	-rm -f TrainScanner.icns
	-rm -rf build
	-rm -rf dist
	-rm -rf venv
	-rm settings.py
	-rm *.zip
