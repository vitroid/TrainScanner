# -*- coding: utf-8 -*-
from PyQt6.QtCore import QTranslator, QLocale
import os
import trainscanner


def setup_translator():
    """
    Qtの翻訳を設定する関数
    """
    translator = QTranslator()
    path = os.path.dirname(trainscanner.__file__)

    # まずLANG環境変数を確認
    lang = os.environ.get("LANG", "").split("_")[0]

    # LANGが設定されていない場合はQLocaleを使用
    if not lang:
        locale = QLocale()
        lang = locale.name().split("_")[0]

    if lang == "ja":
        translator.load(path + "/i18n/trainscanner_ja")
    elif lang == "fr":
        translator.load(path + "/i18n/trainscanner_fr")

    return translator


def _(text):
    """
    翻訳関数
    翻訳に失敗した場合は元のテキストを返す
    """
    if not text:
        return text

    translator = getattr(_, "translator", None)
    if translator is None:
        translator = setup_translator()
        setattr(_, "translator", translator)

    translated = translator.translate("trainscanner", text)
    return translated if translated else text
