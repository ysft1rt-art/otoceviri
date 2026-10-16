"""GitHub'daki son sürümü denetleme, indirme ve kurma.

Kurulum yalnızca derlenmiş .exe'de yapılır. Yeni sürüm geçici bir klasöre açılır
ve oradaki OtoCeviri.exe `--guncellemeyi-kur <kurulu_klasör> <pid>` ile başlatılır:
eski uygulamanın kapanmasını bekler, dosyaları değiştirir ve yeni sürümü açar.
Böylece kurulumu her zaman yeni sürümün kendi kodu yapar. Kurulu klasördeki
ayarlar.json ve log dosyasına dokunulmaz; yalnızca paketteki dosyalar değişir.
"""

import ctypes
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass

from cekirdek import surum
from cekirdek.ceviri import IPv4HTTPSBaglantisi

AD = "OtoCeviri"  # exe ve zip adı; derleme/derle.py ile aynı olmalı
API_URL = surum.GITHUB_URL.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"
KUR_ARGUMANI = "--guncellemeyi-kur"
GECICI_KOK = os.path.join(tempfile.gettempdir(), "OtoCeviri-guncelleme")
_YEDEK_EKI = ".eski"
# Kullanıcıya ait; pakette olsalar bile (ör. kurucunun kendi açtığı boş log) kopyalanmaz.
_KORUNANLAR = {"ayarlar.json", "otoceviri.log"}
_PAKET_DESENI = re.compile(rf"{AD}-[\w.-]+\.zip", re.IGNORECASE)


class GuncellemeHatasi(Exception):
    """anahtar: kullanıcıya gösterilecek metnin metinler.py'deki anahtarı."""

    def __init__(self, anahtar: str, ayrinti=""):
        super().__init__(f"{anahtar}: {ayrinti}")
        self.anahtar = anahtar


@dataclass(frozen=True)
class Guncelleme:
    surum: str
    indirme_url: str
    boyut: int
    sha256: str | None  # GitHub paketin özetini veriyorsa indirilen dosya bununla doğrulanır
    sayfa_url: str


class _IPv4HTTPSIsleyici(urllib.request.HTTPSHandler):
    """Çeviride olduğu gibi: bazı ağlarda IPv6 ile TLS bağlantısı kopuyor."""

    def https_open(self, istek):
        return self.do_open(IPv4HTTPSBaglantisi, istek, context=self._context)


_ACICI = urllib.request.build_opener(_IPv4HTTPSIsleyici())


def _ac(url: str, zaman_asimi: float):
    istek = urllib.request.Request(url, headers={"User-Agent": f"{AD}/{surum.SURUM}"})
    return _ACICI.open(istek, timeout=zaman_asimi)


def surum_demeti(metin: str) -> tuple[int, ...]:
    """'v1.2' -> (1, 2, 0, 0); karşılaştırma için."""
    sayilar = [int(s) for s in re.findall(r"\d+", metin)[:4]]
    return tuple(sayilar + [0] * (4 - len(sayilar)))


def kurulabilir_mi() -> bool:
    """Kaynak koddan çalışırken (python otoceviri.py) güncelleme kurulamaz."""
    return bool(getattr(sys, "frozen", False))


def denetle(zaman_asimi: float = 10) -> Guncelleme | None:
    """Daha yeni bir sürüm yayınlandıysa onu, yoksa None döndürür."""
    try:
        with _ac(API_URL, zaman_asimi) as yanit:
            veri = json.load(yanit)
    except Exception as e:
        raise GuncellemeHatasi("guncelleme_hata_ag", e) from e
    etiket = str(veri.get("tag_name", ""))
    if surum_demeti(etiket) <= surum_demeti(surum.SURUM):
        return None
    for paket in veri.get("assets", []):
        if _PAKET_DESENI.fullmatch(paket.get("name", "")):
            ozet = paket.get("digest") or ""
            return Guncelleme(
                surum=etiket.lstrip("vV"),
                indirme_url=paket["browser_download_url"],
                boyut=int(paket["size"]),
                sha256=ozet.removeprefix("sha256:").lower() if ozet.startswith("sha256:") else None,
                sayfa_url=veri.get("html_url") or surum.GITHUB_URL + "/releases",
            )
    return None  # sürüm açılmış ama zip henüz yüklenmemiş


def indir_ve_baslat(guncelleme: Guncelleme, ilerleme=None):
    """Yeni sürümü indirir, açar ve kurucuyu başlatır. Bu işlev dönünce uygulama
    hemen kapanmalı; kurucu onun kapanmasını bekler. ilerleme(inen, toplam)."""
    kurulu = os.path.dirname(sys.executable)
    try:
        with tempfile.TemporaryFile(dir=kurulu):
            pass
    except OSError as e:
        raise GuncellemeHatasi("guncelleme_hata_yazma", e) from e

    shutil.rmtree(GECICI_KOK, ignore_errors=True)
    acilan = os.path.join(GECICI_KOK, guncelleme.surum)
    zip_yolu = os.path.join(GECICI_KOK, f"{AD}-{guncelleme.surum}.zip")
    try:
        os.makedirs(acilan)
        _indir(guncelleme, zip_yolu, ilerleme)
        with zipfile.ZipFile(zip_yolu) as z:
            z.extractall(acilan)
    except GuncellemeHatasi:
        raise
    except zipfile.BadZipFile as e:
        raise GuncellemeHatasi("guncelleme_hata_bozuk", e) from e
    except Exception as e:
        raise GuncellemeHatasi("guncelleme_hata_ag", e) from e

    yeni_exe = os.path.join(acilan, AD, AD + ".exe")
    if not os.path.isfile(yeni_exe):
        raise GuncellemeHatasi("guncelleme_hata_bozuk", "pakette OtoCeviri.exe yok")
    _baslat([yeni_exe, KUR_ARGUMANI, kurulu, str(os.getpid())], GECICI_KOK)


def _indir(guncelleme: Guncelleme, yol: str, ilerleme):
    ozet = hashlib.sha256()
    inen = 0
    with _ac(guncelleme.indirme_url, 30) as yanit, open(yol, "wb") as f:
        while parca := yanit.read(256 * 1024):
            f.write(parca)
            ozet.update(parca)
            inen += len(parca)
            if ilerleme:
                ilerleme(inen, guncelleme.boyut)
    if inen != guncelleme.boyut or (guncelleme.sha256 and ozet.hexdigest() != guncelleme.sha256):
        raise GuncellemeHatasi("guncelleme_hata_bozuk", f"{inen}/{guncelleme.boyut} bayt, özet tutmadı")


def _baslat(komut: list[str], dizin: str):
    """Başka bir .exe'yi bağımsız başlatır. PyInstaller'a, bu sürecin ortam
    değişkenlerini (kendi _internal yolları) yeni sürece taşımamasını söyler."""
    ortam = {k: v for k, v in os.environ.items()
             if not k.startswith("_PYI") and k not in ("TCL_LIBRARY", "TK_LIBRARY")}
    ortam["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    subprocess.Popen(
        komut, cwd=dizin, env=ortam, close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )


# ---------------------------------------------------------------- Kurucu (yeni sürüm)

def kur(kurulu: str, eski_pid: int):
    """Geçici klasördeki yeni exe bu işlevle çalışır: eski sürüm kapanınca
    dosyalarını değiştirir, sonra kurulu klasördeki exe'yi başlatır. Bir şey
    ters giderse eski dosyalar geri konur ve eski sürüm açılır."""
    kaynak = os.path.dirname(sys.executable)
    kayit = logging.getLogger()
    kayit.handlers.clear()  # geçici klasöre değil, kurulu klasördeki loga yaz
    kayit.addHandler(logging.FileHandler(os.path.join(kurulu, "otoceviri.log"), encoding="utf-8"))

    if not _surecin_bitmesini_bekle(eski_pid, 30):
        logging.warning("Güncelleme kurulmadı: eski sürüm kapanmadı")
        return

    tasinanlar = []  # (asıl yol, yedeği ya da None)
    try:
        for ad in os.listdir(kaynak):
            if ad.lower() in _KORUNANLAR:
                continue
            asil = os.path.join(kurulu, ad)
            yedek = asil + _YEDEK_EKI
            _sil(yedek)
            if os.path.lexists(asil):
                _tekrarla(os.replace, asil, yedek)
                tasinanlar.append((asil, yedek))
            else:
                tasinanlar.append((asil, None))
            yeni = os.path.join(kaynak, ad)
            if os.path.isdir(yeni):
                shutil.copytree(yeni, asil)
            else:
                shutil.copy2(yeni, asil)
    except Exception:
        logging.exception("Güncelleme kurulamadı; eski sürüme dönülüyor")
        for asil, yedek in reversed(tasinanlar):
            try:
                _sil(asil)
                if yedek:
                    _tekrarla(os.replace, yedek, asil)
            except Exception:
                logging.exception("Geri alınamadı: %s", asil)
    else:
        for _, yedek in tasinanlar:
            if yedek:
                _sil(yedek)
    _baslat([os.path.join(kurulu, AD + ".exe")], kurulu)


def artiklari_temizle():
    """Güncellemeden sonra açılan yeni sürüm çağırır: geçici klasörü ve silinemeyen
    yedekleri kaldırır. Kurucu birkaç saniye daha açık olabileceği için gecikmeli."""
    if not kurulabilir_mi():
        return
    time.sleep(15)
    shutil.rmtree(GECICI_KOK, ignore_errors=True)
    kurulu = os.path.dirname(sys.executable)
    for ad in os.listdir(kurulu):
        if ad.endswith(_YEDEK_EKI):
            _sil(os.path.join(kurulu, ad))


def _surecin_bitmesini_bekle(pid: int, saniye: float) -> bool:
    SYNCHRONIZE, WAIT_OBJECT_0 = 0x00100000, 0
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    tutamac = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not tutamac:
        return True  # süreç zaten yok
    try:
        return kernel32.WaitForSingleObject(ctypes.c_void_p(tutamac), int(saniye * 1000)) == WAIT_OBJECT_0
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(tutamac))


def _tekrarla(islev, *argumanlar, deneme=10):
    """Antivirüs yeni açılan dosyayı kısa süre kilitleyebiliyor; birkaç kez dene."""
    for i in range(deneme):
        try:
            return islev(*argumanlar)
        except PermissionError:
            if i == deneme - 1:
                raise
            time.sleep(0.5)


def _sil(yol: str):
    if os.path.isdir(yol) and not os.path.islink(yol):
        shutil.rmtree(yol, ignore_errors=True)
    else:
        try:
            os.remove(yol)
        except FileNotFoundError:
            pass
        except OSError:
            logging.warning("Silinemedi: %s", yol)
