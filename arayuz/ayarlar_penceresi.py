"""Ayarlar penceresi. Tk iş parçacığı ve tema altyapısı pencere.py'de."""

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import keyboard

from arayuz import pencere, tema
from cekirdek import baslangic, ceviri, kisayollar, metinler
from cekirdek.metinler import t

KISAYOL_ALANLARI = [  # (ayar anahtarı, metin anahtarı, ikon)
    ("ac_kapa_kisayolu", "kisayol_ac_kapa", "guc"),
    ("cevir_kisayolu", "kisayol_cevir", "cevir"),
    ("geri_al_kisayolu", "kisayol_geri_al", "geri_al"),
]
TEMA_METINLERI = {"sistem": "sistem", "acik": "tema_acik", "koyu": "tema_koyu"}


def ac(uygulama):
    """Herhangi bir iş parçacığından çağrılabilir."""
    pencere.ac(AyarlarPenceresi, uygulama)


class AyarlarPenceresi(pencere.TemaliPencere):
    def __init__(self, kok, uygulama):
        super().__init__(kok, uygulama, t("pencere_basligi"))
        a = uygulama.ayarlar

        self.ceviri_modu = tk.StringVar(value=a["ceviri_modu"])
        self.acilista_aktif = tk.BooleanVar(value=a["acilista_aktif"])
        self.ceviri_sesi = tk.BooleanVar(value=a["ceviri_sesi"])
        self.windows_acilisi = tk.BooleanVar(value=baslangic.acik_mi())
        self.tema = tk.StringVar(value=a["tema"])
        self.kisayol = {k: a[k] for k, _, _ in KISAYOL_ALANLARI}
        self.kisayol_yazi = {
            k: tk.StringVar(value=kisayollar.goster(a[k])) for k, _, _ in KISAYOL_ALANLARI
        }
        self._kaydediliyor = False

        govde = ttk.Frame(self, padding=16)
        govde.grid(sticky="nsew")
        govde.columnconfigure(0, weight=1)

        # -- Genel
        genel = self._bolum(govde, "genel", t("genel"))
        genel.grid(row=0, column=0, sticky="ew")
        self.kutular = []  # açılır listeler (koyu temada liste kısmı ayrıca boyanır)
        self.dil_kutusu, self.arayuz_kutusu, self.tema_kutusu = (
            self._acilir_liste(genel, satir, ikon, yazi, adlar, secili)
            for satir, (ikon, yazi, adlar, secili) in enumerate([
                ("dil", t("hedef_dil"), [metinler.dil_adi(k) for k in ceviri.DILLER],
                 ceviri.DILLER.index(a["hedef_dil"])),
                ("arayuz_dili", t("arayuz_dili"),
                 [metinler.arayuz_dili_adi(k) for k in metinler.ARAYUZ_DILLERI],
                 metinler.ARAYUZ_DILLERI.index(a["arayuz_dili"])),
                ("tema", t("tema"), [t(TEMA_METINLERI[k]) for k in tema.TEMALAR],
                 tema.TEMALAR.index(a["tema"])),
            ])
        )
        self.tema_kutusu.bind("<<ComboboxSelected>>", self._tema_secildi)
        for satir, (degisken, ikon, yazi) in enumerate([
            (self.acilista_aktif, "guc", t("acilista_aktif")),
            (self.windows_acilisi, "bilgisayar", t("windows_acilisi")),
            (self.ceviri_sesi, "ses", t("ceviri_sesi")),
        ], start=3):
            ttk.Checkbutton(genel, variable=degisken, **self.ikonlu(ikon, yazi)).grid(
                row=satir, column=0, columnspan=2, sticky="w", pady=1
            )

        # -- Çeviri modu
        mod = self._bolum(govde, "mod", t("ceviri_modu"))
        mod.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for satir, (kod, ikon, yazi) in enumerate([
            ("kisayol", "klavye", t("mod_kisayol")),
            ("enter", "enter", t("mod_enter")),
        ]):
            ttk.Radiobutton(
                mod, value=kod, variable=self.ceviri_modu, **self.ikonlu(ikon, yazi)
            ).grid(row=satir, column=0, sticky="w", pady=1)

        # -- Kısayollar
        kisa = self._bolum(govde, "klavye", t("kisayollar"))
        kisa.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        kisa.columnconfigure(1, weight=1)
        self._degistir_dugmeleri = []
        for satir, (anahtar, ad, ikon) in enumerate(KISAYOL_ALANLARI):
            ttk.Label(kisa, **self.ikonlu(ikon, t(ad) + ":")).grid(
                row=satir, column=0, sticky="w", pady=2
            )
            ttk.Entry(
                kisa, textvariable=self.kisayol_yazi[anahtar], state="readonly", width=22
            ).grid(row=satir, column=1, sticky="ew", padx=8)
            dugme = ttk.Button(
                kisa, command=lambda k=anahtar: self._kisayol_kaydet(k),
                **self.ikonlu("duzenle", t("degistir"), dugme=True),
            )
            dugme.grid(row=satir, column=2)
            self._degistir_dugmeleri.append(dugme)
        self.kisayol_hata = ttk.Label(kisa, style="Hata.TLabel", wraplength=340)
        self.kisayol_hata.grid(row=len(KISAYOL_ALANLARI), column=0, columnspan=3, sticky="w")

        # -- Enter hariç programlar
        haric = self._bolum(govde, "engel", t("haric_baslik"))
        haric.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        haric.columnconfigure(0, weight=1)
        ttk.Label(
            haric, text=t("haric_aciklama"),
            style="Soluk.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.haric_kutusu = tk.Text(
            haric, width=44, height=7, font=("Consolas", 9), relief="flat", highlightthickness=1
        )
        kaydirma = ttk.Scrollbar(haric, command=self.haric_kutusu.yview)
        self.haric_kutusu.configure(yscrollcommand=kaydirma.set)
        self.haric_kutusu.grid(row=1, column=0, sticky="ew")
        kaydirma.grid(row=1, column=1, sticky="ns")
        self.haric_kutusu.insert("1.0", "\n".join(a["enter_haric_programlar"]))

        # -- Düğmeler
        dugmeler = ttk.Frame(govde)
        dugmeler.grid(row=4, column=0, sticky="e", pady=(14, 0))
        ttk.Button(
            dugmeler, command=self.destroy, **self.ikonlu("iptal", t("iptal"), dugme=True)
        ).grid(row=0, column=0, padx=(0, 6))
        self.kaydet_dugmesi = ttk.Button(
            dugmeler, command=self._kaydet, **self.ikonlu("kaydet", t("kaydet"), dugme=True)
        )
        self.kaydet_dugmesi.grid(row=0, column=1)

        self.goster()

    def _bolum(self, ust, ikon: str, baslik: str) -> ttk.LabelFrame:
        """İkonlu başlığı olan çerçeve."""
        return ttk.LabelFrame(
            ust, labelwidget=ttk.Label(ust, **self.ikonlu(ikon, baslik)), padding=10
        )

    def _acilir_liste(self, ust, satir, ikon, yazi, adlar, secili) -> ttk.Combobox:
        ttk.Label(ust, **self.ikonlu(ikon, yazi)).grid(row=satir, column=0, sticky="w")
        kutu = ttk.Combobox(ust, values=adlar, state="readonly", width=18)
        kutu.current(secili)
        kutu.grid(row=satir, column=1, sticky="w", padx=(8, 0), pady=(0, 6))
        self.kutular.append(kutu)
        return kutu

    def _tema_secildi(self, _olay=None):
        self.tema.set(tema.TEMALAR[self.tema_kutusu.current()])
        self.tema_kutusu.selection_clear()
        self._temayi_uygula()  # kaydetmeden önce önizleme

    def tema_secimi(self) -> str:
        return self.tema.get()

    def _tema_ozel(self, r):
        self.haric_kutusu.configure(
            background=r["alan"], foreground=r["yazi"], insertbackground=r["yazi"],
            selectbackground=r["vurgu"], selectforeground="#ffffff",
            highlightbackground=r["kenar"], highlightcolor=r["vurgu"],
        )
        for kutu in self.kutular:
            try:  # açılır listenin kendisi ttk değil, ayrıca boyanmalı
                liste = self.tk.call("ttk::combobox::PopdownWindow", kutu) + ".f.l"
                self.tk.call(liste, "configure", "-background", r["alan"], "-foreground", r["yazi"],
                             "-selectbackground", r["vurgu"], "-selectforeground", "#ffffff")
            except tk.TclError:
                pass

    def destroy(self):
        self.uygulama.kayit_modu = False  # kayıt sürerken kapatılırsa kancalar susmuş kalmasın
        super().destroy()

    # ---- kısayol kaydı

    def _kisayol_kaydet(self, anahtar):
        if self._kaydediliyor:
            return
        self._kaydediliyor = True
        self.uygulama.kayit_modu = True  # uygulamanın kancaları bu sırada susar
        for d in self._degistir_dugmeleri + [self.kaydet_dugmesi]:
            d.state(["disabled"])
        self.kisayol_hata.config(text="")
        self.kisayol_yazi[anahtar].set(t("tuslara_bas"))
        sonuc = {}

        def oku():
            try:
                sonuc["ham"] = keyboard.read_hotkey(suppress=False)
            except Exception as e:
                sonuc["hata"] = str(e)

        okuyucu = threading.Thread(target=oku, daemon=True)
        okuyucu.start()

        def bekle():
            if okuyucu.is_alive():
                self.after(50, bekle)
                return
            self._kaydediliyor = False
            self.uygulama.kayit_modu = False
            for d in self._degistir_dugmeleri + [self.kaydet_dugmesi]:
                d.state(["!disabled"])
            ham = sonuc.get("ham", "")
            yeni, hata = (None, None) if ham in ("", "esc") else kisayollar.normallestir(ham)
            if yeni:
                self.kisayol[anahtar] = yeni
            elif hata:
                self.kisayol_hata.config(text=hata)
            self.kisayol_yazi[anahtar].set(kisayollar.goster(self.kisayol[anahtar]))

        self.after(50, bekle)

    # ---- kaydet

    def _kaydet(self):
        degerler = list(self.kisayol.values())
        if len(set(degerler)) != len(degerler):
            self.kisayol_hata.config(text=t("kisayol_ayni"))
            return
        haric = []
        for satir in self.haric_kutusu.get("1.0", "end").splitlines():
            satir = satir.strip().lower()
            if satir and satir not in haric:
                haric.append(satir if satir.endswith(".exe") else satir + ".exe")

        yeni = dict(self.uygulama.ayarlar)
        yeni.update(
            hedef_dil=ceviri.DILLER[self.dil_kutusu.current()],
            arayuz_dili=metinler.ARAYUZ_DILLERI[self.arayuz_kutusu.current()],
            ceviri_modu=self.ceviri_modu.get(),
            acilista_aktif=self.acilista_aktif.get(),
            ceviri_sesi=self.ceviri_sesi.get(),
            tema=self.tema.get(),
            enter_haric_programlar=haric,
            **self.kisayol,
        )
        try:
            self.uygulama.ayarlari_uygula(yeni, self.windows_acilisi.get())
        except Exception as e:
            logging.exception("Ayarlar uygulanamadı")
            messagebox.showerror("OtoÇeviri", t("kaydedilemedi", hata=e), parent=self)
            return
        self.destroy()
