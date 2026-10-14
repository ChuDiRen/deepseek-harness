# AIQE_DYNAMIC_FUNCTION_META {"function_code": "get_login_credentials", "function_type": "通用工具", "function_name": "获取登录凭证", "description": "从环境变量中读取测试登录账号的手机号和密码，供 Web UI 登录流程使用", "enabled": true, "params": [], "outputs": [{"key": "phone_number", "name": "手机号", "value_type": "string", "description": "测试登录手机号，来源为环境变量 TEST_PHONE_NUMBER"}, {"key": "password", "name": "登录密码", "value_type": "string", "description": "测试登录密码，来源为环境变量 TEST_PASSWORD"}]}

def execute(**kwargs):
    """从运行时上下文中读取 TEST_PHONE_NUMBER 和 TEST_PASSWORD 环境变量。

    环境变量由 AI-环境变量/default/env_var.yaml 注入到 _context 中，
    运行时直接通过 context.get(...) 读取即可。

    Returns:
        dict: {"phone_number": str, "password": str}
    """
    import json

    try:
        # --- 获取运行时上下文 ---
        _context_str = kwargs.get("_context", "")
        if not _context_str:
            raise ValueError("_context 缺失，无法获取环境变量")

        context = json.loads(_context_str)
        if not isinstance(context, dict):
            raise TypeError(f"_context 解析后必须是 dict，实际为 {type(context).__name__}")

        # --- 读取必填环境变量（缺少时直接 raise，不设默认值） ---
        phone_number = context.get("TEST_PHONE_NUMBER")
        if not phone_number:
            raise ValueError("环境变量 TEST_PHONE_NUMBER 未配置，请在 AI-环境变量/default/env_var.yaml 中设置测试手机号")

        password = context.get("TEST_PASSWORD")
        if not password:
            raise ValueError("环境变量 TEST_PASSWORD 未配置，请在 AI-环境变量/default/env_var.yaml 中设置测试密码")

        return {
            "phone_number": str(phone_number),
            "password": str(password),
        }
    except Exception:
        # 出现异常直接抛出，不设置默认值掩盖错误
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
