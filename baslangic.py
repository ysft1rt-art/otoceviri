"""Windows açılışında başlatma (HKCU\\...\\Run kaydı; yönetici izni gerekmez)."""

import os
import sys
import winreg

_ANAHTAR = r"Software\Microsoft\Windows\CurrentVersion\Run"
_DEGER_ADI = "OtoCeviri"


def baslatma_komutu() -> str:
    if getattr(sys, "frozen", False):  # PyInstaller ile derlenmiş .exe
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    betik = os.path.join(os.path.dirname(os.path.abspath(__file__)), "otoceviri.py")
    return f'"{pythonw}" "{betik}"'


def _kayitli_komut() -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _ANAHTAR) as k:
            return winreg.QueryValueEx(k, _DEGER_ADI)[0]
    except FileNotFoundError:
        return None


def acik_mi() -> bool:
    return _kayitli_komut() is not None


def ayarla(acik: bool):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _ANAHTAR, 0, winreg.KEY_SET_VALUE) as k:
        if acik:
            winreg.SetValueEx(k, _DEGER_ADI, 0, winreg.REG_SZ, baslatma_komutu())
        else:
            try:
                winreg.DeleteValue(k, _DEGER_ADI)
            except FileNotFoundError:
                pass


def yolu_guncelle():
    """Program (ya da .exe) taşındıysa kayıttaki yolu düzelt."""
    kayitli = _kayitli_komut()
    if kayitli is not None and kayitli != baslatma_komutu():
        ayarla(True)
