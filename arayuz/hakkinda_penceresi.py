"""Hakkında penceresi: sürüm, güncelleme, GitHub bağlantısı, lisans ve sorumluluk reddi."""

import logging
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk

from PIL import ImageTk

from arayuz import pencere
from cekirdek import guncelleme, surum
from cekirdek.metinler import t


def ac(uygulama):
    """Herhangi bir iş parçacığından çağrılabilir."""
    pencere.ac(HakkindaPenceresi, uygulama)


class HakkindaPenceresi(pencere.TemaliPencere):
    def __init__(self, kok, uygulama):
        super().__init__(kok, uygulama, t("hakkinda_basligi"))

        govde = ttk.Frame(self, padding=18)
        govde.grid(sticky="nsew")
        govde.columnconfigure(1, weight=1)

        # -- Simge, ad, sürüm
        self._buyuk_simge = ImageTk.PhotoImage(uygulama.simge_resmi(aktif=True))  # logo: hep yeşil
        ttk.Label(govde, image=self._buyuk_simge).grid(row=0, column=0, rowspan=2, padx=(0, 14))
        ttk.Label(govde, text="OtoÇeviri", style="Baslik.TLabel").grid(
            row=0, column=1, sticky="sw"
        )
        ttk.Label(govde, text=t("surum", surum=surum.SURUM), style="Soluk.TLabel").grid(
            row=1, column=1, sticky="nw"
        )

        # -- Açıklama, bağlantı, lisans
        ttk.Label(govde, text=t("aciklama"), wraplength=380).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(14, 8)
        )
        kaynak = ttk.Frame(govde)
        kaynak.grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Label(kaynak, text=t("kaynak_kodu")).grid(row=0, column=0)
        baglanti = ttk.Label(
            kaynak, text=surum.GITHUB_URL.removeprefix("https://"),
            style="Baglanti.TLabel", cursor="hand2",
        )
        baglanti.grid(row=0, column=1, padx=(6, 0))
        baglanti.bind("<Button-1>", lambda _: webbrowser.open(surum.GITHUB_URL))
        ttk.Label(govde, text=t("lisans")).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # -- Güncelleme
        guncel = ttk.Frame(govde)
        guncel.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        self._denetle = ttk.Button(guncel, text=t("guncelleme_denetle"), command=self._denetlemeyi_baslat)
        self._denetle.grid(row=0, column=0, sticky="nw")
        self._durum = ttk.Label(guncel, wraplength=250, justify="left")
        self._durum.grid(row=0, column=1, sticky="w", padx=(10, 0))
        self._sonuclar = queue.Queue()  # güncelleme iş parçacığı -> Tk
        if uygulama.guncelleme is not None:
            self._durum_yaz(t("guncelleme_var", surum=uygulama.guncelleme.surum))

        # -- Sorumluluk reddi
        sorumluluk = ttk.LabelFrame(govde, text=t("sorumluluk_baslik"), padding=10)
        sorumluluk.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Label(
            sorumluluk, text=t("sorumluluk_metni"), wraplength=380, style="Soluk.TLabel",
            justify="left",
        ).grid(sticky="w")

        # -- Kapat
        kapat = ttk.Button(govde, text=t("kapat"), command=self.destroy)
        kapat.grid(row=7, column=0, columnspan=2, sticky="e", pady=(14, 0))
        kapat.focus_set()
        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<Return>", lambda _: self.destroy())

        self.goster()

    # ---- güncelleme

    def _durum_yaz(self, metin: str, stil: str = "TLabel", baglanti: str | None = None):
        self._durum.configure(text=metin, style=stil, cursor="hand2" if baglanti else "")
        self._durum.unbind("<Button-1>")
        if baglanti:
            self._durum.bind("<Button-1>", lambda _: webbrowser.open(baglanti))

    def _denetlemeyi_baslat(self):
        self._denetle.state(["disabled"])
        self._durum_yaz(t("guncelleme_denetleniyor"), "Soluk.TLabel")
        threading.Thread(target=self._guncelle, daemon=True).start()
        self.after(100, self._sonuclari_isle)

    def _guncelle(self):
        """Tk dışında çalışır; pencereye yalnızca kuyruk üzerinden yazar."""
        bildir = self._sonuclar.put
        try:
            g = guncelleme.denetle()
            self.uygulama.guncelleme_bulundu(g)
            if g is None:
                bildir(("bitti", t("guncelleme_yok"), "TLabel", None))
            elif not guncelleme.kurulabilir_mi():
                bildir(("bitti", t("guncelleme_kaynak", surum=g.surum), "Baglanti.TLabel", g.sayfa_url))
            else:
                def ilerleme(inen, toplam):
                    yuzde = min(100, inen * 100 // max(toplam, 1))
                    bildir(("yaz", t("guncelleme_indiriliyor", surum=g.surum, yuzde=yuzde), "TLabel", None))

                ilerleme(0, 1)
                self.uygulama.guncellemeyi_kur(g, ilerleme)
                bildir(("yaz", t("guncelleme_yeniden_baslatiliyor"), "TLabel", None))
        except guncelleme.GuncellemeHatasi as e:
            logging.warning("Güncelleme başarısız: %s", e)
            bildir(("bitti", t(e.anahtar), "Hata.TLabel", None))
        except Exception:
            logging.exception("Güncelleme sırasında hata")
            bildir(("bitti", t("guncelleme_hata_ag"), "Hata.TLabel", None))

    def _sonuclari_isle(self):
        try:
            if not self.winfo_exists():
                return
            while True:
                tur, metin, stil, baglanti = self._sonuclar.get_nowait()
                self._durum_yaz(metin, stil, baglanti)
                if tur == "bitti":
                    self._denetle.state(["!disabled"])
                    return
        except queue.Empty:
            self.after(100, self._sonuclari_isle)
        except tk.TclError:
            pass  # pencere kapanmış
