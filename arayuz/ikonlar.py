"""Menü ve pencere ikonları: Windows'un kendi ikon yazı tipinden (Segoe Fluent Icons,
Windows 10'da Segoe MDL2 Assets) çizilir. Böylece sistemle aynı görünür ve açık/koyu
temaya göre istenen renkte çizilebilir. Yazı tipi yoksa ikonlar sessizce atlanır."""

import ctypes
import ctypes.wintypes as wt
import functools

from PIL import Image, ImageDraw, ImageFont

GLIFLER = {
    "guncelleme": "\ue896",    # aşağı ok
    "guc": "\ue7e8",           # aç/kapat
    "dil": "\ue774",           # dünya
    "arayuz_dili": "\ue8d2",   # Aa
    "mod": "\ue8ab",           # karşılıklı oklar
    "klavye": "\ue765",
    "enter": "\ue751",
    "bilgisayar": "\ue7f4",
    "ses": "\ue767",           # hoparlör
    "ayarlar": "\ue713",
    "bilgi": "\ue946",
    "cikis": "\ue711",
    "genel": "\ue9e9",         # kaydırıcılar
    "tema": "\ue790",          # palet
    "cevir": "\ue8c1",         # A字
    "geri_al": "\ue7a7",
    "engel": "\ue733",
    "duzenle": "\ue70f",
    "kaydet": "\ue74e",
    "iptal": "\ue711",
    "yenile": "\ue895",
    "kod": "\ue943",
    "belge": "\ue8a5",
    "tik": "\ue73e",           # i\u015faretli men\u00fc \u00f6\u011fesi
}

_YAZI_TIPLERI = ("SegoeIcons.ttf", "segmdl2.ttf")


@functools.lru_cache(maxsize=8)
def _yazi_tipi(boyut: int):
    for ad in _YAZI_TIPLERI:
        try:
            return ImageFont.truetype(ad, boyut)
        except OSError:
            pass
    return None


def var_mi() -> bool:
    return _yazi_tipi(16) is not None


@functools.lru_cache(maxsize=256)
def resim(ad: str, renk: str, boyut: int = 16) -> Image.Image | None:
    """Saydam zeminli kare ikon; yazı tipi yoksa None."""
    yazi_tipi = _yazi_tipi(boyut)
    if yazi_tipi is None:
        return None
    sonuc = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
    # Glifler yazı tipinde boyut x boyut kareye oturacak şekilde tasarlanmış.
    ImageDraw.Draw(sonuc).text((0, 0), GLIFLER[ad], font=yazi_tipi, fill=renk)
    return sonuc


# ---------------------------------------------------------------- Win32 menü bitmap'i

class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD),
    ]


_gdi32 = ctypes.WinDLL("gdi32")
_gdi32.CreateDIBSection.restype = wt.HBITMAP
_gdi32.CreateDIBSection.argtypes = [
    wt.HDC, ctypes.c_void_p, wt.UINT, ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD,
]

MENU_RENKLERI = {False: "#1b1b1b", True: "#f2f2f2"}  # açık / koyu menü


def menu_boyutu() -> int:
    """Küçük simge boyutu (100% ölçekte 16 px); DPI'a göre büyür."""
    return ctypes.windll.user32.GetSystemMetrics(49) or 16  # SM_CXSMICON


def isaretli_resim(ad: str, koyu: bool, boyut: int, isaretli: bool) -> Image.Image | None:
    """İşaretlenebilir menü öğesi: solda tik yeri, sağında ikon. Windows, resmi olan
    öğede tik işaretini çizmediği için tik resmin içine çiziliyor. İşaretsizken tik
    yeri boş kalır ki aynı menüdeki ikonlar hizalı dursun."""
    renk = MENU_RENKLERI[koyu]
    ikon = resim(ad, renk, boyut)
    if ikon is None:
        return None
    bosluk = max(2, boyut // 4)
    sonuc = Image.new("RGBA", (2 * boyut + bosluk, boyut), (0, 0, 0, 0))
    if isaretli:
        sonuc.alpha_composite(resim("tik", renk, boyut))
    sonuc.alpha_composite(ikon, (boyut + bosluk, 0))
    return sonuc


@functools.lru_cache(maxsize=64)
def menu_bitmapi(ad: str, koyu: bool, isaret: bool | None = None):
    """Menü öğesine konacak 32 bit, saydam HBITMAP. isaret None değilse öğe işaretlenebilir
    sayılır ve tik yeri eklenir (bkz. isaretli_resim). Menü yeniden kurulsa da aynı
    tutamaç kullanılır; sayıları az olduğu için hiç silinmez."""
    boyut = menu_boyutu()
    if isaret is None:
        ikon = resim(ad, MENU_RENKLERI[koyu], boyut)
    else:
        ikon = isaretli_resim(ad, koyu, boyut, isaret)
    if ikon is None:
        return None
    r, g, b, a = ikon.split()
    veri = bytes(_on_carp(Image.merge("RGBA", (b, g, r, a)).tobytes()))

    baslik = _BITMAPINFOHEADER(
        biSize=ctypes.sizeof(_BITMAPINFOHEADER), biWidth=ikon.width, biHeight=-ikon.height,  # yukarıdan aşağı
        biPlanes=1, biBitCount=32, biCompression=0,
    )
    bitler = ctypes.c_void_p()
    hbitmap = _gdi32.CreateDIBSection(None, ctypes.byref(baslik), 0, ctypes.byref(bitler), None, 0)
    if not hbitmap:
        return None
    ctypes.memmove(bitler, veri, len(veri))
    return hbitmap


def _on_carp(bgra: bytes):
    """GDI, alfası önceden çarpılmış (premultiplied) renk ister."""
    for i in range(0, len(bgra), 4):
        a = bgra[i + 3]
        yield bgra[i] * a // 255
        yield bgra[i + 1] * a // 255
        yield bgra[i + 2] * a // 255
        yield a
