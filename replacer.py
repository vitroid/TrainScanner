#!/usr/bin/env python
import sys
import os

# from genice2.tool import line_replacer
# import distutils.core
from logging import getLogger, INFO, basicConfig
from jinja2 import Environment, FileSystemLoader
import json
import toml


basicConfig(level=INFO, format="%(levelname)s %(message)s")
logger = getLogger()
logger.debug("Debug mode.")


def add_prefix(L: list[str], prefix: str = "    "):
    return prefix + ("\n" + prefix).join(L) + "\n"


project = toml.load("pyproject.toml")

project |= {
    "usage_hansify": "".join(
        os.popen("python -m trainscanner.converter.hans_style --help").readlines()
    ),
    "usage_helicify": "".join(
        os.popen("python -m trainscanner.converter.helix --help").readlines()
    ),
    "usage_filmify": "".join(
        os.popen("python -m trainscanner.converter.film --help").readlines()
    ),
    "usage_rectify": "".join(
        os.popen("python -m trainscanner.converter.rect --help").readlines()
    ),
    "usage_movify": "".join(
        os.popen("python -m trainscanner.converter.scroll --help").readlines()
    ),
    "usage_movify2": "".join(
        os.popen("python -m trainscanner.converter.movie2 --help").readlines()
    ),
}

# テンプレートの内容を標準入力から読み込む
template_content = sys.stdin.read()

# Jinja2環境を設定
env = Environment(loader=FileSystemLoader("."))
t = env.from_string(template_content)

# レンダリング
markdown_en = t.render(**project)
print(markdown_en)
