import argparse


def list_cli_options(parser: argparse.ArgumentParser):
    """
    コマンドラインオプションの一覧をリストで返すAPI

    Returns:
        list: 各オプションの情報を含む辞書のリスト
        [
            {
                "option_strings": ["--option", "-o"],  # オプション名
                "dest": "option_name",                # 変数名
                "help": "ヘルプテキスト",             # ヘルプメッセージ
                "required": True/False,               # 必須かどうか
                "nargs": None/1/2/.../"+"/"*",       # 引数の数
                "default": None/値,                   # デフォルト値
                "type": "str"/"int"/.../None,        # 型
            },
            ...
        ]
    """
    options = []
    for action in parser._actions:
        opt = {
            "option_strings": action.option_strings,
            "dest": action.dest,
            "help": action.help,
            "required": action.required,
            "nargs": action.nargs,
            "default": action.default,
            "type": action.type if action.type else None,
        }
        if opt["type"] in (int, float):
            try:
                help, minmax = opt["help"].split("--")
                min, max = [float(x) for x in minmax.split(",")]
                opt["help"] = help
                opt["min"] = min
                opt["max"] = max
            except ValueError:
                pass
        options.append(opt)
    return options, parser.description
