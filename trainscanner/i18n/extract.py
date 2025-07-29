#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import os
import argparse
import html
from pathlib import Path
import xml.etree.ElementTree as ET


def extract_strings(file_path):
    """Pythonファイルから翻訳対象の文字列を抽出する"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 行番号も取得するために、行ごとに処理
    strings_with_location = []
    for line_num, line in enumerate(content.splitlines(), 1):
        # tr()関数と_()関数の両方を検索
        patterns = [
            r'tr\s*\(\s*"([^"]*)"\s*\)',  # tr("...")
            r"tr\s*\(\s*\'([^\']*)\'\s*\)",  # tr('...')
            r'_\s*\(\s*"([^"]*)"\s*\)',  # _("...")
            r"_\s*\(\s*\'([^\']*)\'\s*\)",  # _('...')
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, line):
                strings_with_location.append((match.group(1), line_num))

    return strings_with_location


def read_existing_ts(ts_path):
    """既存のTSファイルから<source>文字列を抽出"""
    if not os.path.exists(ts_path):
        return {}

    tree = ET.parse(ts_path)
    root = tree.getroot()

    contexts = {}
    for context in root.findall(".//context"):
        name = context.find("name").text
        messages = {}
        for message in context.findall("message"):
            source = message.find("source").text
            translation = message.find("translation")
            messages[source] = {
                "translation": translation.text if translation is not None else source,
                "locations": [],
            }
            # 既存のlocationタグがあれば保持
            unique_items = set()
            for location in message.findall("location"):
                unique_items.add(
                    (location.get("filename", ""), location.get("line", ""))
                )
            # messages[source]["locations"] = [
            #     {"filename": filename, "line": line} for filename, line in unique_items
            # ]
        contexts[name] = messages

    return contexts


def create_ts_file(contexts, output_file):
    """翻訳対象の文字列から.tsファイルを生成する"""
    root = ET.Element("TS")
    root.set("version", "2.1")
    root.set("language", "ja_JP")

    for context_name, messages in sorted(contexts.items()):
        context = ET.SubElement(root, "context")
        name = ET.SubElement(context, "name")
        name.text = context_name

        for source, data in sorted(messages.items()):
            message = ET.SubElement(context, "message")
            source_elem = ET.SubElement(message, "source")
            source_elem.text = source
            translation_elem = ET.SubElement(message, "translation")
            translation_elem.text = data["translation"]

            # locationタグを追加
            for loc in data["locations"]:
                location = ET.SubElement(message, "location")
                location.set("filename", loc["filename"])
                location.set("line", str(loc["line"]))

    # XMLを整形して出力
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    tree.write(output_file, encoding="utf-8", xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(
        description="Extract translatable strings and generate TS file."
    )
    parser.add_argument(
        "--ts",
        type=str,
        default="trainscanner_ja.ts",
        help="出力先TSファイル名（デフォルト: trainscanner_ja.ts）",
    )
    parser.add_argument("files", nargs="+", help="翻訳対象のPythonファイル")
    args = parser.parse_args()

    output_file = args.ts
    input_files = args.files

    # 既存のTSファイルからcontextごとの文字列を取得
    existing_contexts = read_existing_ts(output_file)

    # 各ファイルから文字列を抽出
    for file_path in input_files:
        # ファイルの存在確認
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}", file=sys.stderr)
            continue

        # ファイルパスを正規化
        abs_file_path = os.path.abspath(file_path)
        print(f"Processing: {abs_file_path}", file=sys.stderr)  # デバッグ出力

        context_name = "trainscanner"  # single context
        strings_with_location = extract_strings(abs_file_path)

        if context_name not in existing_contexts:
            existing_contexts[context_name] = {}

        # 新規文字列を追加（既存の翻訳は保持）
        for string, line_num in strings_with_location:
            if string not in existing_contexts[context_name]:
                existing_contexts[context_name][string] = {
                    "translation": string,
                    "locations": [{"filename": abs_file_path, "line": line_num}],
                }
            else:
                # 既存の文字列に新しいlocationを追加
                existing_contexts[context_name][string]["locations"].append(
                    {"filename": abs_file_path, "line": line_num}
                )

    create_ts_file(existing_contexts, output_file)


if __name__ == "__main__":
    main()
