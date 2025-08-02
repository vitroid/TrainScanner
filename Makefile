#PYTHONEXE=trainscanner_gui.py pass1_gui.py stitch_gui.py shakereduction.py rect.py helix.py hans_style.py film.py add_instruction.py
#PYTHONLIB=canvas.py imagebar.py pass1.py imageselector2.py qrangeslider.py trainscanner.py stitch.py
PIP=pip3
PYTHON=python3

# バージョン番号を取得
VERSION := $(shell poetry version -s)

all: #macapp install #macapp-personally
	echo There is no 'all' to be built for now.

%.md: temp_%.md Makefile pyproject.toml replacer.py
	python replacer.py < $< > $@

##############################
#  Git Hooks
##############################
setup-hooks:
	@echo "Git hooksを設定中..."
	@cp hooks/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@cp hooks/post-commit .git/hooks/post-commit
	@chmod +x .git/hooks/post-commit
	@echo "Git hooksの設定が完了しました"

##############################
#  PyPI
##############################
test-deploy: build
	poetry publish -r testpypi
test-install:
	$(PIP) install --index-url https://test.pypi.org/simple/ trainscanner

uninstall:
	-$(PIP) uninstall -y trainscanner
build: README.md $(wildcard trainscanner/*.py)
	poetry build -f wheel

tag:
	-git tag -a v$(VERSION) -m "Release version $(VERSION)"

deploy: build tag
	poetry publish
	git push origin v$(VERSION)

check:
	poetry check
clean:
	-rm $(ALL) *~ */*~
	-rm -rf build dist *.egg-info
	-find . -name __pycache__ | xargs rm -rf

# # old stuff
# test1: test1.png
# test1.png: test1.tsconf
# 	$(PYTHON) ./stitch_gui.py @$<
# test1.tsconf:
# 	$(PYTHON) ./pass1_gui.py examples/sample.mov --log test1
distclean:
	-rm -rf dist build *.egg-info __pycache__ *.pyc
	make -C examples distclean
