#!/usr/bin/env python
import sys
import os

# from genice2.tool import line_replacer
# import distutils.core
from logging import getLogger, INFO, basicConfig
from jinja2 import Environment, FileSystemLoader
import json
import toml
from trainscanner.i18n import tr, init_translations

basicConfig(level=INFO, format="%(levelname)s %(message)s")
logger = getLogger()
logger.debug("Debug mode.")

init_translations()


def add_prefix(L: list[str], prefix: str = "    "):
    return prefix + ("\n" + prefix).join(L) + "\n"


def get_usage(command: str, short_command: str):
    return "".join(
        os.popen(f"python -m trainscanner.converter.{command} --help").readlines()
    ).replace(f"python -m trainscanner.converter.{command}", short_command)


project = toml.load("pyproject.toml")

project |= {
    "usage_helicify": get_usage("helix", "helicify"),
    "usage_rectify": get_usage("rect", "rectify"),
    "usage_movify": get_usage("movie", "movify"),
}

# テンプレートの内容を標準入力から読み込む
template_content = sys.stdin.read()

# Jinja2環境を設定
env = Environment(loader=FileSystemLoader("."))
t = env.from_string(template_content)

# レンダリング
markdown_en = t.render(**project)
print(markdown_en)
