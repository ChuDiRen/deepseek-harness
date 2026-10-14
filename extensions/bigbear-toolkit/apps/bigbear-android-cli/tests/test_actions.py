# -*- coding: utf-8 -*-
"""AndroidActions 单元测试（mock ADBManager）"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bigbear_android.actions import AndroidActions, KEYCODES


@pytest.fixture
def mock_adb():
    """构造 mock ADBManager"""
    adb = MagicMock()
    adb.get_screen_size.return_value = (1080, 1920)
    adb.shell.return_value = (0, "", "")  # 默认 shell 返回成功
    return adb


@pytest.fixture
def actions(mock_adb):
    return AndroidActions(mock_adb)


# ===== 点击 =====

def test_tap_calls_shell_input(actions, mock_adb):
    actions.tap(100, 200)
    mock_adb.shell_input.assert_called_once_with("tap", "100", "200")


def test_click_at_is_alias_for_tap(actions, mock_adb):
    actions.click_at(300, 400)
    mock_adb.shell_input.assert_called_once_with("tap", "300", "400")


def test_double_tap_taps_twice(actions, mock_adb):
    actions.double_tap(500, 600)
    assert mock_adb.shell_input.call_count == 2
    mock_adb.shell_input.assert_any_call("tap", "500", "600")


def test_long_press_uses_swipe_with_same_coords(actions, mock_adb):
    actions.long_press(700, 800, duration_ms=1500)
    mock_adb.shell_input.assert_called_once_with(
        "swipe", "700", "800", "700", "800", "1500",
    )


# ===== 滑动 =====

def test_swipe_up(actions, mock_adb):
    actions.swipe_up(count=1)
    mock_adb.shell_input.assert_called_once()
    args = mock_adb.shell_input.call_args[0]
    assert args[0] == "swipe"
    # 起点 y 应大于终点 y（手指从下往上划）
    start_y = int(args[2])
    end_y = int(args[4])
    assert start_y > end_y


def test_swipe_down(actions, mock_adb):
    actions.swipe_down(count=1)
    args = mock_adb.shell_input.call_args[0]
    assert args[0] == "swipe"
    # 起点 y 应小于终点 y（手指从上往下划）
    start_y = int(args[2])
    end_y = int(args[4])
    assert start_y < end_y


def test_swipe_left(actions, mock_adb):
    actions.swipe_left(count=1)
    args = mock_adb.shell_input.call_args[0]
    start_x = int(args[1])
    end_x = int(args[3])
    assert start_x > end_x


def test_swipe_right(actions, mock_adb):
    actions.swipe_right(count=1)
    args = mock_adb.shell_input.call_args[0]
    start_x = int(args[1])
    end_x = int(args[3])
    assert start_x < end_x


def test_swipe_count_multiplies(actions, mock_adb):
    actions.swipe_up(count=3)
    assert mock_adb.shell_input.call_count == 3


def test_swipe_in_region_down(actions, mock_adb):
    actions.swipe_in_region((100, 200, 500, 1000), direction="down")
    args = mock_adb.shell_input.call_args[0]
    assert args[0] == "swipe"
    # 起点 y < 终点 y（在区域内从上方划向下方）
    start_y = int(args[2])
    end_y = int(args[4])
    assert start_y < end_y


def test_swipe_in_region_invalid_direction_raises(actions):
    with pytest.raises(ValueError):
        actions.swipe_in_region((0, 0, 100, 100), direction="diagonal")


# ===== 输入 =====

def test_input_text_english(actions, mock_adb):
    actions.input_text(300, 400, "hello")
    # 第一次 tap，第二次 input text
    assert mock_adb.shell_input.call_count == 2
    first_call = mock_adb.shell_input.call_args_list[0]
    assert first_call[0] == ("tap", "300", "400")
    second_call = mock_adb.shell_input.call_args_list[1]
    assert second_call[0][0] == "text"
    assert "hello" in second_call[0][1]


def test_input_text_chinese_uses_clipboard(actions, mock_adb):
    """中文输入通过剪贴板路径：默认 mock 返回 rc=0 且读回一致 -> 走剪贴板方案"""
    # mock clipboard set/get 都返回成功
    mock_adb.shell.return_value = (0, "你好", "")
    actions.input_text(300, 400, "你好")
    # 中文路径：tap + MOVE_END + batch DEL + PASTE
    calls = mock_adb.shell_input.call_args_list
    # 必须有 tap
    assert any(c[0][:2] == ("tap", "300") for c in calls)
    # 必须有 batch keyevent（包含多次 DEL）
    del_call = [c for c in calls if c[0][0] == "keyevent" and len(c[0]) > 1 and c[0][1] == "67"]
    assert len(del_call) >= 1, f"期望至少一次批量 DEL 调用，实际: {calls}"
    # 必须有 PASTE (279)
    assert any(c[0] == ("keyevent", "279") for c in calls)
    # 不应该触发 ADBKeyboard 路径（无 is_installed / set_ime / broadcast 调用）
    mock_adb.set_ime.assert_not_called()
    mock_adb.broadcast.assert_not_called()


def test_input_text_chinese_falls_back_when_clipboard_unsupported(actions, mock_adb, monkeypatch):
    """当 cmd clipboard 在设备上不可用（如 vivo），自动回退到 ADBKeyboard"""
    # 模拟 vivo 行为：set 和 get 都返回 'No shell command implementation.'
    def fake_shell(*args, **kwargs):
        cmd = args
        if "set-primary-clip" in cmd or "get-primary-clip" in cmd:
            return (0, "", "No shell command implementation.")
        return (0, "", "")

    mock_adb.shell.side_effect = fake_shell
    # 模拟 ADBKeyboard 已安装，跳过下载
    mock_adb.is_installed.return_value = True
    mock_adb.get_current_ime.return_value = "com.baidu.input_vivo/.ImeVivoService"
    mock_adb.broadcast.return_value = (0, "Broadcast completed: result=0", "")

    actions.input_text(300, 400, "别墅")

    # 应该走 ADBKeyboard 路径
    mock_adb.set_ime.assert_any_call("com.android.adbkeyboard/.AdbIME")
    mock_adb.broadcast.assert_called_once()
    # 广播参数应包含 msg="别墅"
    broadcast_args = mock_adb.broadcast.call_args
    assert broadcast_args[0][0] == "ADB_INPUT_TEXT"
    assert broadcast_args[1]["msg"] == "别墅"
    # 必须恢复原 IME
    mock_adb.set_ime.assert_any_call("com.baidu.input_vivo/.ImeVivoService")


def test_input_text_chinese_falls_back_when_clipboard_readback_mismatch(actions, mock_adb, monkeypatch):
    """当剪贴板 set 返回 rc=0 但读回内容不一致（实际失败），也应回退"""
    def fake_shell(*args, **kwargs):
        cmd = args
        if "set-primary-clip" in cmd:
            return (0, "", "")  # rc=0, 看似成功
        if "get-primary-clip" in cmd:
            return (0, "旧内容", "")  # 但读回是旧内容，没真的写入
        return (0, "", "")

    mock_adb.shell.side_effect = fake_shell
    mock_adb.is_installed.return_value = True
    mock_adb.get_current_ime.return_value = "com.baidu.input_vivo/.ImeVivoService"
    mock_adb.broadcast.return_value = (0, "Broadcast completed: result=0", "")

    actions.input_text(300, 400, "别墅")

    # 读回不一致 → 必须触发 ADBKeyboard 回退
    mock_adb.set_ime.assert_any_call("com.android.adbkeyboard/.AdbIME")
    mock_adb.broadcast.assert_called_once()


def test_input_text_chinese_batch_del_in_one_call(actions, mock_adb):
    """DEL 应是批量一次调用而非 50 次循环（性能）"""
    mock_adb.shell.return_value = (0, "你好", "")
    actions.input_text(300, 400, "你好")

    # 找出所有 keyevent "67" 调用
    del_calls = [
        c for c in mock_adb.shell_input.call_args_list
        if c[0][0] == "keyevent" and any("67" == x for x in c[0][1:])
    ]
    # 应有 1 次 batch DEL 调用（带 50 个 '67'），而不是 50 次单独调用
    assert len(del_calls) == 1, f"期望 1 次批量 DEL，实际 {len(del_calls)} 次: {del_calls}"
    # 该调用应包含 50 个 '67'
    assert del_calls[0][0].count("67") == 50


def test_input_via_clipboard_raises_clipboard_not_supported(actions, mock_adb):
    """_input_via_clipboard 在 cmd clipboard 不可用时必须抛 ClipboardNotSupported"""
    from bigbear_android.actions import ClipboardNotSupported

    mock_adb.shell.return_value = (0, "", "No shell command implementation.")
    with pytest.raises(ClipboardNotSupported):
        actions._input_via_clipboard("别墅")


def test_input_via_adbkeyboard_installs_when_missing(actions, mock_adb, tmp_path, monkeypatch):
    """ADBKeyboard 未安装时应自动下载+安装"""
    # 把下载缓存目录指向 tmp
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # 创建一个假的已下载 APK
    apk = tmp_path / ".cache" / "bigbear-android-cli" / "ADBKeyboard.apk"
    apk.parent.mkdir(parents=True)
    apk.write_bytes(b"fake apk content" * 100)

    mock_adb.is_installed.return_value = False
    mock_adb.get_current_ime.return_value = "com.baidu.input_vivo/.ImeVivoService"
    mock_adb.broadcast.return_value = (0, "Broadcast completed: result=0", "")

    actions._input_via_adbkeyboard("别墅")

    # 应该调用 install_apk 一次
    mock_adb.install_apk.assert_called_once()
    # 应该切换 IME 并广播
    mock_adb.set_ime.assert_any_call("com.android.adbkeyboard/.AdbIME")
    mock_adb.broadcast.assert_called_once()
    # 恢复原 IME
    mock_adb.set_ime.assert_any_call("com.baidu.input_vivo/.ImeVivoService")


def test_input_via_adbkeyboard_skips_install_when_present(actions, mock_adb):
    """ADBKeyboard 已安装时跳过下载和安装"""
    mock_adb.is_installed.return_value = True
    mock_adb.get_current_ime.return_value = "com.baidu.input_vivo/.ImeVivoService"
    mock_adb.broadcast.return_value = (0, "Broadcast completed: result=0", "")

    actions._input_via_adbkeyboard("别墅")

    mock_adb.install_apk.assert_not_called()
    mock_adb.set_ime.assert_any_call("com.android.adbkeyboard/.AdbIME")
    mock_adb.broadcast.assert_called_once()


def test_input_via_adbkeyboard_restores_ime_on_failure(actions, mock_adb):
    """ADBKeyboard 广播失败时仍应恢复原 IME"""
    mock_adb.is_installed.return_value = True
    mock_adb.get_current_ime.return_value = "com.baidu.input_vivo/.ImeVivoService"
    mock_adb.broadcast.return_value = (0, "Broadcast completed: result=-1", "")  # 失败

    with pytest.raises(RuntimeError):
        actions._input_via_adbkeyboard("别墅")

    # 即使失败，也必须尝试恢复原 IME
    assert any(
        c.args[0] == "com.baidu.input_vivo/.ImeVivoService"
        for c in mock_adb.set_ime.call_args_list
    )


def test_input_text_escapes_spaces(actions, mock_adb):
    actions.input_text(100, 100, "hello world")
    text_call = [c for c in mock_adb.shell_input.call_args_list if c[0][0] == "text"]
    assert len(text_call) == 1
    # adb input text 用 %s 表示空格
    assert "hello%sworld" in text_call[0][0][1]


def test_has_non_ascii_detects_chinese(actions):
    """_has_non_ascii 应通过实例调用"""
    assert actions._has_non_ascii("hello") is False
    assert actions._has_non_ascii("你好") is True
    assert actions._has_non_ascii("hello你好") is True
    assert actions._has_non_ascii("") is False


# ===== 按键 =====

def test_keyevent_with_int(actions, mock_adb):
    actions.keyevent(4)
    mock_adb.shell_input.assert_called_once_with("keyevent", "4")


def test_keyevent_with_name(actions, mock_adb):
    actions.keyevent("back")
    mock_adb.shell_input.assert_called_once_with("keyevent", "4")


def test_keyevent_unknown_name_raises(actions):
    with pytest.raises(ValueError):
        actions.keyevent("nonsense_key")


def test_press_back_uses_keyevent_4(actions, mock_adb):
    actions.press_back()
    mock_adb.shell_input.assert_called_once_with("keyevent", "4")


def test_press_home_uses_keyevent_3(actions, mock_adb):
    actions.press_home()
    mock_adb.shell_input.assert_called_once_with("keyevent", "3")


def test_press_enter_uses_keyevent_66(actions, mock_adb):
    actions.press_enter()
    mock_adb.shell_input.assert_called_once_with("keyevent", "66")


def test_wake_screen_uses_keyevent_224(actions, mock_adb):
    actions.wake_screen()
    mock_adb.shell_input.assert_called_once_with("keyevent", "224")


def test_sleep_screen_uses_keyevent_223(actions, mock_adb):
    actions.sleep_screen()
    mock_adb.shell_input.assert_called_once_with("keyevent", "223")


# ===== 按键码字典 =====

def test_keycodes_aliases_exist():
    assert KEYCODES["back"] == 4
    assert KEYCODES["home"] == 3
    assert KEYCODES["enter"] == 66
    assert KEYCODES["wake"] == 224
    assert KEYCODES["sleep"] == 223


def test_keycodes_recents_aliases():
    """recents / app_switch / recent / overview 都映射到 187"""
    assert KEYCODES["recents"] == 187
    assert KEYCODES["app_switch"] == 187
    assert KEYCODES["recent"] == 187
    assert KEYCODES["overview"] == 187


def test_keycodes_notifications_aliases():
    assert KEYCODES["notifications"] == 83


def test_keycodes_menu_alias():
    assert KEYCODES["menu"] == 82


def test_keycodes_navigation_aliases():
    """导航类按键"""
    assert KEYCODES["up"] == 19
    assert KEYCODES["down"] == 20
    assert KEYCODES["left"] == 21
    assert KEYCODES["right"] == 22


def test_open_recents_uses_187(actions, mock_adb):
    """open_recents 触发 KEYCODE_APP_SWITCH (187)"""
    actions.open_recents()
    mock_adb.shell_input.assert_called_once_with("keyevent", "187")


def test_open_notifications_uses_83(actions, mock_adb):
    """open_notifications 触发 KEYCODE_NOTIFICATION (83)"""
    actions.open_notifications()
    mock_adb.shell_input.assert_called_once_with("keyevent", "83")


def test_keyevent_with_recents_alias(actions, mock_adb):
    """keyevent 'recents' 解析为 187"""
    actions.keyevent("recents")
    mock_adb.shell_input.assert_called_once_with("keyevent", "187")


def test_keyevent_with_app_switch_alias(actions, mock_adb):
    """keyevent 'app_switch' 解析为 187"""
    actions.keyevent("app_switch")
    mock_adb.shell_input.assert_called_once_with("keyevent", "187")


# ===== 应用 =====

def test_launch_app_with_activity(actions, mock_adb):
    actions.launch_app("com.example", "MainActivity")
    mock_adb.shell.assert_called_once_with("am", "start", "-n", "com.example/MainActivity")


def test_launch_app_without_activity_uses_monkey(actions, mock_adb):
    actions.launch_app("com.example")
    mock_adb.shell.assert_called_once_with(
        "monkey", "-p", "com.example",
        "-c", "android.intent.category.LAUNCHER", "1",
    )


def test_launch_app_failure_raises(actions, mock_adb):
    mock_adb.shell.return_value = (1, "", "Error: no activity found")
    with pytest.raises(RuntimeError):
        actions.launch_app("invalid.pkg")


def test_stop_app_uses_force_stop(actions, mock_adb):
    actions.stop_app("com.example")
    mock_adb.shell.assert_called_once_with("am", "force-stop", "com.example")


def test_go_home(actions, mock_adb):
    actions.go_home()
    mock_adb.shell_input.assert_called_once_with("keyevent", "3")


# ===== 双指缩放 =====

def test_pinch_calls_two_swipes(actions, mock_adb):
    """pinch 调用两次 swipe（双指向内捏合）"""
    actions.pinch(540, 1100, scale=0.5, duration_ms=400)
    # 应有两次 shell_input 调用（两指各一次）
    assert mock_adb.shell_input.call_count == 2
    # 两次都应是 swipe 命令
    for call in mock_adb.shell_input.call_args_list:
        assert call[0][0] == "swipe"


def test_pinch_fingers_move_toward_center(actions, mock_adb):
    """pinch 时两指终点应更靠近中心"""
    actions.pinch(540, 1100, scale=0.5, duration_ms=400)
    calls = mock_adb.shell_input.call_args_list
    # 提取终点 X 坐标
    end_xs = [int(c[0][3]) for c in calls]  # swipe x1 y1 x2 y2 duration → x2 是第4个
    # 终点 X 应分布在中心两侧
    assert end_xs[0] < 540 < end_xs[1]


def test_pinch_smaller_scale_more_pinch(actions, mock_adb):
    """scale 越小（越接近 0），两指终点距离中心越近"""
    mock_adb.reset_mock()
    actions.pinch(540, 1100, scale=0.2, duration_ms=400)
    end_xs_close = sorted(int(c[0][3]) for c in mock_adb.shell_input.call_args_list)
    # 终点之间的距离
    dist_close = end_xs_close[1] - end_xs_close[0]

    mock_adb.reset_mock()
    actions.pinch(540, 1100, scale=0.8, duration_ms=400)
    end_xs_far = sorted(int(c[0][3]) for c in mock_adb.shell_input.call_args_list)
    dist_far = end_xs_far[1] - end_xs_far[0]

    assert dist_close < dist_far


def test_zoom_calls_two_swipes(actions, mock_adb):
    """zoom 调用两次 swipe（双指向外张开）"""
    actions.zoom(540, 1100, scale=2.0, duration_ms=400)
    assert mock_adb.shell_input.call_count == 2
    for call in mock_adb.shell_input.call_args_list:
        assert call[0][0] == "swipe"


def test_zoom_fingers_move_away_from_center(actions, mock_adb):
    """zoom 时两指起点应更靠近中心，终点远离中心"""
    actions.zoom(540, 1100, scale=2.0, duration_ms=400)
    calls = mock_adb.shell_input.call_args_list
    # 提取起点 X
    start_xs = sorted(int(c[0][1]) for c in calls)
    # 提取终点 X
    end_xs = sorted(int(c[0][3]) for c in calls)
    # 起点距离比终点距离近
    assert (start_xs[1] - start_xs[0]) < (end_xs[1] - end_xs[0])


def test_zoom_larger_scale_more_zoom(actions, mock_adb):
    """scale 越大，两指终点距离中心越远"""
    mock_adb.reset_mock()
    actions.zoom(540, 1100, scale=2.0, duration_ms=400)
    end_xs_2x = sorted(int(c[0][3]) for c in mock_adb.shell_input.call_args_list)
    dist_2x = end_xs_2x[1] - end_xs_2x[0]

    mock_adb.reset_mock()
    actions.zoom(540, 1100, scale=3.0, duration_ms=400)
    end_xs_3x = sorted(int(c[0][3]) for c in mock_adb.shell_input.call_args_list)
    dist_3x = end_xs_3x[1] - end_xs_3x[0]

    assert dist_3x > dist_2x


def test_pinch_duration_passed_through(actions, mock_adb):
    """duration_ms 应作为第 5 个参数传给 swipe"""
    actions.pinch(540, 1100, scale=0.5, duration_ms=800)
    for call in mock_adb.shell_input.call_args_list:
        assert call[0][5] == "800"  # duration


def test_zoom_minimum_offset(actions, mock_adb):
    """scale 极小时偏移不应小于 10 像素（兜底）"""
    actions.pinch(540, 1100, scale=0.001, duration_ms=400)
    for call in mock_adb.shell_input.call_args_list:
        # 终点 X 与中心的距离应 >= 10
        end_x = int(call[0][3])
        assert abs(end_x - 540) >= 10