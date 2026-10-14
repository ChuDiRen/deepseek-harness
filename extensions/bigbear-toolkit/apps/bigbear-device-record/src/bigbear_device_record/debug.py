"""调试日志模块。

非 debug 模式：只输出简洁步骤信息。
debug 模式：输出详细调试信息。
"""
import sys

_DEBUG = False


def set_debug(enabled: bool) -> None:
    global _DEBUG
    _DEBUG = enabled


def is_debug() -> bool:
    return _DEBUG


def debug(*args, **kwargs) -> None:
    if _DEBUG:
        print("[DEBUG]", *args, **kwargs)
        sys.stdout.flush()


def info(*args, **kwargs) -> None:
    print("[INFO]", *args, **kwargs)
    sys.stdout.flush()


def warn(*args, **kwargs) -> None:
    print("[WARNING]", *args, **kwargs)
    sys.stdout.flush()


def error(*args, **kwargs) -> None:
    print("[ERROR]", *args, **kwargs)
    sys.stdout.flush()


def step(msg: str) -> None:
    """简洁步骤信息，非 debug 模式也显示。"""
    print(msg)
    sys.stdout.flush()
