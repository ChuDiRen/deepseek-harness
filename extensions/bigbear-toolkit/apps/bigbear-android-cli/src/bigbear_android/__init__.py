# -*- coding: utf-8 -*-
"""BigBear Android - AI-powered Android device control via adb commands"""
try:
    from importlib.metadata import version
    __version__ = version("bigbear-android-cli")
except Exception:
    __version__ = "unknown"