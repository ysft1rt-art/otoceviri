"""Açık / koyu / sistem teması: sistem temasını okuma, renkler, başlık çubuğu ve tepsi menüsü."""

import ctypes
import winreg

TEMALAR = {"sistem": "Sistem", "acik": "Açık", "koyu": "Koyu"}

RENKLER = {
    False: {  # açık
        "zemin": "SystemButtonFace", "alan": "#ffffff", "yazi": "#000000",
        "soluk": "#666666", "kenar": "#c8c8c8", "vurgu": "#0067c0", "hata": "#c0392b",
    },
    True: {  # koyu
        "zemin": "#202020", "alan": "#2d2d2d", "yazi": "#e6e6e6", "soluk": "#9a9a9a",
        "kenar": "#3c3c3c", "kutu_kenari": "#7a7a7a",
        "dugme": "#333333", "dugme_uzerinde": "#3d3d3d", "kaydirma": "#5a5a5a",
        "vurgu": "#4c8dde", "hata": "#ff6b6b",
    },
}


def sistem_koyu_mu() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def koyu_mu(tema: str) -> bool:
    if tema == "koyu":
        return True
    if tema == "acik":
        return False
    return sistem_koyu_mu()


def baslik_cubugu(hwnd: int, koyu: bool):
    """Pencerenin başlık çubuğunu koyu/açık yapar (Windows 10 20H1+ / 11)."""
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    deger = ctypes.c_int(1 if koyu else 0)
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(deger), ctypes.sizeof(deger)
        )
        # Başlık çubuğu hemen yeniden çizilsin.
        SWP = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020  # NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|FRAMECHANGED
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP)
    except (AttributeError, OSError):
        pass


def menu_temasi(tema: str):
    """Sağ tık menülerini temaya uydurur. uxtheme'nin belgelenmemiş ama Windows 10 1903'ten
    beri kararlı olan SetPreferredAppMode (135) ve FlushMenuThemes (136) fonksiyonları."""
    mod = {"sistem": 1, "koyu": 2, "acik": 3}[tema]  # AllowDark / ForceDark / ForceLight
    try:
        uxtheme = ctypes.WinDLL("uxtheme")
        uxtheme[135](mod)
        uxtheme[136]()
    except (AttributeError, OSError):
        pass
