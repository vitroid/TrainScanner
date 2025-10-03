import functools
from logging import getLogger


def debug_log(func):
    """関数の引数と戻り値をデバッグログに出力するデコレータ"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = getLogger()
        # 引数を文字列に変換
        args_str = ", ".join(map(repr, args))
        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        all_args_str = (
            f"{args_str}, {kwargs_str}"
            if args_str and kwargs_str
            else args_str or kwargs_str
        )

        logger.debug(f"{func.__name__} called with arguments: ({all_args_str})")
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} returned: {result!r}")
        return result

    return wrapper
