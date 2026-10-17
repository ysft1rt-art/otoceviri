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

from arayuz import ikonlar, koyu_ogeler, tema

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
        self.withdraw()  # içerik kurulup tema uygulanana kadar görünmesin (bkz. goster)
        self.uygulama = uygulama
        self._uygulanan_koyu = None
        self._ikonlar = []  # (PhotoImage, ad, rol): tema değişince yeniden boyanır
        self.title(baslik)
        self.resizable(False, False)
        self._simge = ImageTk.PhotoImage(uygulama.simge_resmi())
        self.iconphoto(True, self._simge)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def tema_secimi(self) -> str:
        """Pencerenin kullanacağı tema; ayarlar penceresi önizleme için değiştirir."""
        return self.uygulama.ayarlar["tema"]

    # ---- ikonlar

    def ikonlu(self, ad: str, metin: str, dugme: bool = False) -> dict:
        """Widget'a verilecek text/image/compound seçenekleri. İkon temanın yazı
        renginde çizilir; dugme=True ise devre dışıyken soluk görünür."""
        if not ikonlar.var_mi():
            return {"text": metin}
        resim = self._yeni_ikon(ad, "yazi")
        if dugme:
            resim = (resim, "disabled", self._yeni_ikon(ad, "soluk"))
        # ttk'da resimle yazı arasında boşluk ayarı yok; başa boşluk konur.
        return {"text": " " + metin, "image": resim, "compound": "left"}

    def _yeni_ikon(self, ad: str, rol: str):
        foto = ImageTk.PhotoImage(self._ikon_ciz(ad, rol), master=self)
        self._ikonlar.append((foto, ad, rol))
        return foto

    def _ikon_ciz(self, ad: str, rol: str):
        r = tema.RENKLER[tema.koyu_mu(self.tema_secimi())]
        # 16 nokta değil 16 piksel: Tk ölçeği (piksel/nokta) 96 DPI'da 4/3'tür.
        boyut = round(16 * float(self.tk.call("tk", "scaling")) * 3 / 4)
        return ikonlar.resim(ad, r[rol], boyut)

    def _tema_ozel(self, r: dict):
        """ttk olmayan parçaları (Text, açılır liste) boyamak için alt sınıflarda."""

    def goster(self):
        """Pencereyi temalı, yerinde ve tamamen çizilmiş olarak gösterir. Önceden pencere
        temasız ve köşede açılıp sonra renk ve yer değiştiriyor, parça parça boyanıyordu."""
        self._temayi_uygula()  # gizliyken: renkler ve koyu başlık çubuğu baştan doğru
        self.update_idletasks()
        g, y = self.winfo_reqwidth(), self.winfo_reqheight()
        x = (self.winfo_screenwidth() - g) // 2
        yy = (self.winfo_screenheight() - y) // 3
        self.geometry(f"+{x}+{yy}")
        hwnd = int(self.wm_frame(), 16)
        tema.ortul(hwnd, True)
        self.deiconify()
        # Windows, hiç gösterilmemiş pencereye verilen koyu başlık ayarını yok sayıyor.
        tema.baslik_cubugu(hwnd, self._uygulanan_koyu)
        self.update()  # örtü altında tamamen boyansın
        tema.ortul(hwnd, False)
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
            # clam bu durumlarda açık gri zemin veriyor; yuvarlak köşelerin dışında görünür.
            stil.map("TButton", foreground=[("disabled", r["soluk"])],
                     background=[("disabled", r["zemin"]), ("pressed", r["zemin"]),
                                 ("active", r["zemin"])])
            for tur in ("TCheckbutton", "TRadiobutton"):
                stil.map(tur, background=[("active", r["zemin"])])
            stil.map("TEntry", background=[("readonly", r["zemin"])])
            stil.map("TCombobox",
                     background=[("active", r["zemin"]), ("pressed", r["zemin"])],
                     selectbackground=[("readonly", r["alan"])],
                     selectforeground=[("readonly", r["yazi"])])
            stil.configure("Vertical.TScrollbar", troughcolor=r["alan"], bordercolor=r["alan"],
                           lightcolor=r["alan"], darkcolor=r["alan"])
            koyu_ogeler.kur(stil, r, self)  # yuvarlak köşeli düğme, kutu vb.
        else:
            stil.theme_use("vista" if "vista" in stil.theme_names() else "default")
        stil.configure("Soluk.TLabel", foreground=r["soluk"])
        stil.configure("Hata.TLabel", foreground=r["hata"])
        stil.configure("Baslik.TLabel", font=("Segoe UI Semibold", 15))
        stil.configure("Baglanti.TLabel", foreground=r["vurgu"], font=("Segoe UI", 9, "underline"))

        self.configure(background=r["zemin"])
        for foto, ad, rol in self._ikonlar:
            foto.paste(self._ikon_ciz(ad, rol))
        self._tema_ozel(r)
        tema.baslik_cubugu(int(self.wm_frame(), 16), koyu)
