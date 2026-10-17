"""Google Translate ile çeviri ve yazım tarzını koruma."""

import collections
import functools
import http.client
import json
import queue
import re
import socket
import ssl
import statistics
import threading
import time
import unicodedata
import urllib.parse

# Biri yanıt vermezse sıradakine geçilir.
GOOGLE_SUNUCULARI = ("translate.googleapis.com", "translate.google.com")
_YOL = "/translate_a/single"
_BASLIKLAR = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
}

# Google boşta kalan bağlantıyı bir süre sonra kapatıyor. Bundan uzun süre
# kullanılmamış bağlantıya güvenmeyip yenisini kuruyoruz; yoksa kapanmış
# bağlantıda hatayı (ya da zaman aşımını) beklemek gerekirdi.
BOSTA_SINIRI = 200  # sn; Google ~240 sn sonra kapatıyor (ölçüldü)
_ISINMA_ARALIGI = 5  # sn; ağ yokken her tuşta bağlanmayı denemesin

# Google arada bir isteği ~1 sn bekletiyor (ölçüldü). Ana sunucu olağan süresinin
# birkaç katında yanıt vermezse aynı istek yedek sunucuya da gönderilir; önce gelen
# yanıt kullanılır. Olağan süre ağa göre değiştiği için son isteklerden öğrenilir.
_YEDEK_EN_AZ_BEKLEME = 0.3  # sn
_SON_SURELER = collections.deque(maxlen=9)  # sn; açık bağlantıdaki başarılı istekler

# Hedef dil kodları (Google Translate). Arayüzde görünen adları metinler.py'de.
DILLER = ("en", "de", "fr", "es", "it", "pt", "nl", "ru", "ar", "ja", "ko", "zh-CN", "tr")

_URL_DESENI = re.compile(r"^\s*(https?://|www\.)\S+\s*$", re.IGNORECASE)
_SON_NOKTALAMA = ".!?…"


class CeviriHatasi(Exception):
    pass


class IPv4HTTPSBaglantisi(http.client.HTTPSConnection):
    """Bazı ağlarda Google'a IPv6 ile TLS bağlantısı kopuyor; IPv4 kullan."""

    def connect(self):
        adres = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)[0][4]
        sok = socket.create_connection(adres, self.timeout)
        # http.client başlıkları ve gövdeyi ayrı gönderir. Nagle açıkken gövde,
        # başlıkların onayını bekliyor ve her istek bir tur (~95 ms) uzuyordu.
        # Asıl connect() bunu kendisi açıyor; onu ezdiğimiz için burada açmalıyız.
        sok.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock = self._context.wrap_socket(sok, server_hostname=self.host)


class _KaliciBaglanti:
    """Bir sunucuya açık tutulan HTTPS bağlantısı (keep-alive). Her çeviride
    TCP + TLS'i baştan kurmak isteği ~150 ms uzatıyordu."""

    def __init__(self, sunucu: str):
        self.sunucu = sunucu
        self._baglanti = None
        self._son_kullanim = 0.0
        self._son_isinma = -_ISINMA_ARALIGI
        self._kilit = threading.Lock()

    def taze_mi(self) -> bool:
        return (
            self._baglanti is not None
            and self._baglanti.sock is not None  # sunucu "Connection: close" dediyse None
            and time.monotonic() - self._son_kullanim < BOSTA_SINIRI
        )

    def isinmali_mi(self) -> bool:
        return (
            not self.taze_mi()
            and not self._kilit.locked()
            and time.monotonic() - self._son_isinma >= _ISINMA_ARALIGI
        )

    def _kapat(self):
        if self._baglanti is not None:
            self._baglanti.close()
            self._baglanti = None

    def _ac(self, zaman_asimi: float):
        self._kapat()
        baglanti = IPv4HTTPSBaglantisi(self.sunucu, timeout=zaman_asimi, context=_SSL_BAGLAMI)
        baglanti.connect()
        self._baglanti = baglanti
        self._son_kullanim = time.monotonic()

    def isit(self, zaman_asimi: float):
        """Bağlantıyı önceden kurar; bu sırada gelen çeviri bitmesini bekler."""
        if not self._kilit.acquire(blocking=False):
            return  # zaten bağlanılıyor ya da çeviri yapılıyor
        try:
            self._son_isinma = time.monotonic()
            if not self.taze_mi():
                self._ac(zaman_asimi)
        finally:
            self._kilit.release()

    def gonder(self, govde: bytes, zaman_asimi: float) -> bytes:
        with self._kilit:
            yeniden_kullanim = self.taze_mi()
            if not yeniden_kullanim:
                self._kapat()
            # Eski bağlantıyı sunucu biz fark etmeden kapatmış olabilir: öyleyse
            # bir kez de yeni bağlantıyla dene. Zaman aşımında tekrar bekletme.
            for son_deneme in (not yeniden_kullanim, True):
                try:
                    if self._baglanti is None:
                        self._ac(zaman_asimi)
                    return self._istek(govde, zaman_asimi)
                except Exception as e:
                    self._kapat()
                    if son_deneme or isinstance(e, (TimeoutError, CeviriHatasi)):
                        raise

    def _istek(self, govde: bytes, zaman_asimi: float) -> bytes:
        baglanti = self._baglanti
        baglanti.sock.settimeout(zaman_asimi)
        baslangic = time.monotonic()
        baglanti.request("POST", _YOL, body=govde, headers=_BASLIKLAR)
        yanit = baglanti.getresponse()
        veri = yanit.read()  # bağlantı yeniden kullanılabilsin diye tamamı okunur
        self._son_kullanim = time.monotonic()
        if yanit.status != 200:
            raise CeviriHatasi(f"HTTP {yanit.status}")
        _SON_SURELER.append(self._son_kullanim - baslangic)
        return veri


_SSL_BAGLAMI = ssl.create_default_context()
_BAGLANTILAR = [_KaliciBaglanti(s) for s in GOOGLE_SUNUCULARI]


def isit(zaman_asimi: float = 4.0):
    """İlk çeviri beklemesin diye Google bağlantılarını önceden kurar; yedeğinkini de,
    gerektiğinde yarışa hazır girsin. Hata vermez; bağlanamazsa çeviri sırasında
    yeniden denenir."""
    for baglanti in _BAGLANTILAR:
        try:
            baglanti.isit(zaman_asimi)
        except Exception:
            pass


def isinmali_mi() -> bool:
    """Bir bağlantı soğumuş ve şu an kurulmuyorsa True (klavye kancasında çağrılır: hızlı)."""
    return any(baglanti.isinmali_mi() for baglanti in _BAGLANTILAR)


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


def _yedek_beklemesi(baglanti: _KaliciBaglanti) -> float:
    """Bu bağlantıdan yanıt ne kadar beklenince yedek sunucu da denensin?"""
    olagan = statistics.median(_SON_SURELER) if _SON_SURELER else 0.15
    bekleme = max(_YEDEK_EN_AZ_BEKLEME, 2.5 * olagan)
    if not baglanti.taze_mi():
        bekleme += 2 * olagan  # önce TCP + TLS kurulacak (~iki tur)
    return bekleme


def _yarisarak_gonder(veri: bytes, zaman_asimi: float):
    """İsteği ana sunucuya gönderir; hata alınırsa ya da yanıt gecikirse aynısını
    sıradaki sunucuya da gönderir. İlk gelen geçerli yanıtı (JSON) döndürür."""
    sonuclar = queue.SimpleQueue()

    def gonder(baglanti):
        try:
            sonuclar.put((json.loads(baglanti.gonder(veri, zaman_asimi).decode("utf-8")), None))
        except Exception as e:
            sonuclar.put((None, e))

    bekleyen, son_hata = 0, None
    for sira, baglanti in enumerate(_BAGLANTILAR):
        sonuncu = sira == len(_BAGLANTILAR) - 1
        bekleme = None if sonuncu else _yedek_beklemesi(baglanti)
        threading.Thread(target=gonder, args=(baglanti,), daemon=True).start()
        bekleyen += 1
        while bekleyen:
            try:
                yanit, hata = sonuclar.get(timeout=bekleme)
            except queue.Empty:
                break  # gecikti: yanıtını beklemeyi sürdürürken yedeği de dene
            bekleyen -= 1
            if hata is None:
                return yanit
            son_hata = hata
    raise CeviriHatasi(str(son_hata)) from son_hata


def google_cevir(metin: str, hedef: str, zaman_asimi: float = 4.0) -> tuple[str, str]:
    """(çeviri, algılanan_kaynak_dil) döndürür."""
    veri = urllib.parse.urlencode(
        {"client": "gtx", "sl": "auto", "tl": hedef, "dt": "t", "q": metin}
    ).encode("utf-8")
    sonuc = _yarisarak_gonder(veri, zaman_asimi)

    try:
        ceviri = "".join(parca[0] for parca in sonuc[0] if parca and parca[0])
        kaynak = sonuc[2] if len(sonuc) > 2 and isinstance(sonuc[2], str) else ""
    except (TypeError, IndexError) as e:
        raise CeviriHatasi("Beklenmeyen yanıt biçimi") from e
    return ceviri, kaynak


# "Tamam", "teşekkürler" gibi sık yazılan metinler için Google'a tekrar gitme.
# Yalnızca bellekte tutulur; hatalar önbelleğe girmez.
_onbellekli_cevir = functools.lru_cache(maxsize=256)(google_cevir)


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
    ceviri, kaynak = _onbellekli_cevir(govde, hedef)
    if not ceviri or kaynak.lower() == hedef.lower():
        return None
    sonuc = on_ek + tarzi_koru(govde, ceviri, hedef) + son_ek
    return None if sonuc == metin else sonuc


if __name__ == "__main__":
    # Deneme: python -m cekirdek.ceviri en "naber kanka nasılsın"
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        print('Kullanım: python -m cekirdek.ceviri <dil> "metin"')
        sys.exit(1)
    print(cevir(" ".join(sys.argv[2:]), sys.argv[1]) or "(çeviri gerekmedi)")
