# AIQE_DYNAMIC_FUNCTION_META {"function_code": "get_login_info", "function_type": "通用工具", "function_name": "获取用户登录信息", "description": "固定返回预置的用户登录信息（用户名 admin，密码 123456），用于测试登录或演示场景", "enabled": true, "params": [], "outputs": [{"key": "username", "name": "用户名", "value_type": "string", "description": "登录用户名，固定为 admin"}, {"key": "password", "name": "密码", "value_type": "string", "description": "登录密码，固定为 123456"}]}

def execute(**kwargs):
    """固定返回预置的用户登录信息。

    Returns:
        dict: 包含 username 和 password 两个字段的字典。
    """
    try:
        # 固定返回预置的测试账号信息
        login_info = {
            "username": "admin",
            "password": "123456",
        }
        return login_info
    except Exception:
        # 出现异常直接抛出，不设置默认值
        raise
    finally:
        # 该函数无外部资源，保留 finally 结构以符合规范
        pass


if __name__ == "__main__":
    # AIQE 动态函数 CLI 入口。
    #
    # 三种调用方式(按优先级):
    #   1) stdin 传 JSON(推荐,完全回避 shell 引号嵌套问题):
    #        echo '{"k":"v"}' | python xxx.py --_context-stdin
    #   2) 命令行 --_context <json>(简单场景):
    #        python xxx.py --_context '{"k":"v"}'
    #   3) 透传 --key value 给 execute(**kwargs)(兼容旧调用):
    #        python xxx.py --_context '{}' --foo bar
    #
    # 业务返回 dict → json.dumps 到 stdout。
    # 异常 → traceback + error JSON 到 stderr,RC=1。
    import argparse
    import json
    import sys
    import traceback

    parser = argparse.ArgumentParser(description="AIQE 动态函数执行入口")
    parser.add_argument(
        "--_context",
        default="",
        help="运行时上下文 JSON 字符串(命令行直接传,简单场景用)",
    )
    parser.add_argument(
        "--_context-stdin",
        action="store_true",
        help="从 stdin 读取运行时上下文 JSON(推荐,避免 shell 引号嵌套问题)",
    )
    # parse_known_args:除已注册选项外,允许透传任意 --key value 给 execute(**kwargs)
    _parsed, _extras = parser.parse_known_args()

    if _parsed._context_stdin:
        # 优先用 stdin(无 shell 引号嵌套风险)
        try:
            _context_str = sys.stdin.read()
        except Exception as _e:
            raise RuntimeError(f"从 stdin 读取 _context 失败:{_e}") from _e
    else:
        _context_str = _parsed._context

    _kwargs: dict = {"_context": _context_str}
    _i = 0
    while _i < len(_extras):
        _arg = _extras[_i]
        if not _arg.startswith("--"):
            raise ValueError(
                f"不支持的位置参数 {_arg!r},请使用 --key value 形式"
            )
        _key = _arg[2:]
        if not _key:
            raise ValueError(f"参数名不能为空:{_arg!r}")
        if _i + 1 < len(_extras) and not _extras[_i + 1].startswith("--"):
            _kwargs[_key] = _extras[_i + 1]
            _i += 2
        else:
            # 布尔型标记:只传 --flag,不接 value
            _kwargs[_key] = ""
            _i += 1

    try:
        _result = execute(**_kwargs)
        print(json.dumps(_result, ensure_ascii=False))
    except SystemExit:
        raise
    except Exception as _e:
        # 诊断信息走 stderr,stdout 仍保持干净,调用方用 returncode 区分成功/失败
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"error": str(_e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
