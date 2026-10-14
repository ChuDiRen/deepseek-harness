# -*- coding: utf-8 -*-
"""BigBear Web - AI-powered browser control via CDP"""
try:
    from importlib.metadata import version
    __version__ = version("bigbear-web-cli")
except Exception:
    __version__ = "unknown"
