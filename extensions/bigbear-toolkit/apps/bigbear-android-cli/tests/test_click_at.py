# -*- coding: utf-8 -*-
"""Tests for bigbear-android-cli click-at subcommand."""
from unittest.mock import patch

import pytest

from bigbear_android.adb import tap, ADBCommandError


def _ok_result():
    """构造一个返回码为 0 的 CompletedProcess 风格 mock"""
    result = type("R", (), {})()
    result.returncode = 0
    result.stdout = b""
    result.stderr = b""
    return result


def _fail_result(stderr: str):
    """构造一个返回码非 0 的 CompletedProcess 风格 mock"""
    result = type("R", (), {})()
    result.returncode = 1
    result.stdout = b""
    result.stderr = stderr.encode("utf-8")
    return result


def test_tap_with_serial():
    """带 serial 时命令为 adb -s <serial> shell input tap X Y"""
    with patch("bigbear_android.adb.subprocess.run", return_value=_ok_result()) as mock_run:
        tap(serial="emulator-5554", x=100, y=200)
        args = mock_run.call_args[0][0]
        assert args[:5] == ["adb", "-s", "emulator-5554", "shell", "input"]
        assert args[-3:] == ["tap", "100", "200"]


def test_tap_without_serial():
    """无 serial 时命令为 adb shell input tap X Y"""
    with patch("bigbear_android.adb.subprocess.run", return_value=_ok_result()) as mock_run:
        tap(serial=None, x=50, y=60)
        args = mock_run.call_args[0][0]
        assert args[:3] == ["adb", "shell", "input"]
        assert args[-3:] == ["tap", "50", "60"]


def test_tap_raises_on_error():
    """adb 返回非 0 时抛 ADBCommandError，错误信息含 stderr"""
    with patch("bigbear_android.adb.subprocess.run", return_value=_fail_result("error: closed")):
        with pytest.raises(ADBCommandError, match="closed"):
            tap(serial="x", x=0, y=0)
