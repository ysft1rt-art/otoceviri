"""Tk pencereleri için ortak altyapı: kalıcı Tk iş parçacığı ve temalı pencere sınıfı.

Tepsi menüsü ana iş parçacığını kullandığı için Tk kendi iş parçacığında çalışır.
Bu iş parçacığı uygulama boyunca yaşar ve tek bir gizli kök pencere tutar; her
pencere onun alt penceresi (Toplevel) olarak açılır. Tk'yi her açılışta yeni bir
iş parçacığında kurup yıkmak, Tk nesneleri başka bir iş parçacığında çöpe gidince
Tcl'i (tcl86t.dll) çökertiyordu.
"""

import gc
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

import tema

_istekler = queue.Queue()
_tk_baslat = threading.Lock()
_tk_is_parcacigi = None
_acik = {}  # pencere sınıfı -> açık penceresi (her türden en fazla bir tane)


def ac(sinif, uygulama):
    """Verilen pencereyi açar ya da zaten açıksa öne getirir. Her iş parçacığından çağrılabilir."""
    global _tk_is_parcacigi
    with _tk_baslat:
        if _tk_is_parcacigi is None:
            _tk_is_parcacigi = threading.Thread(target=_tk_dongusu, daemon=True)
            _tk_is_parcacigi.start()
    _istekler.put((sinif, uygulama))


def kapat():
    """Uygulamadan çıkarken çağrılır: Tk döngüsünü kendi iş parçacığında durdurur.
    Yoksa Python, Tk iş parçacığı yaşarken kapanmaya çalışıp takılıyor."""
    with _tk_baslat:
        is_parcacigi = _tk_is_parcacigi
    if is_parcacigi is not None and is_parcacigi.is_alive():
        _istekler.put(None)
        is_parcacigi.join(timeout=2)


def acik_pencere(sinif):
    return _acik.get(sinif)


def _tk_dongusu():
    kok = tk.Tk()
    kok.withdraw()

    def istekleri_isle():
        try:
            while True:
                istek = _istekler.get_nowait()
                if istek is None:
                    kok.quit()
                    return
                _goster(kok, *istek)
        except queue.Empty:
            pass
        except Exception:
            logging.exception("Pencere açılamadı")
        kok.after(100, istekleri_isle)

    kok.after(0, istekleri_isle)
    kok.mainloop()
    # Tk nesneleri (pencere, değişkenler, resimler) bu iş parçacığında temizlensin;
    # başka iş parçacığında çöpe giderlerse Tcl "wrong thread" diye çöküyor.
    _acik.clear()
    kok.destroy()
    del kok
    gc.collect()


def _goster(kok, sinif, uygulama):
    pencere = _acik.get(sinif)
    if pencere is not None and pencere.winfo_exists():
        pencere.one_getir()
        return
    _acik[sinif] = sinif(kok, uygulama)


class TemaliPencere(tk.Toplevel):
    """Uygulamanın temasını (açık/koyu/sistem) kullanan pencere. Alt sınıflar içeriği
    kurduktan sonra goster()'i çağırır."""

    def __init__(self, kok, uygulama, baslik: str):
        super().__init__(kok)
        self.uygulama = uygulama
        self._uygulanan_koyu = None
        self.title(baslik)
        self.resizable(False, False)
        self._simge = ImageTk.PhotoImage(uygulama.simge_resmi())
        self.iconphoto(True, self._simge)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def tema_secimi(self) -> str:
        """Pencerenin kullanacağı tema; ayarlar penceresi önizleme için değiştirir."""
        return self.uygulama.ayarlar["tema"]

    def _tema_ozel(self, r: dict):
        """ttk olmayan parçaları (Text, açılır liste) boyamak için alt sınıflarda."""

    def goster(self):
        self.update_idletasks()
        self._temayi_uygula()
        g, y = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - g) // 2
        yy = (self.winfo_screenheight() - y) // 3
        self.geometry(f"+{x}+{yy}")
        self.one_getir()
        self.after(1500, self._sistem_temasini_izle)

    def one_getir(self):
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def destroy(self):
        kok = self.master
        super().destroy()
        if _acik.get(type(self)) is self:
            del _acik[type(self)]
        kok.after_idle(gc.collect)  # pencerenin Tk nesneleri bu iş parçacığında temizlensin

    # ---- tema

    def _sistem_temasini_izle(self):
        """'Sistem' seçiliyken Windows teması değişirse pencere de değişsin."""
        if self.tema_secimi() == "sistem":
            self._temayi_uygula()
        self.after(1500, self._sistem_temasini_izle)

    def _temayi_uygula(self):
        koyu = tema.koyu_mu(self.tema_secimi())
        if koyu == self._uygulanan_koyu:
            return
        self._uygulanan_koyu = koyu
        r = tema.RENKLER[koyu]
        stil = ttk.Style(self)
        if koyu:
            # 'vista' teması Windows'un kendi çizimini kullanır ve renklendirilemez.
            stil.theme_use("clam")
            stil.configure(".", background=r["zemin"], foreground=r["yazi"],
                           fieldbackground=r["alan"], bordercolor=r["kenar"],
                           lightcolor=r["zemin"], darkcolor=r["zemin"],
                           troughcolor=r["zemin"], focuscolor=r["vurgu"],
                           selectbackground=r["vurgu"], selectforeground="#ffffff",
                           insertcolor=r["yazi"], arrowcolor=r["yazi"])
            stil.configure("TLabelframe", background=r["zemin"], bordercolor=r["kenar"])
            stil.configure("TLabelframe.Label", background=r["zemin"], foreground=r["yazi"])
            stil.configure("TButton", background=r["dugme"], lightcolor=r["dugme"],
                           darkcolor=r["dugme"], padding=(10, 3))
            stil.map("TButton",
                     background=[("disabled", r["zemin"]), ("pressed", r["kenar"]),
                                 ("active", r["dugme_uzerinde"])],
                     foreground=[("disabled", r["soluk"])])
            for tur in ("TCheckbutton", "TRadiobutton"):
                stil.configure(tur, indicatorbackground=r["alan"],
                               indicatorforeground="#ffffff", upperbordercolor=r["kutu_kenari"],
                               lowerbordercolor=r["kutu_kenari"])
                stil.map(tur, background=[("active", r["zemin"])],
                         indicatorbackground=[("selected", r["vurgu"]), ("active", r["kenar"])])
            stil.map("TEntry", fieldbackground=[("readonly", r["alan"])])
            stil.map("TCombobox",
                     fieldbackground=[("readonly", r["alan"])],
                     selectbackground=[("readonly", r["alan"])],
                     selectforeground=[("readonly", r["yazi"])],
                     background=[("active", r["dugme_uzerinde"]), ("!active", r["dugme"])])
            for tur in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
                stil.configure(tur, background=r["kaydirma"], troughcolor=r["alan"],
                               bordercolor=r["alan"], lightcolor=r["kaydirma"],
                               darkcolor=r["kaydirma"], arrowcolor=r["yazi"], gripcount=0)
                stil.map(tur, background=[("active", r["soluk"])])
        else:
            stil.theme_use("vista" if "vista" in stil.theme_names() else "default")
        stil.configure("Soluk.TLabel", foreground=r["soluk"])
        stil.configure("Hata.TLabel", foreground=r["hata"])
        stil.configure("Baslik.TLabel", font=("Segoe UI Semibold", 15))
        stil.configure("Baglanti.TLabel", foreground=r["vurgu"], font=("Segoe UI", 9, "underline"))

        self.configure(background=r["zemin"])
        self._tema_ozel(r)
        tema.baslik_cubugu(int(self.wm_frame(), 16), koyu)
