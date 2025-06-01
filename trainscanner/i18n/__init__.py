#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import locale
import logging
from pathlib import Path

# 翻訳データを保持する辞書
# {言語コード: {コンテキスト: {原文: 翻訳文}}}
TRANSLATIONS = {}

CURRENT_CONTEXT = "trainscanner"


def load_translations(ts_path: str) -> Dict[str, Dict[str, str]]:
    """
    TSファイルから翻訳データを読み込みます。

    Args:
        ts_path: TSファイルのパス

    Returns:
        翻訳データの辞書（{コンテキスト: {原文: 翻訳文}}）
    """
    logger = logging.getLogger()
    logger.debug(f"Loading translations from: {ts_path}")

    if not os.path.exists(ts_path):
        logger.error(f"Translation file not found: {ts_path}")
        return {}

    try:
        tree = ET.parse(ts_path)
        root = tree.getroot()

        translations = {}
        for context in root.findall(".//context"):
            context_name = context.find("name").text
            messages = {}
            for message in context.findall("message"):
                source = message.find("source").text
                translation = message.find("translation")
                if translation is not None and translation.text:
                    messages[source] = translation.text
            translations[context_name] = messages

        logger.debug(f"Successfully loaded translations from: {ts_path}")
        return translations
    except Exception as e:
        logger.error(f"Failed to load translations from {ts_path}: {e}")
        return {}


def get_system_language() -> str:
    """
    システムの言語設定を取得します。
    環境変数LANG、LC_ALL、LC_MESSAGESの順で確認し、
    最初に見つかった言語設定を返します。

    Returns:
        言語コード（例: "ja", "en"）
    """
    logger = logging.getLogger()

    # 環境変数から言語設定を取得
    lang = os.environ.get("LANG", "")
    logger.debug(f"LANG environment variable: {lang}")
    if not lang:
        lang = os.environ.get("LC_ALL", "")
        logger.debug(f"LC_ALL environment variable: {lang}")
    if not lang:
        lang = os.environ.get("LC_MESSAGES", "")
        logger.debug(f"LC_MESSAGES environment variable: {lang}")

    # 言語コードを抽出（例: "ja_JP.UTF-8" -> "ja"）
    if lang:
        lang = lang.split("_")[0]
        logger.debug(f"Extracted language code: {lang}")

    logger.debug(f"System language detected: {lang}")
    if lang:
        return lang

    # サポートされている言語かチェック
    if lang not in TRANSLATIONS:
        # デフォルトの言語設定を取得
        try:
            default_lang = locale.getdefaultlocale()[0].split("_")[0]
            logger.debug(f"Default locale: {default_lang}")
            if default_lang in TRANSLATIONS:
                logger.debug(f"Using default language: {default_lang}")
                return default_lang
        except Exception as e:
            logger.debug(f"Error getting default locale: {e}")
        logger.debug("Using fallback language: en")
        return "en"  # サポートされていない言語の場合は英語を返す

    return lang


def tr(text: str) -> str:
    """
    pylupdate6で抽出可能な翻訳関数。
    Qtのtr()関数と互換性を持つように実装されています。

    Args:
        text: 翻訳するテキスト

    Returns:
        翻訳されたテキスト
    """
    return _(text)


def _(text: str, lang: str = None) -> str:
    """
    テキストを翻訳します。

    Args:
        text: 翻訳するテキスト
        lang: 言語コード（Noneの場合はシステムの言語設定を使用）

    Returns:
        翻訳されたテキスト。翻訳が見つからない場合は元のテキストを返します。
    """
    logger = logging.getLogger()
    if lang is None:
        lang = get_system_language()

    if lang not in TRANSLATIONS:
        logger.warning(f"Unsupported language: {lang}")
        return text

    # 翻訳データから該当する翻訳を探す
    translations = TRANSLATIONS[lang]
    logger.debug(f"Translating text: {text}")

    # 現在のコンテキストで翻訳を探す
    if CURRENT_CONTEXT and CURRENT_CONTEXT in translations:
        if text in translations[CURRENT_CONTEXT]:
            translation = translations[CURRENT_CONTEXT][text]
            logger.debug(
                f"Found translation in context {CURRENT_CONTEXT}: {translation}"
            )
            return translation

    # どのコンテキストでも翻訳が見つからない場合は元のテキストを返す
    logger.debug(f"No translation found for: {text}")
    return text


def get_available_languages() -> list[str]:
    """
    利用可能な言語のリストを返します。

    Returns:
        言語コードのリスト
    """
    return list(TRANSLATIONS.keys())


def init_translations():
    """
    翻訳ファイルを初期化します。
    QApplicationの初期化時に呼び出す必要があります。
    """
    logger = logging.getLogger()
    i18n_dir = os.path.dirname(__file__)
    logger.debug(f"Initializing translations from directory: {i18n_dir}")

    for lang in ["ja", "fr"]:  # サポートする言語を追加
        ts_path = os.path.join(i18n_dir, f"trainscanner_{lang}.ts")
        logger.debug(f"Looking for translation file: {ts_path}")
        if os.path.exists(ts_path):
            translations = load_translations(ts_path)
            if translations:
                TRANSLATIONS[lang] = translations
                logger.debug(f"Added translations for language: {lang}")
        else:
            logger.warning(f"Translation file not found: {ts_path}")


if __name__ == "__main__":
    print(_("Open a movie"))
    print(_("Settings"))
    print(_("Slit mixing"))
    print(_("Sharp"))
    print(_("Diffuse"))
    print(_("Minimal displacement between the frames"))
    print(_("pixels"))
    print(_("Small"))
    print(_("Large"))
    print(_("Number of frames to estimate the velocity"))
    print(_("frames"))
    print(_("Short"))
    print(_("Long"))
    print(_("Ignore vertical displacements"))
    print(_("The train is initially stalling in the motion detection area."))
    print(_("Max acceleration"))
    print(_("Tripod"))
    print(_("Handheld"))
    print(_("Trailing frames"))
    print(_("Debug"))
    print(_("Finish"))
    print(_("Set the upper bound of the product image width"))
    print(_("Start"))
    print(_("Open file"))
    print(_("degrees"))
    print(_("Drag & drop an image strip"))
    print(_("Add the film perforations"))
    print(_("Do nothing"))
    print(_("Make a helical image"))
    print(_("Make a rectangular image"))
    print(_("Make a Hans-style image"))
    print(_("Make a scrolling movie"))
    print(_("Stitch to a long image strip"))
    print(_("Open an image"))
