"""Hakkında penceresi: sürüm, GitHub bağlantısı, lisans ve sorumluluk reddi."""

import webbrowser
from tkinter import ttk

from PIL import ImageTk

from arayuz import pencere
from cekirdek import surum
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

        # -- Sorumluluk reddi
        sorumluluk = ttk.LabelFrame(govde, text=t("sorumluluk_baslik"), padding=10)
        sorumluluk.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Label(
            sorumluluk, text=t("sorumluluk_metni"), wraplength=380, style="Soluk.TLabel",
            justify="left",
        ).grid(sticky="w")

        # -- Kapat
        kapat = ttk.Button(govde, text=t("kapat"), command=self.destroy)
        kapat.grid(row=6, column=0, columnspan=2, sticky="e", pady=(14, 0))
        kapat.focus_set()
        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<Return>", lambda _: self.destroy())

        self.goster()
