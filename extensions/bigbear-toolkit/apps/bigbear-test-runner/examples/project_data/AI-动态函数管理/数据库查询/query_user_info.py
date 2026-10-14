# AIQE_DYNAMIC_FUNCTION_META {"function_code":"query_user_info","function_type":"数据库查询","function_name":"查询用户信息","description":"从数据库 user 表中随机返回一条用户信息（登录名、昵称），密码统一返回 123456","enabled":true,"params":[],"outputs":[{"key":"login_name","name":"登录名","value_type":"string","description":"用户登录名（来自 user.username）"},{"key":"nickname","name":"昵称","value_type":"string","description":"用户昵称（来自 user.nick_name）"},{"key":"password","name":"密码","value_type":"string","description":"固定返回 123456"}]}

def execute(**kwargs):
    """从数据库 user 表中随机返回一条用户信息（登录名、昵称），密码统一返回 123456。"""
    import json

    # 读取运行时上下文信息（_context 是系统自动传入的 JSON 字符串）
    # 环境变量在运行时会被打包进 _context，与 env_var.yaml 中的键一一对应
    _context_str = kwargs.get("_context", "")
    context = json.loads(_context_str) if _context_str else {}

    db_host = context.get("DB_HOST", "localhost")
    db_port_str = context.get("DB_PORT", "3306")
    try:
        db_port = int(db_port_str)
    except (TypeError, ValueError):
        db_port = 3306
    db_name = context.get("DB_NAME", "")
    db_user = context.get("DB_USER", "root")
    db_password = context.get("DB_PASSWORD", "")

    try:
        import pymysql
    except ImportError:
        return {"login_name": "", "nickname": "", "password": "123456"}

    conn = None
    try:
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        with conn.cursor() as cursor:
            # 随机返回一条用户
            sql = "SELECT username, nick_name FROM user ORDER BY RAND() LIMIT 1"
            cursor.execute(sql)
            row = cursor.fetchone()
            if row:
                return {
                    "login_name": str(row.get("username", "") or ""),
                    "nickname": str(row.get("nick_name", "") or ""),
                    "password": "123456",
                }
            return {"login_name": "", "nickname": "", "password": "123456"}
    except Exception:
        return {"login_name": "", "nickname": "", "password": "123456"}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
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
