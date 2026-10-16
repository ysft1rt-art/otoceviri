"""Ayarlar penceresi. Tk iş parçacığı ve tema altyapısı pencere.py'de."""

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import keyboard

from arayuz import pencere
from cekirdek import baslangic, ceviri, kisayollar, metinler
from cekirdek.metinler import t

KISAYOL_ALANLARI = [  # (ayar anahtarı, metin anahtarı)
    ("ac_kapa_kisayolu", "kisayol_ac_kapa"),
    ("cevir_kisayolu", "kisayol_cevir"),
    ("geri_al_kisayolu", "kisayol_geri_al"),
]


def ac(uygulama):
    """Herhangi bir iş parçacığından çağrılabilir."""
    pencere.ac(AyarlarPenceresi, uygulama)


class AyarlarPenceresi(pencere.TemaliPencere):
    def __init__(self, kok, uygulama):
        super().__init__(kok, uygulama, t("pencere_basligi"))
        a = uygulama.ayarlar

        self.dil = tk.StringVar(value=metinler.dil_adi(a["hedef_dil"]))
        self.arayuz_dili = tk.StringVar(value=a["arayuz_dili"])
        self.ceviri_modu = tk.StringVar(value=a["ceviri_modu"])
        self.acilista_aktif = tk.BooleanVar(value=a["acilista_aktif"])
        self.windows_acilisi = tk.BooleanVar(value=baslangic.acik_mi())
        self.tema = tk.StringVar(value=a["tema"])
        self.kisayol = {k: a[k] for k, _ in KISAYOL_ALANLARI}
        self.kisayol_yazi = {
            k: tk.StringVar(value=kisayollar.goster(a[k])) for k, _ in KISAYOL_ALANLARI
        }
        self._kaydediliyor = False

        govde = ttk.Frame(self, padding=16)
        govde.grid(sticky="nsew")
        govde.columnconfigure(0, weight=1)

        # -- Genel
        genel = ttk.LabelFrame(govde, text=t("genel"), padding=10)
        genel.grid(row=0, column=0, sticky="ew")
        ttk.Label(genel, text=t("hedef_dil")).grid(row=0, column=0, sticky="w")
        self.dil_kutusu = ttk.Combobox(
            genel, textvariable=self.dil, values=[metinler.dil_adi(k) for k in ceviri.DILLER],
            state="readonly", width=18,
        )
        self.dil_kutusu.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 6))
        for satir, (yazi, degisken, secenekler, komut) in enumerate([
            (t("arayuz_dili"), self.arayuz_dili,
             [(k, metinler.arayuz_dili_adi(k)) for k in metinler.ARAYUZ_DILLERI], None),
            (t("tema"), self.tema,
             [("sistem", t("sistem")), ("acik", t("tema_acik")), ("koyu", t("tema_koyu"))],
             self._temayi_uygula),
        ], start=1):
            ttk.Label(genel, text=yazi).grid(row=satir, column=0, sticky="w")
            cerceve = ttk.Frame(genel)
            cerceve.grid(row=satir, column=1, sticky="w", padx=(8, 0), pady=(0, 6))
            for sutun, (kod, ad) in enumerate(secenekler):
                ttk.Radiobutton(
                    cerceve, text=ad, value=kod, variable=degisken, command=komut,
                ).grid(row=0, column=sutun, padx=(0, 12))
        for satir, (degisken, yazi) in enumerate([
            (self.acilista_aktif, t("acilista_aktif")),
            (self.windows_acilisi, t("windows_acilisi")),
        ], start=3):
            ttk.Checkbutton(genel, text=yazi, variable=degisken).grid(
                row=satir, column=0, columnspan=2, sticky="w", pady=1
            )

        # -- Çeviri modu
        mod = ttk.LabelFrame(govde, text=t("ceviri_modu"), padding=10)
        mod.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for satir, (kod, yazi) in enumerate([
            ("kisayol", t("mod_kisayol")),
            ("enter", t("mod_enter")),
        ]):
            ttk.Radiobutton(mod, text=yazi, value=kod, variable=self.ceviri_modu).grid(
                row=satir, column=0, sticky="w", pady=1
            )

        # -- Kısayollar
        kisa = ttk.LabelFrame(govde, text=t("kisayollar"), padding=10)
        kisa.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        kisa.columnconfigure(1, weight=1)
        self._degistir_dugmeleri = []
        for satir, (anahtar, ad) in enumerate(KISAYOL_ALANLARI):
            ttk.Label(kisa, text=t(ad) + ":").grid(row=satir, column=0, sticky="w", pady=2)
            ttk.Entry(
                kisa, textvariable=self.kisayol_yazi[anahtar], state="readonly", width=22
            ).grid(row=satir, column=1, sticky="ew", padx=8)
            dugme = ttk.Button(
                kisa, text=t("degistir"), command=lambda k=anahtar: self._kisayol_kaydet(k)
            )
            dugme.grid(row=satir, column=2)
            self._degistir_dugmeleri.append(dugme)
        self.kisayol_hata = ttk.Label(kisa, style="Hata.TLabel", wraplength=340)
        self.kisayol_hata.grid(row=len(KISAYOL_ALANLARI), column=0, columnspan=3, sticky="w")

        # -- Enter hariç programlar
        haric = ttk.LabelFrame(govde, text=t("haric_baslik"), padding=10)
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
        ttk.Button(dugmeler, text=t("iptal"), command=self.destroy).grid(row=0, column=0, padx=(0, 6))
        self.kaydet_dugmesi = ttk.Button(dugmeler, text=t("kaydet"), command=self._kaydet)
        self.kaydet_dugmesi.grid(row=0, column=1)

        self.goster()

    def tema_secimi(self) -> str:
        return self.tema.get()  # kaydetmeden önce önizleme

    def _tema_ozel(self, r):
        self.haric_kutusu.configure(
            background=r["alan"], foreground=r["yazi"], insertbackground=r["yazi"],
            selectbackground=r["vurgu"], selectforeground="#ffffff",
            highlightbackground=r["kenar"], highlightcolor=r["vurgu"],
        )
        try:  # açılır listenin kendisi ttk değil, ayrıca boyanmalı
            liste = self.tk.call("ttk::combobox::PopdownWindow", self.dil_kutusu) + ".f.l"
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
            arayuz_dili=self.arayuz_dili.get(),
            ceviri_modu=self.ceviri_modu.get(),
            acilista_aktif=self.acilista_aktif.get(),
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
