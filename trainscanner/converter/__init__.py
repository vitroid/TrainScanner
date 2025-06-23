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
        try:
            # ヘルプテキストからオプションの値の範囲を取得
            # specの解釈はここでは行わない。
            help, spec = opt["help"].split("--")
            opt["help"] = help
            opt["spec"] = spec
        except ValueError:
            pass
        options.append(opt)
    return options, parser.description
