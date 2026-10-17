"""Hakkında penceresi: sürüm, güncelleme, GitHub bağlantısı ve lisans."""

import logging
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from arayuz import pencere
from cekirdek import guncelleme, surum
from cekirdek.metinler import t


def ac(uygulama):
    """Herhangi bir iş parçacığından çağrılabilir."""
    pencere.ac(HakkindaPenceresi, uygulama)


def guncellemeyi_sor(uygulama):
    """Tepsi menüsünden: pencereyi açar ve bulunan güncelleme kurulsun mu diye sorar.
    Herhangi bir iş parçacığından çağrılabilir."""
    pencere.ac(HakkindaPenceresi, uygulama, sonra=HakkindaPenceresi.guncellemeyi_sor)


class HakkindaPenceresi(pencere.TemaliPencere):
    def __init__(self, kok, uygulama):
        super().__init__(kok, uygulama, t("hakkinda_basligi"))

        govde = ttk.Frame(self, padding=18)
        govde.grid(sticky="nsew")
        govde.columnconfigure(0, weight=1)

        # -- Ad, sürüm
        ttk.Label(govde, text="OtoÇeviri", style="Baslik.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(govde, text=t("surum", surum=surum.SURUM), style="Soluk.TLabel").grid(
            row=1, column=0, sticky="w"
        )

        # -- Açıklama, bağlantı, lisans
        ttk.Label(govde, text=t("aciklama"), wraplength=380).grid(
            row=2, column=0, sticky="w", pady=(14, 8)
        )
        kaynak = ttk.Frame(govde)
        kaynak.grid(row=3, column=0, sticky="w")
        ttk.Label(kaynak, **self.ikonlu("kod", t("kaynak_kodu"))).grid(row=0, column=0)
        baglanti = ttk.Label(
            kaynak, text=surum.GITHUB_URL.removeprefix("https://"),
            style="Baglanti.TLabel", cursor="hand2",
        )
        baglanti.grid(row=0, column=1, padx=(6, 0))
        baglanti.bind("<Button-1>", lambda _: webbrowser.open(surum.GITHUB_URL))
        ttk.Label(govde, **self.ikonlu("belge", t("lisans"))).grid(row=4, column=0, sticky="w", pady=(4, 0))

        # -- Güncelleme
        guncel = ttk.Frame(govde)
        guncel.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        # Düğme, kurulabilir bir güncelleme bulununca "denetle"den "yükle"ye döner.
        self._denetle_secenekleri = self.ikonlu("yenile", t("guncelleme_denetle"), dugme=True)
        self._yukle_secenekleri = self.ikonlu("guncelleme", t("guncelleme_yukle"), dugme=True)
        self._dugme = ttk.Button(guncel, command=self._dugmeye_basildi, **self._denetle_secenekleri)
        self._dugme.grid(row=0, column=0, sticky="nw")
        self._durum = ttk.Label(guncel, wraplength=250, justify="left")
        self._durum.grid(row=0, column=1, sticky="w", padx=(10, 0))
        self._sonuclar = queue.Queue()  # güncelleme iş parçacığı -> Tk
        self._mesgul = False  # denetleniyor ya da kuruluyor
        self._gosterilen = None  # durumu gösterilen güncelleme
        self._yuklenecek = None  # düğme "yükle"deyken kurulacak güncelleme
        if uygulama.guncelleme is not None:
            self._guncelleme_goster(uygulama.guncelleme)
        else:
            self._isi_baslat(_denetle_isi)  # pencere açılınca kendiliğinden denetle
        self.after(1000, self._guncellemeyi_izle)

        # -- Kapat
        kapat = ttk.Button(govde, command=self.destroy, **self.ikonlu("cikis", t("kapat")))
        kapat.grid(row=6, column=0, sticky="e", pady=(14, 0))
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

    def _guncelleme_goster(self, g, denetlendi: bool = False):
        self._gosterilen = g
        self._yuklenecek = g if g is not None and guncelleme.kurulabilir_mi() else None
        self._dugme.configure(
            **(self._yukle_secenekleri if self._yuklenecek else self._denetle_secenekleri)
        )
        if g is None:
            self._durum_yaz(t("guncelleme_yok") if denetlendi else "")
        elif self._yuklenecek is None:
            self._durum_yaz(t("guncelleme_kaynak", surum=g.surum), "Baglanti.TLabel", g.sayfa_url)
        else:
            self._durum_yaz(t("guncelleme_var", surum=g.surum))

    def _guncellemeyi_izle(self):
        """Arka plandaki denetim pencere açıkken güncelleme bulursa düğme hemen değişsin."""
        g = self.uygulama.guncelleme
        if not self._mesgul and g is not None and g != self._gosterilen:
            self._guncelleme_goster(g)
        self.after(1000, self._guncellemeyi_izle)

    def _dugmeye_basildi(self):
        if self._yuklenecek is not None:
            self.guncellemeyi_sor()
        else:
            self._isi_baslat(_denetle_isi)

    def guncellemeyi_sor(self):
        g = self._yuklenecek
        if g is None or self._mesgul:
            return
        if messagebox.askyesno("OtoÇeviri", t("guncelleme_onay", surum=g.surum), parent=self):
            self._isi_baslat(_kur_isi, g)

    def _isi_baslat(self, is_, *argumanlar):
        self._mesgul = True
        self._dugme.state(["disabled"])
        if is_ is _denetle_isi:
            self._durum_yaz(t("guncelleme_denetleniyor"), "Soluk.TLabel")
        # İş parçacığına pencere (self) verilmez; bkz. _denetle_isi.
        threading.Thread(
            target=is_, args=(self.uygulama, *argumanlar, self._sonuclar.put), daemon=True
        ).start()
        self.after(100, self._sonuclari_isle)

    def _sonuclari_isle(self):
        try:
            if not self.winfo_exists():
                return
            while True:
                tur, deger = self._sonuclar.get_nowait()
                if tur == "yaz":  # kurulum ilerlemesi; iş sürüyor
                    self._durum_yaz(deger)
                    continue
                self._mesgul = False
                self._dugme.state(["!disabled"])
                if tur == "bulundu":
                    self._guncelleme_goster(deger, denetlendi=True)
                else:
                    self._durum_yaz(deger, "Hata.TLabel")
                return
        except queue.Empty:
            self.after(100, self._sonuclari_isle)
        except tk.TclError:
            pass  # pencere kapanmış


# İşler Tk dışında çalışır; pencereye yalnızca kuyruk üzerinden yazar. Pencereyi tutmazlar:
# pencere kapandıktan sonra son referans burada bırakılırsa Tk nesneleri bu iş parçacığında
# çöpe gider ve Tcl çöker. bildir(("yaz" | "bulundu" | "hata", değer)).

def _denetle_isi(uygulama, bildir):
    try:
        g = guncelleme.denetle()
        uygulama.guncelleme_bulundu(g)
        bildir(("bulundu", g))
    except guncelleme.GuncellemeHatasi as e:
        logging.warning("Güncelleme denetlenemedi: %s", e)
        bildir(("hata", t(e.anahtar)))
    except Exception:
        logging.exception("Güncelleme denetlenirken hata")
        bildir(("hata", t("guncelleme_hata_ag")))


def _kur_isi(uygulama, g, bildir):
    def ilerleme(inen, toplam):
        yuzde = min(100, inen * 100 // max(toplam, 1))
        bildir(("yaz", t("guncelleme_indiriliyor", surum=g.surum, yuzde=yuzde)))

    try:
        ilerleme(0, 1)
        uygulama.guncellemeyi_kur(g, ilerleme)
        bildir(("yaz", t("guncelleme_yeniden_baslatiliyor")))
    except guncelleme.GuncellemeHatasi as e:
        logging.warning("Güncelleme başarısız: %s", e)
        bildir(("hata", t(e.anahtar)))
    except Exception:
        logging.exception("Güncelleme sırasında hata")
        bildir(("hata", t("guncelleme_hata_ag")))
