"""OtoÇeviri — yazdığın her şeyi seçtiğin dile çeviren sistem tepsisi uygulaması.

Enter modu : Açıkken Enter'a bastığında yazı kutusundaki metin çevrilir ve gönderilir.
Kısayol modu: Kısayola bastığında seçili metin (seçim yoksa kutunun tamamı) çevrilir.
"""

import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import subprocess
import sys
import threading
import time
import winsound

import keyboard
import pyperclip
import pystray
from PIL import Image, ImageDraw, ImageFont

import ceviri

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
    "acilista_aktif": False,
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
DEGISTIRICILER = ("ctrl", "shift", "alt", "windows")
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_ALREADY_EXISTS = 183


def on_plandaki_program() -> str:
    """Odaktaki pencerenin program adını (ör. 'discord.exe') döndürür."""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wt.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
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

class OtoCeviri:
    def __init__(self):
        self.ayarlar = self._ayarlari_yukle()
        self.aktif = bool(self.ayarlar["acilista_aktif"])
        self._gecir = False  # kendi gönderdiğimiz Enter'ı tekrar yakalamamak için
        self._mesgul = threading.Lock()
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
        self._ayarlari_kaydet(ayarlar)
        return ayarlar

    def _ayarlari_kaydet(self, ayarlar=None):
        try:
            with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(ayarlar or self.ayarlar, f, ensure_ascii=False, indent=2)
        except Exception:
            logging.exception("Ayar dosyası kaydedilemedi")

    # ---- açma / kapama

    def ac_kapa(self, *_):
        self.aktif = not self.aktif
        bip(self.aktif)
        self._simgeyi_guncelle()

    # ---- klavye kancaları

    def kancalari_kur(self):
        keyboard.on_press_key("enter", self._enter_basildi, suppress=True)
        self._kisayol_kancasi(
            self.ayarlar["ac_kapa_kisayolu"], self.ac_kapa, lambda: True
        )
        self._kisayol_kancasi(
            self.ayarlar["cevir_kisayolu"],
            self._kisayol_isle,
            lambda: self.aktif and self.ayarlar["kisayol_modu"] and not self._mesgul.locked(),
        )

    def _kisayol_kancasi(self, kisayol: str, islev, etkin_mi):
        """Kısayolu yakalar ve son tuşunu yutar; böylece odaktaki programa ulaşmaz
        (ör. Discord'da Ctrl+Shift+U dosya seçme penceresini açmaz).

        keyboard.add_hotkey(suppress=True) değiştirici tuşları geciktirip bozduğu için
        yalnızca son tuşu engelliyoruz; Ctrl/Shift tek başına bir şey yapmaz.
        """
        parcalar = [p.strip().lower() for p in kisayol.split("+")]
        tus, gerekli = parcalar[-1], set(parcalar[:-1])
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
            if not etkin_mi():
                return True
            if any(keyboard.is_pressed(d) != (d in gerekli) for d in DEGISTIRICILER):
                return True
            basili = True
            threading.Thread(target=islev, daemon=True).start()
            return False

        keyboard.hook_key(tus, kanca, suppress=True)

    def _enter_basildi(self, olay) -> bool:
        """Klavye kancasının içinde çalışır: hızlı olmalı. True = Enter'ı geçir."""
        if self._gecir or not self.aktif or not self.ayarlar["enter_modu"]:
            return True
        # Shift+Enter (yeni satır), Ctrl+Enter vb. dokunulmaz.
        if any(keyboard.is_pressed(t) for t in ("shift", "ctrl", "alt", "windows")):
            return True
        if on_plandaki_program() in self.ayarlar["enter_haric_programlar"]:
            return True
        if self._mesgul.locked():
            return False  # önceki çeviri sürerken gelen Enter'ı yut
        threading.Thread(target=self._enter_isle, daemon=True).start()
        return False

    # ---- asıl iş

    def _tus_gonder(self, kombinasyon: str):
        keyboard.send(kombinasyon)
        time.sleep(0.03)

    def _enter_gonder(self):
        self._gecir = True
        try:
            keyboard.send("enter")
            time.sleep(0.05)
        finally:
            self._gecir = False

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
            self._bildir("Çeviri yapılamadı. İnternet bağlantını kontrol et.")
            winsound.MessageBeep(winsound.MB_ICONHAND)
            return False, None

    def _enter_isle(self):
        with self._mesgul:
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
            # Kullanıcı kısayol tuşlarını bırakana kadar bekle (yoksa Ctrl+Shift+A gider).
            bitis = time.time() + 2
            while time.time() < bitis and any(
                keyboard.is_pressed(t) for t in ("shift", "ctrl", "alt")
            ):
                time.sleep(0.02)
            eski_pano = pano_oku()
            try:
                metin = self._kopyala(hepsini_sec=False) or self._kopyala(hepsini_sec=True)
                if not metin:
                    return
                basarili, yeni = self._cevir(metin)
                if basarili and yeni:
                    self._degistir(yeni)
            except Exception:
                logging.exception("Kısayol işlenirken hata")
            finally:
                time.sleep(0.15)
                pano_yaz(eski_pano)

    # ---- tepsi simgesi

    def _simge_resmi(self) -> Image.Image:
        renk = (34, 160, 90) if self.aktif else (120, 120, 120)
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
        durum = "AÇIK" if self.aktif else "KAPALI"
        return f"OtoÇeviri: {durum} → {ceviri.DILLER[self.ayarlar['hedef_dil']]}"

    def _simgeyi_guncelle(self):
        if self.simge:
            self.simge.icon = self._simge_resmi()
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

    def _menu(self) -> pystray.Menu:
        k = self.ayarlar
        diller = [
            pystray.MenuItem(
                ad, self._dil_sec(kod), radio=True,
                checked=lambda _, kod=kod: self.ayarlar["hedef_dil"] == kod,
            )
            for kod, ad in ceviri.DILLER.items()
        ]
        return pystray.Menu(
            pystray.MenuItem(
                lambda _: f"Otomatik Çeviri: {'AÇIK' if self.aktif else 'KAPALI'}"
                          f"  ({k['ac_kapa_kisayolu'].upper()})",
                self.ac_kapa, default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: f"Hedef dil: {ceviri.DILLER[self.ayarlar['hedef_dil']]}",
                pystray.Menu(*diller),
            ),
            pystray.MenuItem(
                "Enter'a basınca çevir", self._ayar_degistir("enter_modu"),
                checked=lambda _: self.ayarlar["enter_modu"],
            ),
            pystray.MenuItem(
                f"Kısayolla çevir ({k['cevir_kisayolu'].upper()})",
                self._ayar_degistir("kisayol_modu"),
                checked=lambda _: self.ayarlar["kisayol_modu"],
            ),
            pystray.MenuItem(
                "Açılışta aktif başlasın", self._ayar_degistir("acilista_aktif"),
                checked=lambda _: self.ayarlar["acilista_aktif"],
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Ayar dosyasını aç", self._ayar_dosyasini_ac),
            pystray.MenuItem("Çıkış", self._cikis),
        )

    def _ayar_dosyasini_ac(self, *_):
        subprocess.Popen(["notepad.exe", AYAR_DOSYASI])

    def _cikis(self, *_):
        keyboard.unhook_all()
        self.simge.stop()

    def calistir(self):
        self.kancalari_kur()
        self.simge = pystray.Icon(
            "OtoCeviri", self._simge_resmi(), self._ipucu(), self._menu()
        )

        def hazir(simge):
            simge.visible = True
            self._bildir(
                f"Çalışıyor. {self.ayarlar['ac_kapa_kisayolu'].upper()} ile aç/kapat "
                f"ya da simgeye tıkla."
            )

        self.simge.run(setup=hazir)


def main():
    kilit = tek_ornek_kilidi()
    if kilit is None:
        ctypes.windll.user32.MessageBoxW(None, "OtoÇeviri zaten çalışıyor.", "OtoÇeviri", 0x40)
        return
    try:
        OtoCeviri().calistir()
    except Exception:
        logging.exception("Uygulama çöktü")
        raise


if __name__ == "__main__":
    main()
