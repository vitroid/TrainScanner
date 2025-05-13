#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import locale
import logging


def load_translations(qph_path: str) -> Dict[str, str]:
    """
    QPHファイルから翻訳データを読み込みます。

    Args:
        qph_path: QPHファイルのパス

    Returns:
        翻訳データの辞書（キー: 原文、値: 翻訳文）
    """
    tree = ET.parse(qph_path)
    root = tree.getroot()

    translations = {}
    for phrase in root.findall("phrase"):
        source = phrase.find("source").text
        target = phrase.find("target").text
        translations[source] = target

    return translations


# QPHファイルのパス
QPH_PATH = os.path.join(os.path.dirname(__file__), "trainscanner.qph")

# 翻訳データを読み込む
TRANSLATIONS = {"ja": load_translations(QPH_PATH)}


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
    if not lang:
        lang = os.environ.get("LC_ALL", "")
    if not lang:
        lang = os.environ.get("LC_MESSAGES", "")

    # 言語コードを抽出（例: "ja_JP.UTF-8" -> "ja"）
    if lang:
        lang = lang.split("_")[0]

    # サポートされている言語かチェック
    if lang not in TRANSLATIONS:
        # デフォルトの言語設定を取得
        try:
            default_lang = locale.getdefaultlocale()[0].split("_")[0]
            if default_lang in TRANSLATIONS:
                return default_lang
        except:
            pass
        return "en"  # サポートされていない言語の場合は英語を返す

    return lang


def tr(text: str, context: str = None) -> str:
    """
    pylupdate6で抽出可能な翻訳関数。
    Qtのtr()関数と互換性を持つように実装されています。

    Args:
        text: 翻訳するテキスト
        context: コンテキスト（オプション）

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
    translation = TRANSLATIONS[lang].get(text)
    if translation is None:
        logger.debug(f"No translation found for: {text}")
        return text

    return translation


def get_available_languages() -> list[str]:
    """
    利用可能な言語のリストを返します。

    Returns:
        言語コードのリスト
    """
    return list(TRANSLATIONS.keys())


# pylupdate6で抽出される文字列の例
if __name__ == "__main__":
    tr("Open a movie")
    tr("Settings")
    tr("Slit mixing")
    tr("Sharp")
    tr("Diffuse")
    tr("Minimal displacement between the frames")
    tr("pixels")
    tr("Small")
    tr("Large")
    tr("Number of frames to estimate the velocity")
    tr("frames")
    tr("Short")
    tr("Long")
    tr("Ignore vertical displacements")
    tr("The train is initially stalling in the motion detection area.")
    tr("Max acceleration")
    tr("Tripod")
    tr("Handheld")
    tr("Trailing frames")
    tr("Debug")
    tr("Finish")
    tr("Set the upper bound of the product image width")
    tr("Start")
    tr("Open file")
    tr("degrees")
    tr("Drag & drop an image strip")
    tr("Add the film perforations")
    tr("Do nothing")
    tr("Make a helical image")
    tr("Make a rectangular image")
    tr("Make a Hans-style image")
    tr("Make a scrolling movie")
    tr("Stitch to a long image strip")
    tr("Open an image")
