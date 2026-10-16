"""Çeviri yapıldığını belli eden kısa ses. Dosya gerekmez; WAV bellekte üretilir."""

import io
import math
import struct
import threading
import wave
import winsound

_ORNEKLEME = 44100
_NOTALAR = ((880.0, 0.0), (1318.5, 0.055))  # (frekans Hz, başlama sn): La5 → Mi6
_NOTA_SURESI = 0.11  # saniye
_SES_DUZEYI = 0.18  # 0–1; yazarken rahatsız etmesin diye kısık


def _wav_uret() -> bytes:
    """Yumuşak, iki notalı bir "tın-tın": her nota hızlı yükselir, üstel söner."""
    toplam = int(_ORNEKLEME * (_NOTALAR[-1][1] + _NOTA_SURESI))
    ornekler = []
    for i in range(toplam):
        sn = i / _ORNEKLEME
        deger = 0.0
        for frekans, baslangic in _NOTALAR:
            gecen = sn - baslangic
            if 0 <= gecen < _NOTA_SURESI:
                zarf = min(1.0, gecen / 0.004) * math.exp(-gecen * 38)  # tık sesi olmasın
                deger += math.sin(2 * math.pi * frekans * gecen) * zarf
        ornekler.append(int(max(-1.0, min(1.0, deger * _SES_DUZEYI)) * 32767))
    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_ORNEKLEME)
        w.writeframes(struct.pack(f"<{len(ornekler)}h", *ornekler))
    return tampon.getvalue()


_WAV = _wav_uret()


def ceviri_sesi():
    """Beklemeden döner. winsound bellekteki sesi eşzamansız çalamadığı için ayrı iş
    parçacığında çalınır."""
    threading.Thread(
        target=lambda: winsound.PlaySound(_WAV, winsound.SND_MEMORY | winsound.SND_NODEFAULT),
        daemon=True,
    ).start()
