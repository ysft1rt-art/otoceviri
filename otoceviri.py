"""OtoÇeviri — yazdığın her şeyi seçtiğin dile çeviren sistem tepsisi uygulaması.

Enter modu : Açıkken Enter'a bastığında yazı kutusundaki metin çevrilir ve gönderilir.
Kısayol modu: Kısayola bastığında seçili metin (seçim yoksa kutunun tamamı) çevrilir.
Geri al     : Kısayol modundaki son çeviriyi orijinal metne döndürür.
"""

import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import sys
import threading
import time
import unicodedata
import winsound

import keyboard
import pyperclip
import pystray
from PIL import Image, ImageDraw, ImageFont

import ayarlar_penceresi
import hakkinda_penceresi
import pencere
import baslangic
import ceviri
import kisayollar
import metinler
import tema
from kisayollar import DEGISTIRICILER
from metinler import t

if getattr(sys, "frozen", False):
    UYGULAMA_DIZINI = os.path.dirname(sys.executable)
else:
    UYGULAMA_DIZINI = os.path.dirname(os.path.abspath(__file__))

AYAR_DOSYASI = os.path.join(UYGULAMA_DIZINI, "ayarlar.json")
LOG_DOSYASI = os.path.join(UYGULAMA_DIZINI, "otoceviri.log")

VARSAYILAN_AYARLAR = {
    "hedef_dil": "en",
    "enter_modu": True,
    "kisayol_modu": True,
    "ac_kapa_kisayolu": "ctrl+shift+y",
    "cevir_kisayolu": "ctrl+shift+u",
    "geri_al_kisayolu": "ctrl+shift+z",
    "acilista_aktif": False,
    "tema": "sistem",  # sistem / acik / koyu
    "arayuz_dili": "sistem",  # sistem / tr / en
    # Bu programlarda Enter normal çalışır (belge/tablo/terminal bozulmasın diye).
    # Kısayol modu bunlarda da çalışır.
    "enter_haric_programlar": [
        "excel.exe", "winword.exe", "powerpnt.exe", "onenote.exe",
        "notepad.exe", "notepad++.exe", "code.exe", "devenv.exe",
        "windowsterminal.exe", "cmd.exe", "powershell.exe", "pwsh.exe",
        "explorer.exe", "searchhost.exe", "keepass.exe", "1password.exe",
        "bitwarden.exe",
    ],
}

# Kullanıcının yazdığı metinler asla log dosyasına yazılmaz; yalnızca hatalar.
logging.basicConfig(
    filename=LOG_DOSYASI,
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)


# ---------------------------------------------------------------- Windows yardımcıları

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.OpenProcess.restype = wt.HANDLE
_kernel32.CreateMutexW.restype = wt.HANDLE
_user32.GetForegroundWindow.restype = wt.HWND
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_ALREADY_EXISTS = 183


def on_plandaki_pencere() -> int:
    return _user32.GetForegroundWindow() or 0


def on_plandaki_pid() -> int:
    pid = wt.DWORD()
    _user32.GetWindowThreadProcessId(on_plandaki_pencere(), ctypes.byref(pid))
    return pid.value


def on_plandaki_program() -> str:
    """Odaktaki pencerenin program adını (ör. 'discord.exe') döndürür."""
    pid = on_plandaki_pid()
    if not pid:
        return ""
    h = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        boyut = wt.DWORD(1024)
        tampon = ctypes.create_unicode_buffer(boyut.value)
        if _kernel32.QueryFullProcessImageNameW(h, 0, tampon, ctypes.byref(boyut)):
            return os.path.basename(tampon.value).lower()
        return ""
    finally:
        _kernel32.CloseHandle(h)


_GEZINME_TUSLARI = {"left": (0x25, 0x4B), "right": (0x27, 0x4D), "end": (0x23, 0x4F)}
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x1, 0x2


def gezinme_tusu(ad: str):
    """Ok/End tuşunu 'genişletilmiş tuş' olarak gönderir. keyboard.send('left') bu
    bayrağı koymadığı için Windows onu sayısal tuş takımındaki 4 sanıyor; NumLock
    açıkken Shift+Sol metni seçmiyor, yalnızca imleci kaydırıyor."""
    vk, tarama = _GEZINME_TUSLARI[ad]
    _user32.keybd_event(vk, tarama, KEYEVENTF_EXTENDEDKEY, 0)
    _user32.keybd_event(vk, tarama, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def tek_ornek_kilidi():
    """İkinci kez açılırsa None döndürür."""
    kilit = _kernel32.CreateMutexW(None, False, "Local\\OtoCeviriTekOrnek")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return None
    return kilit


def bip(yuksek: bool):
    threading.Thread(
        target=lambda: winsound.Beep(1200 if yuksek else 600, 90), daemon=True
    ).start()


def imlec_adimi(metin: str) -> int:
    """Metnin üzerinden geçmek için kaç kez sol ok tuşuna basılacağını tahmin eder.
    Birleşik emojiler (ten rengi, aile emojileri, bayraklar) tek adımdır. Tahmin
    yanlışsa geri alma zaten seçimi doğrulayıp vazgeçer."""
    adim, zwj_sonrasi, bolge = 0, False, 0
    for ch in metin.replace("\r\n", "\n"):
        if zwj_sonrasi:
            zwj_sonrasi = False
            continue
        if ch == "\u200d":  # sıfır genişlikli birleştirici
            zwj_sonrasi = True
            continue
        if (unicodedata.category(ch) in ("Mn", "Me") or ch in "\ufe0e\ufe0f"
                or 0x1F3FB <= ord(ch) <= 0x1F3FF):
            continue
        if 0x1F1E6 <= ord(ch) <= 0x1F1FF:  # bayrak = iki bölge harfi
            bolge += 1
            if bolge % 2 == 0:
                continue
        adim += 1
    return adim


# ---------------------------------------------------------------- Pano

def pano_oku() -> str:
    for _ in range(5):
        try:
            return pyperclip.paste() or ""
        except Exception:
            time.sleep(0.03)
    return ""


def pano_yaz(metin: str):
    for _ in range(5):
        try:
            pyperclip.copy(metin)
            return
        except Exception:
            time.sleep(0.03)


# ---------------------------------------------------------------- Uygulama

GERI_AL_SURESI = 300  # saniye; bundan eski çeviriler geri alınamaz


class OtoCeviri:
    def __init__(self):
        self.ayarlar = self._ayarlari_yukle()
        self.aktif = bool(self.ayarlar["acilista_aktif"])
        self.kayit_modu = False  # ayarlar penceresi kısayol kaydederken kancalar susar
        self._gecir = False  # kendi gönderdiğimiz Enter'ı tekrar yakalamamak için
        self._mesgul = threading.Lock()
        self._kisayol_kaldiricilar = []
        self._son_ceviri = None  # geri alma için: {pencere, orijinal, ceviri, zaman}
        self.simge = None

    # ---- ayarlar

    def _ayarlari_yukle(self) -> dict:
        ayarlar = dict(VARSAYILAN_AYARLAR)
        try:
            with open(AYAR_DOSYASI, encoding="utf-8") as f:
                ayarlar.update(json.load(f))
        except FileNotFoundError:
            pass
        except Exception:
            logging.exception("Ayar dosyası okunamadı, varsayılanlar kullanılıyor")
        if ayarlar["hedef_dil"] not in ceviri.DILLER:
            ayarlar["hedef_dil"] = "en"
        if ayarlar["tema"] not in tema.TEMALAR:
            ayarlar["tema"] = "sistem"
        if ayarlar["arayuz_dili"] not in metinler.ARAYUZ_DILLERI:
            ayarlar["arayuz_dili"] = "sistem"
        metinler.ayarla(ayarlar["arayuz_dili"])
        for anahtar in ("ac_kapa_kisayolu", "cevir_kisayolu", "geri_al_kisayolu"):
            normal, hata = kisayollar.normallestir(str(ayarlar[anahtar]))
            ayarlar[anahtar] = normal or VARSAYILAN_AYARLAR[anahtar]
        self._ayarlari_kaydet(ayarlar)
        return ayarlar

    def _ayarlari_kaydet(self, ayarlar=None):
        try:
            with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(ayarlar or self.ayarlar, f, ensure_ascii=False, indent=2)
        except Exception:
            logging.exception("Ayar dosyası kaydedilemedi")

    def ayarlari_uygula(self, yeni: dict, windows_acilisinda: bool):
        """Ayarlar penceresinden çağrılır."""
        self.ayarlar = yeni
        metinler.ayarla(yeni["arayuz_dili"])
        self._ayarlari_kaydet()
        self.kisayollari_kur()
        if windows_acilisinda != baslangic.acik_mi():
            baslangic.ayarla(windows_acilisinda)
        tema.menu_temasi(self.ayarlar["tema"])
        self._simgeyi_guncelle()

    def _sistem_temasini_izle(self):
        """'Sistem' temasında Windows açık/koyu değişince tepsi menüsü de değişsin."""
        onceki = tema.sistem_koyu_mu()
        while True:
            time.sleep(2)
            simdiki = tema.sistem_koyu_mu()
            if simdiki != onceki and self.ayarlar["tema"] == "sistem":
                tema.menu_temasi("sistem")
            onceki = simdiki

    # ---- açma / kapama

    def ac_kapa(self, *_):
        self.aktif = not self.aktif
        bip(self.aktif)
        self._simgeyi_guncelle()

    # ---- klavye kancaları

    def kisayollari_kur(self):
        for kaldir in self._kisayol_kaldiricilar:
            try:
                kaldir()
            except (KeyError, ValueError):
                pass
        a = self.ayarlar
        self._kisayol_kaldiricilar = [
            self._kisayol_kancasi(a["ac_kapa_kisayolu"], self.ac_kapa, lambda: True),
            self._kisayol_kancasi(
                a["cevir_kisayolu"],
                self._kisayol_isle,
                lambda: self.aktif and self.ayarlar["kisayol_modu"] and not self._mesgul.locked(),
            ),
            # Geri alınacak bir şey yoksa kısayol programın kendisine gider
            # (ör. Ctrl+Shift+Z = yinele).
            self._kisayol_kancasi(a["geri_al_kisayolu"], self._geri_al_isle, self._geri_alinabilir),
        ]

    def _kisayol_kancasi(self, kisayol: str, islev, etkin_mi):
        """Kısayolu yakalar ve son tuşunu yutar; böylece odaktaki programa ulaşmaz
        (ör. Discord'da Ctrl+Shift+U dosya seçme penceresini açmaz).

        keyboard.add_hotkey(suppress=True) değiştirici tuşları geciktirip bozduğu için
        yalnızca son tuşu engelliyoruz; Ctrl/Shift tek başına bir şey yapmaz.
        Kaldırma fonksiyonu döndürür.
        """
        tus, gerekli = kisayollar.ayristir(kisayol)
        basili = False

        def kanca(olay) -> bool:
            nonlocal basili
            if olay.event_type == keyboard.KEY_UP:
                if basili:
                    basili = False
                    return False
                return True
            if basili:  # basılı tutulunca gelen tekrarlar
                return False
            if self.kayit_modu or not etkin_mi():
                return True
            if any(keyboard.is_pressed(d) != (d in gerekli) for d in DEGISTIRICILER):
                return True
            basili = True
            threading.Thread(target=islev, daemon=True).start()
            return False

        return keyboard.hook_key(tus, kanca, suppress=True)

    def _enter_basildi(self, olay) -> bool:
        """Klavye kancasının içinde çalışır: hızlı olmalı. True = Enter'ı geçir."""
        if self._gecir or self.kayit_modu or not self.aktif or not self.ayarlar["enter_modu"]:
            return True
        # Shift+Enter (yeni satır), Ctrl+Enter vb. dokunulmaz.
        if any(keyboard.is_pressed(t) for t in DEGISTIRICILER):
            return True
        if on_plandaki_pid() == os.getpid():  # kendi ayarlar penceremiz
            return True
        if on_plandaki_program() in self.ayarlar["enter_haric_programlar"]:
            return True
        if self._mesgul.locked():
            return False  # önceki çeviri sürerken gelen Enter'ı yut
        threading.Thread(target=self._enter_isle, daemon=True).start()
        return False

    def _geri_alinabilir(self) -> bool:
        son = self._son_ceviri
        return (
            son is not None
            and not self._mesgul.locked()
            and son["pencere"] == on_plandaki_pencere()
            and time.time() - son["zaman"] < GERI_AL_SURESI
        )

    # ---- asıl iş

    def _tus_gonder(self, kombinasyon: str):
        if kombinasyon in _GEZINME_TUSLARI:
            gezinme_tusu(kombinasyon)
        else:
            keyboard.send(kombinasyon)
        time.sleep(0.03)

    def _enter_gonder(self):
        self._gecir = True
        try:
            keyboard.send("enter")
            time.sleep(0.05)
        finally:
            self._gecir = False

    def _degistiricileri_bekle(self):
        """Kullanıcı kısayol tuşlarını bırakana kadar bekle (yoksa Ctrl+Shift+A gider)."""
        bitis = time.time() + 2
        while time.time() < bitis and any(keyboard.is_pressed(t) for t in DEGISTIRICILER):
            time.sleep(0.02)

    def _kopyala(self, hepsini_sec: bool) -> str:
        pano_yaz("")
        if hepsini_sec:
            self._tus_gonder("ctrl+a")
        self._tus_gonder("ctrl+c")
        bitis = time.time() + 0.5
        while time.time() < bitis:
            metin = pano_oku()
            if metin:
                return metin
            time.sleep(0.02)
        return ""

    def _degistir(self, yeni: str):
        pano_yaz(yeni)
        time.sleep(0.03)
        self._tus_gonder("ctrl+v")
        time.sleep(0.12)  # uygulama yapıştırmayı bitirsin

    def _cevir(self, metin: str) -> tuple[bool, str | None]:
        """(başarılı_mı, yeni_metin_ya_da_None)"""
        try:
            return True, ceviri.cevir(metin, self.ayarlar["hedef_dil"])
        except ceviri.CeviriHatasi as e:
            logging.warning("Çeviri başarısız: %s", e)
            self._bildir(t("bildirim_ceviri_hatasi"))
            winsound.MessageBeep(winsound.MB_ICONHAND)
            return False, None

    def _enter_isle(self):
        with self._mesgul:
            self._son_ceviri = None  # gönderilen mesaj geri alınamaz
            eski_pano = pano_oku()
            try:
                metin = self._kopyala(hepsini_sec=True)
                # Boş kutu ya da kopyalanamayan alan (ör. şifre kutusu): normal Enter.
                if not metin:
                    self._tus_gonder("end")
                    self._enter_gonder()
                    return
                basarili, yeni = self._cevir(metin)
                if not basarili:
                    self._tus_gonder("end")  # metin seçili kalmasın, gönderme
                    return
                if yeni:
                    self._degistir(yeni)
                else:
                    self._tus_gonder("end")
                self._enter_gonder()
            except Exception:
                logging.exception("Enter işlenirken hata")
            finally:
                time.sleep(0.15)
                pano_yaz(eski_pano)

    def _kisayol_isle(self):
        with self._mesgul:
            self._degistiricileri_bekle()
            eski_pano = pano_oku()
            try:
                metin = self._kopyala(hepsini_sec=False) or self._kopyala(hepsini_sec=True)
                if not metin:
                    return
                basarili, yeni = self._cevir(metin)
                if basarili and yeni:
                    self._degistir(yeni)
                    self._son_ceviri = {
                        "pencere": on_plandaki_pencere(),
                        "orijinal": metin,
                        "ceviri": yeni,
                        "zaman": time.time(),
                    }
            except Exception:
                logging.exception("Kısayol işlenirken hata")
            finally:
                time.sleep(0.15)
                pano_yaz(eski_pano)

    def _geri_al_isle(self):
        """İmleç yapıştırılan çevirinin sonundadır: geriye doğru seç, seçimin gerçekten
        çeviri olduğunu doğrula, sonra orijinali yapıştır. Doğrulama tutmazsa
        (metin düzenlenmiş, imleç taşınmış) hiçbir şeye dokunma."""
        with self._mesgul:
            son, self._son_ceviri = self._son_ceviri, None
            if not son:
                return
            self._degistiricileri_bekle()
            eski_pano = pano_oku()
            try:
                keyboard.press("shift")
                try:
                    for _ in range(imlec_adimi(son["ceviri"])):
                        gezinme_tusu("left")
                finally:
                    keyboard.release("shift")
                time.sleep(0.05)
                secili = self._kopyala(hepsini_sec=False).replace("\r\n", "\n")
                if secili == son["ceviri"].replace("\r\n", "\n"):
                    self._degistir(son["orijinal"])
                else:
                    self._tus_gonder("right")  # seçimi kaldır, imleç yerine dönsün
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                    self._bildir(t("bildirim_geri_alinamadi"))
            except Exception:
                logging.exception("Geri alınırken hata")
            finally:
                time.sleep(0.15)
                pano_yaz(eski_pano)

    # ---- tepsi simgesi

    def simge_resmi(self, aktif: bool | None = None) -> Image.Image:
        """aktif verilmezse uygulamanın o anki durumuna göre (yeşil/gri) çizilir."""
        aktif = self.aktif if aktif is None else aktif
        renk = (34, 160, 90) if aktif else (120, 120, 120)
        resim = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ciz = ImageDraw.Draw(resim)
        ciz.rounded_rectangle((2, 2, 62, 62), radius=14, fill=renk)
        try:
            yazi_tipi = ImageFont.truetype("segoeuib.ttf", 40)
        except OSError:
            yazi_tipi = ImageFont.load_default()
        ciz.text((32, 33), "Ç", font=yazi_tipi, fill="white", anchor="mm")
        return resim

    def _ipucu(self) -> str:
        return t("ipucu", durum=self._durum(), dil=metinler.dil_adi(self.ayarlar["hedef_dil"]))

    def _durum(self) -> str:
        return t("acik") if self.aktif else t("kapali")

    def _simgeyi_guncelle(self):
        if self.simge:
            self.simge.icon = self.simge_resmi()
            self.simge.title = self._ipucu()
            self.simge.update_menu()

    def _bildir(self, mesaj: str):
        try:
            if self.simge:
                self.simge.notify(mesaj, "OtoÇeviri")
        except Exception:
            pass

    def _dil_sec(self, kod):
        def isle(*_):
            self.ayarlar["hedef_dil"] = kod
            self._ayarlari_kaydet()
            self._simgeyi_guncelle()
        return isle

    def _ayar_degistir(self, anahtar):
        def isle(*_):
            self.ayarlar[anahtar] = not self.ayarlar[anahtar]
            self._ayarlari_kaydet()
            self._simgeyi_guncelle()
        return isle

    def _windows_acilisini_degistir(self, *_):
        try:
            baslangic.ayarla(not baslangic.acik_mi())
        except OSError:
            logging.exception("Başlangıç kaydı değiştirilemedi")
            self._bildir(t("bildirim_windows_hatasi"))
        self._simgeyi_guncelle()

    def _menu(self) -> pystray.Menu:
        g = kisayollar.goster
        diller = [
            pystray.MenuItem(
                lambda _, kod=kod: metinler.dil_adi(kod), self._dil_sec(kod), radio=True,
                checked=lambda _, kod=kod: self.ayarlar["hedef_dil"] == kod,
            )
            for kod in ceviri.DILLER
        ]
        return pystray.Menu(
            pystray.MenuItem(
                lambda _: t("menu_otomatik", durum=self._durum(),
                            kisayol=g(self.ayarlar["ac_kapa_kisayolu"])),
                self.ac_kapa, default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: t("menu_hedef_dil", dil=metinler.dil_adi(self.ayarlar["hedef_dil"])),
                pystray.Menu(*diller),
            ),
            pystray.MenuItem(lambda _: t("ceviri_modu"), pystray.Menu(
                pystray.MenuItem(
                    lambda _: t("mod_kisayol_menu", kisayol=g(self.ayarlar["cevir_kisayolu"])),
                    self._ayar_degistir("kisayol_modu"),
                    checked=lambda _: self.ayarlar["kisayol_modu"],
                ),
                pystray.MenuItem(
                    lambda _: t("mod_enter"), self._ayar_degistir("enter_modu"),
                    checked=lambda _: self.ayarlar["enter_modu"],
                ),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: t("windows_acilisi"), self._windows_acilisini_degistir,
                checked=lambda _: baslangic.acik_mi(),
            ),
            pystray.MenuItem(lambda _: t("menu_ayarlar"), lambda *_: ayarlar_penceresi.ac(self)),
            pystray.MenuItem(lambda _: t("menu_hakkinda"), lambda *_: hakkinda_penceresi.ac(self)),
            pystray.MenuItem(lambda _: t("menu_cikis"), self._cikis),
        )

    def _cikis(self, *_):
        keyboard.unhook_all()
        pencere.kapat()
        self.simge.stop()

    def calistir(self):
        try:
            baslangic.yolu_guncelle()
        except OSError:
            logging.exception("Başlangıç kaydı güncellenemedi")
        tema.menu_temasi(self.ayarlar["tema"])
        threading.Thread(target=self._sistem_temasini_izle, daemon=True).start()
        keyboard.on_press_key("enter", self._enter_basildi, suppress=True)
        self.kisayollari_kur()
        self.simge = pystray.Icon(
            "OtoCeviri", self.simge_resmi(), self._ipucu(), self._menu()
        )

        def hazir(simge):
            simge.visible = True
            self._bildir(
                t("bildirim_basladi", kisayol=kisayollar.goster(self.ayarlar["ac_kapa_kisayolu"]))
            )

        self.simge.run(setup=hazir)


def main():
    kilit = tek_ornek_kilidi()
    if kilit is None:
        ctypes.windll.user32.MessageBoxW(None, t("zaten_calisiyor"), "OtoÇeviri", 0x40)
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # ayarlar penceresi bulanık olmasın
    except (AttributeError, OSError):
        pass
    try:
        OtoCeviri().calistir()
    except Exception:
        logging.exception("Uygulama çöktü")
        raise


if __name__ == "__main__":
    main()
