"""Google Translate ile çeviri ve yazım tarzını koruma."""

import http.client
import json
import re
import socket
import unicodedata
import urllib.parse
import urllib.request

# Biri yanıt vermezse sıradakine geçilir.
GOOGLE_URLLERI = [
    "https://translate.googleapis.com/translate_a/single",
    "https://translate.google.com/translate_a/single",
]

# Hedef dil kodları (Google Translate). Arayüzde görünen adları metinler.py'de.
DILLER = ("en", "de", "fr", "es", "it", "pt", "nl", "ru", "ar", "ja", "ko", "zh-CN", "tr")

_URL_DESENI = re.compile(r"^\s*(https?://|www\.)\S+\s*$", re.IGNORECASE)
_SON_NOKTALAMA = ".!?…"


class CeviriHatasi(Exception):
    pass


class _IPv4HTTPSBaglantisi(http.client.HTTPSConnection):
    """Bazı ağlarda Google'a IPv6 ile TLS bağlantısı kopuyor; IPv4 kullan."""

    def connect(self):
        adres = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)[0][4]
        sok = socket.create_connection(adres, self.timeout)
        self.sock = self._context.wrap_socket(sok, server_hostname=self.host)


class _IPv4HTTPSIsleyici(urllib.request.HTTPSHandler):
    def https_open(self, istek):
        return self.do_open(_IPv4HTTPSBaglantisi, istek, context=self._context)


_ACICI = urllib.request.build_opener(_IPv4HTTPSIsleyici())


def cevrilmeli_mi(metin: str) -> bool:
    """Çevirmenin anlamsız ya da zararlı olacağı metinleri ayıklar."""
    yalin = metin.strip()
    if not yalin:
        return False
    if yalin.startswith("/"):  # Discord / oyun komutları
        return False
    if _URL_DESENI.match(yalin):
        return False
    return any(ch.isalpha() for ch in yalin)


def google_cevir(metin: str, hedef: str, zaman_asimi: float = 4.0) -> tuple[str, str]:
    """(çeviri, algılanan_kaynak_dil) döndürür."""
    veri = urllib.parse.urlencode(
        {"client": "gtx", "sl": "auto", "tl": hedef, "dt": "t", "q": metin}
    ).encode("utf-8")
    son_hata = None
    for url in GOOGLE_URLLERI:
        istek = urllib.request.Request(
            url,
            data=veri,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            },
        )
        try:
            with _ACICI.open(istek, timeout=zaman_asimi) as yanit:
                sonuc = json.loads(yanit.read().decode("utf-8"))
            break
        except Exception as e:
            son_hata = e
    else:
        raise CeviriHatasi(str(son_hata)) from son_hata

    try:
        ceviri = "".join(parca[0] for parca in sonuc[0] if parca and parca[0])
        kaynak = sonuc[2] if len(sonuc) > 2 and isinstance(sonuc[2], str) else ""
    except (TypeError, IndexError) as e:
        raise CeviriHatasi("Beklenmeyen yanıt biçimi") from e
    return ceviri, kaynak


def _kucult(metin: str, hedef: str) -> str:
    if hedef == "tr":
        metin = metin.replace("I", "ı").replace("İ", "i")
    return metin.lower()


def tarzi_koru(orijinal: str, ceviri: str, hedef: str) -> str:
    """Çeviriyi, kullanıcının yazış alışkanlıklarına göre düzeltir."""
    harfler = [ch for ch in orijinal if ch.isalpha() and ch.lower() != ch.upper()]
    govde = ceviri.strip()

    # Hepsi küçük harfle yazdıysa çeviri de küçük harf olsun.
    if harfler and not any(ch.isupper() for ch in harfler):
        govde = _kucult(govde, hedef)
    # Bağırarak (hepsi büyük) yazdıysa çeviri de büyük harf olsun.
    elif len(harfler) >= 3 and all(ch.isupper() for ch in harfler):
        govde = govde.upper()

    # Sonuna nokta koymadıysa Google'ın eklediği noktayı sil.
    yalin = orijinal.rstrip()
    if yalin and yalin[-1] not in _SON_NOKTALAMA:
        if govde.endswith(".") and not govde.endswith(".."):
            govde = govde[:-1]

    bas = orijinal[: len(orijinal) - len(orijinal.lstrip())]
    son = orijinal[len(orijinal.rstrip()):]
    return bas + govde + son


def _sus_mu(ch: str) -> bool:
    """Emoji ya da boşluk mu? (Google baştaki/sondaki emojileri silebiliyor.)"""
    return ch.isspace() or ch in "‍️⃣" or unicodedata.category(ch) in ("So", "Sk")


def _suslari_ayir(metin: str) -> tuple[str, str, str]:
    """'😄 selam 👋' -> ('😄 ', 'selam', ' 👋')"""
    bas = 0
    while bas < len(metin) and _sus_mu(metin[bas]):
        bas += 1
    son = len(metin)
    while son > bas and _sus_mu(metin[son - 1]):
        son -= 1
    return metin[:bas], metin[bas:son], metin[son:]


def cevir(metin: str, hedef: str) -> str | None:
    """Çevrilmiş metni döndürür; değişiklik gerekmiyorsa None döndürür."""
    if not cevrilmeli_mi(metin):
        return None
    on_ek, govde, son_ek = _suslari_ayir(metin)
    ceviri, kaynak = google_cevir(govde, hedef)
    if not ceviri or kaynak.lower() == hedef.lower():
        return None
    sonuc = on_ek + tarzi_koru(govde, ceviri, hedef) + son_ek
    return None if sonuc == metin else sonuc


if __name__ == "__main__":
    # Deneme: python ceviri.py en "naber kanka nasılsın"
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        print('Kullanım: python ceviri.py <dil> "metin"')
        sys.exit(1)
    print(cevir(" ".join(sys.argv[2:]), sys.argv[1]) or "(çeviri gerekmedi)")
