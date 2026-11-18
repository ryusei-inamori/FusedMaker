# -*- coding: utf-8 -*-
"""
Qt binding selector.

PySide6 (LGPL v3) is preferred for distribution; PyQt6 (GPL v3 / commercial) is used as a
fallback so the app keeps running in an environment where only PyQt6 is installed.
Force a binding with the environment variable FUSED_QT_API=pyside6 | pyqt6.
"""
import os

_forced = os.environ.get("FUSED_QT_API", "").lower()
_order = ["pyqt6", "pyside6"] if _forced == "pyqt6" else ["pyside6", "pyqt6"]

QT_API = None
_err = None
for _api in _order:
    try:
        if _api == "pyside6":
            from PySide6 import QtCore, QtGui, QtWidgets  # noqa: F401
            from PySide6.QtCore import Signal, Slot  # noqa: F401
            QT_API = "PySide6"
            QT_VERSION = QtCore.qVersion()
            BINDING_VERSION = __import__("PySide6").__version__
        else:
            from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: F401
            from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot  # noqa: F401
            QT_API = "PyQt6"
            QT_VERSION = QtCore.qVersion()
            BINDING_VERSION = QtCore.PYQT_VERSION_STR
        break
    except ImportError as e:  # pragma: no cover
        _err = e

if QT_API is None:  # pragma: no cover
    raise ImportError(f"Neither PySide6 nor PyQt6 is installed: {_err}")
