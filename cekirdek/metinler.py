"""Arayüz metinleri (Türkçe / English).

Kullanım: metinler.t("anahtar", deger=...)  ->  seçili arayüz dilindeki metin.
Yeni bir metin eklerken iki dile de eklemeyi unutma; eksik İngilizce metin
Türkçeye düşer.
"""

import ctypes

ARAYUZ_DILLERI = ("sistem", "tr", "en")

METINLER = {
    "tr": {
        # Tepsi simgesi ve menü
        "acik": "AÇIK",
        "kapali": "KAPALI",
        "ipucu": "OtoÇeviri: {durum} → {dil}",
        "menu_otomatik": "Otomatik Çeviri: {durum}  ({kisayol})",
        "menu_hedef_dil": "Hedef dil: {dil}",
        "ceviri_modu": "Çeviri modu",
        "mod_kisayol": "Kısayol ile çevir",
        "mod_kisayol_menu": "Kısayol ile çevir ({kisayol})",
        "mod_enter": "Enter'a basınca otomatik çevir",
        "windows_acilisi": "Windows açılışında başlat",
        "menu_ayarlar": "Ayarlar…",
        "menu_guncelleme_mevcut": "Bir güncelleme mevcut!",
        "menu_hakkinda": "Hakkında",
        "menu_cikis": "Çıkış",
        # Bildirimler
        "bildirim_basladi": "Çalışıyor. {kisayol} ile aç/kapat ya da simgeye tıkla.",
        "bildirim_ceviri_hatasi": "Çeviri yapılamadı. İnternet bağlantını kontrol et.",
        "bildirim_geri_alinamadi": "Geri alınamadı: metin değişmiş. Ctrl+Z deneyebilirsin.",
        "bildirim_windows_hatasi": "Windows açılış ayarı değiştirilemedi.",
        "zaten_calisiyor": "OtoÇeviri zaten çalışıyor.",
        # Ayarlar penceresi
        "pencere_basligi": "OtoÇeviri Ayarları",
        "genel": "Genel",
        "hedef_dil": "Hedef dil:",
        "arayuz_dili": "Arayüz dili:",
        "tema": "Tema:",
        "sistem": "Sistem",
        "tema_acik": "Açık",
        "tema_koyu": "Koyu",
        "acilista_aktif": "Program açılınca Otomatik Çeviri açık başlasın",
        "ceviri_sesi": "Çeviri yapılınca ses çal",
        "kisayollar": "Kısayollar",
        "kisayol_ac_kapa": "Aç / Kapat",
        "kisayol_cevir": "Çevir",
        "kisayol_geri_al": "Son çeviriyi geri al",
        "degistir": "Değiştir",
        "tuslara_bas": "Tuşlara bas…  (Esc: iptal)",
        "kisayol_ayni": "Aynı kısayol birden fazla işe atanamaz.",
        "haric_baslik": "Enter modunun çalışmayacağı programlar",
        "haric_aciklama": "Her satıra bir program (ör. excel.exe). Kısayol modu bunlarda da çalışır.",
        "iptal": "İptal",
        "kaydet": "Kaydet",
        "kaydedilemedi": "Ayarlar kaydedilemedi:\n{hata}",
        # Kısayol doğrulama
        "kisayol_hata_tus": "Bir harf ya da tuş ile birlikte Ctrl/Alt/Win kullan (ör. Ctrl+Shift+U).",
        "kisayol_hata_degistirici": "Kısayol Ctrl, Alt ya da Win tuşu içermeli; yoksa yazı yazmayı engeller.",
        "kisayol_hata_taninmadi": "'{tus}' tuşu tanınmadı.",
        # Hakkında penceresi
        "hakkinda_basligi": "OtoÇeviri Hakkında",
        "surum": "Sürüm {surum}",
        "aciklama": "Yazdığın metni, yazım tarzını bozmadan seçtiğin dile çevirir.",
        "kaynak_kodu": "Kaynak kodu:",
        "lisans": "MIT Lisansı ile yayınlanmıştır.",
        "sorumluluk_baslik": "Sorumluluk reddi",
        "sorumluluk_metni": (
            "OtoÇeviri bağımsız bir projedir. Google ile bir bağlantısı yoktur, Google "
            "tarafından onaylanmamış ya da desteklenmemiştir. \"Google Translate\", Google "
            "LLC'nin ticari markasıdır. Ücretsiz web adresi kişisel ve ticari olmayan "
            "kullanım için kullanılır. Sorumlu bir şekilde ve kendi sorumluluğunda kullan."
        ),
        "guncelleme_denetle": "Güncellemeleri denetle",
        "guncelleme_denetleniyor": "Denetleniyor…",
        "guncelleme_yok": "OtoÇeviri güncel.",
        "guncelleme_var": "Yeni sürüm mevcut: {surum}",
        "guncelleme_indiriliyor": "Sürüm {surum} indiriliyor… %{yuzde}",
        "guncelleme_yeniden_baslatiliyor": "Kuruluyor. OtoÇeviri birkaç saniye içinde yeniden açılacak.",
        "guncelleme_kaynak": "Sürüm {surum} yayınlandı. Kaynak koddan çalıştırdığın için GitHub'dan indir.",
        "guncelleme_hata_ag": "Güncelleme sunucusuna ulaşılamadı. İnternet bağlantını kontrol et.",
        "guncelleme_hata_bozuk": "İndirilen güncelleme bozuk; hiçbir şey değiştirilmedi.",
        "guncelleme_hata_yazma": "OtoÇeviri'nin klasörüne yazılamıyor. Güncellemeyi GitHub'dan elle indir.",
        "kapat": "Kapat",
    },
    "en": {
        "acik": "ON",
        "kapali": "OFF",
        "ipucu": "OtoÇeviri: {durum} → {dil}",
        "menu_otomatik": "Auto-Translate: {durum}  ({kisayol})",
        "menu_hedef_dil": "Target language: {dil}",
        "ceviri_modu": "Translation mode",
        "mod_kisayol": "Translate with hotkey",
        "mod_kisayol_menu": "Translate with hotkey ({kisayol})",
        "mod_enter": "Translate automatically on Enter",
        "windows_acilisi": "Start with Windows",
        "menu_ayarlar": "Settings…",
        "menu_guncelleme_mevcut": "An update is available!",
        "menu_hakkinda": "About",
        "menu_cikis": "Exit",
        "bildirim_basladi": "Running. Press {kisayol} or click the icon to turn it on/off.",
        "bildirim_ceviri_hatasi": "Translation failed. Check your internet connection.",
        "bildirim_geri_alinamadi": "Couldn't undo: the text has changed. Try Ctrl+Z instead.",
        "bildirim_windows_hatasi": "Couldn't change the Start with Windows setting.",
        "zaten_calisiyor": "OtoÇeviri is already running.",
        "pencere_basligi": "OtoÇeviri Settings",
        "genel": "General",
        "hedef_dil": "Target language:",
        "arayuz_dili": "Interface language:",
        "tema": "Theme:",
        "sistem": "System",
        "tema_acik": "Light",
        "tema_koyu": "Dark",
        "acilista_aktif": "Turn Auto-Translate on when the app starts",
        "ceviri_sesi": "Play a sound when text is translated",
        "kisayollar": "Hotkeys",
        "kisayol_ac_kapa": "Turn on / off",
        "kisayol_cevir": "Translate",
        "kisayol_geri_al": "Undo last translation",
        "degistir": "Change",
        "tuslara_bas": "Press the keys…  (Esc: cancel)",
        "kisayol_ayni": "The same hotkey can't be used for more than one action.",
        "haric_baslik": "Apps where Enter mode is disabled",
        "haric_aciklama": "One app per line (e.g. excel.exe). Hotkey mode still works in these apps.",
        "iptal": "Cancel",
        "kaydet": "Save",
        "kaydedilemedi": "Couldn't save settings:\n{hata}",
        "kisayol_hata_tus": "Use one letter or key together with Ctrl/Alt/Win (e.g. Ctrl+Shift+U).",
        "kisayol_hata_degistirici": "The hotkey must include Ctrl, Alt or Win; otherwise it would block typing.",
        "kisayol_hata_taninmadi": "The key '{tus}' wasn't recognized.",
        "hakkinda_basligi": "About OtoÇeviri",
        "surum": "Version {surum}",
        "aciklama": "Translates what you type into the language you choose, keeping your writing style.",
        "kaynak_kodu": "Source code:",
        "lisans": "Released under the MIT License.",
        "sorumluluk_baslik": "Disclaimer",
        "sorumluluk_metni": (
            "OtoÇeviri is an independent project. It is not affiliated with, endorsed by or "
            "sponsored by Google. \"Google Translate\" is a trademark of Google LLC. The free "
            "web endpoint is used for personal, non-commercial use. Use it responsibly and "
            "at your own risk."
        ),
        "guncelleme_denetle": "Check for updates",
        "guncelleme_denetleniyor": "Checking…",
        "guncelleme_yok": "OtoÇeviri is up to date.",
        "guncelleme_var": "New version available: {surum}",
        "guncelleme_indiriliyor": "Downloading version {surum}… {yuzde}%",
        "guncelleme_yeniden_baslatiliyor": "Installing. OtoÇeviri will restart in a few seconds.",
        "guncelleme_kaynak": "Version {surum} is out. You're running from source, so download it from GitHub.",
        "guncelleme_hata_ag": "Couldn't reach the update server. Check your internet connection.",
        "guncelleme_hata_bozuk": "The downloaded update was damaged; nothing was changed.",
        "guncelleme_hata_yazma": "Can't write to OtoÇeviri's folder. Download the update from GitHub manually.",
        "kapat": "Close",
    },
}

# Çeviri hedef dillerinin adları, arayüz diline göre.
DIL_ADLARI = {
    "tr": {
        "en": "İngilizce", "de": "Almanca", "fr": "Fransızca", "es": "İspanyolca",
        "it": "İtalyanca", "pt": "Portekizce", "nl": "Felemenkçe", "ru": "Rusça",
        "ar": "Arapça", "ja": "Japonca", "ko": "Korece", "zh-CN": "Çince", "tr": "Türkçe",
    },
    "en": {
        "en": "English", "de": "German", "fr": "French", "es": "Spanish",
        "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
        "ar": "Arabic", "ja": "Japanese", "ko": "Korean", "zh-CN": "Chinese", "tr": "Turkish",
    },
}

# Arayüz dili seçeneklerinin adları: her dil kendi adıyla yazılır.
ARAYUZ_DILI_ADLARI = {"tr": "Türkçe", "en": "English"}


def sistem_dili() -> str:
    """Windows'un görüntüleme dili Türkçeyse 'tr', değilse 'en'."""
    try:
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError):
        return "en"
    return "tr" if langid & 0x3FF == 0x1F else "en"  # 0x1F = LANG_TURKISH


_aktif = sistem_dili()


def ayarla(secim: str):
    """secim: 'sistem', 'tr' ya da 'en'."""
    global _aktif
    _aktif = sistem_dili() if secim == "sistem" else secim if secim in METINLER else "en"


def aktif() -> str:
    return _aktif


def t(anahtar: str, **degerler) -> str:
    metin = METINLER[_aktif].get(anahtar) or METINLER["tr"][anahtar]
    return metin.format(**degerler) if degerler else metin


def dil_adi(kod: str) -> str:
    return DIL_ADLARI[_aktif][kod]


def arayuz_dili_adi(kod: str) -> str:
    return t("sistem") if kod == "sistem" else ARAYUZ_DILI_ADLARI[kod]
