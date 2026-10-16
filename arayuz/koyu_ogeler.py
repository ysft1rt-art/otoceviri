"""Koyu tema için yuvarlak köşeli ttk öğeleri.

Açık temada 'vista' teması Windows'un kendi (yuvarlak köşeli) çizimini kullanır ama
renklendirilemez; koyu temada kullanılan 'clam' ise her şeyi köşeli çizer. Bu yüzden
koyu temada düğme, giriş/açılır kutu, işaret kutusu, bölüm çerçevesi ve kaydırma
çubuğu PIL ile çizilen resimlerden kurulur. Resimler DPI ölçeğine göre çizilir.
"""

from PIL import Image, ImageDraw, ImageTk

KAT = 4  # yumuşak kenar için büyük çizip küçültme katı
# Resimlerin kenar payı dışında kalan ortası. Tk ortayı döşeyerek büyütür; orta 1 piksel
# olursa geniş bir çerçeve binlerce parçayla çizilir ve pencere donmuş gibi olur.
ORTA = 24


def _ciz(genislik: int, yukseklik: int, ciz) -> Image.Image:
    """ciz(d, k) KAT kat büyük tuvale çizer; k = bir pikselin büyütülmüş karşılığı."""
    tuval = Image.new("RGBA", (genislik * KAT, yukseklik * KAT), (0, 0, 0, 0))
    ciz(ImageDraw.Draw(tuval), KAT)
    return tuval.resize((genislik, yukseklik), Image.LANCZOS)


def _kutu(boyut: int, yaricap: int, dolgu: str, kenar: str, alt: str | None = None,
          alt_kalinlik: int = 1) -> Image.Image:
    """Kenarlıklı yuvarlak dikdörtgen; alt verilirse alt kenar o renkte (odak çizgisi)."""
    k, s = KAT, boyut * KAT
    tam = (0, 0, s - 1, s - 1)
    tuval = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(tuval).rounded_rectangle(tam, yaricap * k, fill=kenar)
    if not alt:
        alt_kalinlik = 1
    else:  # aynı şekli alt renkte çizip yalnızca en alttaki şeridini al
        serit = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(serit).rounded_rectangle(tam, yaricap * k, fill=alt)
        y = s - alt_kalinlik * k
        tuval.paste(serit.crop((0, y, s, s)), (0, y))
    ImageDraw.Draw(tuval).rounded_rectangle(
        (k, k, s - k - 1, s - alt_kalinlik * k - 1), (yaricap - 1) * k, fill=dolgu
    )
    return tuval.resize((boyut, boyut), Image.LANCZOS)


def _isaret(boyut: int, bosluk: int, dolgu: str, kenar: str, tik: str | None) -> Image.Image:
    """İşaret kutusu; sağında yazıyla arasında kalacak saydam boşluk."""
    def ciz(d, k):
        s = boyut * k
        d.rounded_rectangle((0, 0, s - 1, s - 1), 3 * k, fill=kenar)
        if tik is None:
            d.rounded_rectangle((k, k, s - k - 1, s - k - 1), 2 * k, fill=dolgu)
        else:
            d.line([(s * 0.24, s * 0.52), (s * 0.42, s * 0.70), (s * 0.77, s * 0.32)],
                   fill=tik, width=round(1.4 * k), joint="curve")
    return _ciz(boyut + bosluk, boyut, ciz)


def _secenek(boyut: int, bosluk: int, dolgu: str, kenar: str, nokta: str | None) -> Image.Image:
    """Seçenek (radyo) düğmesi; sağında saydam boşluk."""
    def ciz(d, k):
        s = boyut * k
        d.ellipse((0, 0, s - 1, s - 1), fill=kenar)
        if nokta is None:
            d.ellipse((k, k, s - k - 1, s - k - 1), fill=dolgu)
        else:
            y = s * 0.2
            d.ellipse((s / 2 - y, s / 2 - y, s / 2 + y, s / 2 + y), fill=nokta)
    return _ciz(boyut + bosluk, boyut, ciz)


def _ok(genislik: int, yukseklik: int, renk: str) -> Image.Image:
    """Açılır kutunun aşağı bakan ince oku (Windows 11'deki gibi)."""
    def ciz(d, k):
        g, y = genislik * k, yukseklik * k
        d.line([(g * 0.32, y * 0.42), (g * 0.5, y * 0.6), (g * 0.68, y * 0.42)],
               fill=renk, width=k, joint="curve")
    return _ciz(genislik, yukseklik, ciz)


def _kaydirma(genislik: int, kalinlik: int, renk: str) -> Image.Image:
    """Kaydırma çubuğunun ince, uçları yuvarlak tutamağı."""
    yukseklik = kalinlik + ORTA
    def ciz(d, k):
        x = (genislik - kalinlik) / 2 * k
        d.rounded_rectangle((x, 0, x + kalinlik * k - 1, yukseklik * k - 1), kalinlik * k / 2,
                            fill=renk)
    return _ciz(genislik, yukseklik, ciz)


def kur(stil, r: dict, pencere):
    """'clam' teması seçiliyken çağrılır. Öğeler Tk yorumlayıcısı başına bir kez kurulur;
    düzenler (layout) yalnızca clam'e ait olduğu için açık temayı etkilemez."""
    if "Yuv.Button.border" in stil.element_names():
        return
    olcek = float(pencere.tk.call("tk", "scaling")) * 3 / 4  # 96 DPI'da 1
    def px(n):
        return max(1, round(n * olcek))

    kok = pencere._root()
    resimler = kok.__dict__.setdefault("_koyu_ogeler", [])  # Tk resimleri silinmesin

    def tk_resmi(resim):
        foto = ImageTk.PhotoImage(resim, master=kok)
        resimler.append(foto)
        return foto

    yaricap = px(4)
    kenar = yaricap + 1
    boyut = 2 * kenar + ORTA
    en_az = {"width": 2 * kenar, "height": 2 * kenar}  # yoksa öğe resim kadar büyük olur

    # -- Düğme
    dugme = {d: tk_resmi(_kutu(boyut, yaricap, dolgu, cerceve)) for d, dolgu, cerceve in [
        ("normal", r["dugme"], r["kenar"]),
        ("uzerinde", r["dugme_uzerinde"], r["kenar"]),
        ("basili", r["zemin"], r["kenar"]),
        ("devre_disi", r["zemin"], r["kenar"]),
        ("odak", r["dugme"], r["vurgu"]),
    ]}
    stil.element_create(
        "Yuv.Button.border", "image", dugme["normal"],
        ("disabled", dugme["devre_disi"]), ("pressed", dugme["basili"]),
        ("active", dugme["uzerinde"]), ("focus", dugme["odak"]),
        border=kenar, padding=px(2), sticky="nsew", **en_az,
    )
    stil.layout("TButton", [("Yuv.Button.border", {"sticky": "nswe", "children": [
        ("Button.padding", {"sticky": "nswe", "children": [
            ("Button.label", {"sticky": "nswe"})]})]})])
    stil.configure("TButton", padding=(px(8), px(2)), anchor="center")

    # -- Giriş ve açılır kutu
    alan = {d: tk_resmi(_kutu(boyut, yaricap, dolgu, r["kenar"], alt, px(alt_kalinlik)))
            for d, dolgu, alt, alt_kalinlik in [
                ("normal", r["alan"], r["kutu_kenari"], 1),
                ("uzerinde", r["dugme_uzerinde"], r["kutu_kenari"], 1),
                ("odak", r["alan"], r["vurgu"], 2),
            ]}
    stil.element_create(
        "Yuv.Alan.field", "image", alan["normal"],
        ("focus", alan["odak"]), ("active", alan["uzerinde"]),
        border=kenar, padding=(px(6), px(2)), sticky="nsew", **en_az,
    )
    stil.element_create("Yuv.Combobox.downarrow", "image", tk_resmi(_ok(px(20), px(16), r["yazi"])),
                        sticky="")
    stil.layout("TEntry", [("Yuv.Alan.field", {"sticky": "nswe", "children": [
        ("Entry.padding", {"sticky": "nswe", "children": [
            ("Entry.textarea", {"sticky": "nswe"})]})]})])
    stil.layout("TCombobox", [("Yuv.Alan.field", {"sticky": "nswe", "children": [
        ("Yuv.Combobox.downarrow", {"side": "right", "sticky": "ns"}),
        ("Combobox.padding", {"expand": "1", "sticky": "nswe", "children": [
            ("Combobox.textarea", {"sticky": "nswe"})]})]})])
    stil.configure("TEntry", padding=px(1))
    stil.configure("TCombobox", padding=px(1))

    # -- İşaret kutusu ve seçenek düğmesi
    gosterge, bosluk = px(14), px(4)
    for tur, ciz, isaret in [("Checkbutton", _isaret, "#ffffff"), ("Radiobutton", _secenek, "#ffffff")]:
        bos = tk_resmi(ciz(gosterge, bosluk, r["alan"], r["kutu_kenari"], None))
        bos_uzerinde = tk_resmi(ciz(gosterge, bosluk, r["dugme_uzerinde"], r["yazi"], None))
        secili = tk_resmi(ciz(gosterge, bosluk, None, r["vurgu"], isaret))
        secili_uzerinde = tk_resmi(ciz(gosterge, bosluk, None, r["vurgu_uzerinde"], isaret))
        stil.element_create(
            f"Yuv.{tur}.indicator", "image", bos,
            ("selected", "active", secili_uzerinde), ("selected", secili),
            ("active", bos_uzerinde), sticky="",
        )
        stil.layout(f"T{tur}", [(f"{tur}.padding", {"sticky": "nswe", "children": [
            (f"Yuv.{tur}.indicator", {"side": "left", "sticky": ""}),
            (f"{tur}.focus", {"side": "left", "sticky": "w", "children": [
                (f"{tur}.label", {"sticky": "nswe"})]})]})])

    # -- Bölüm çerçevesi
    stil.element_create(
        "Yuv.Labelframe.border", "image",
        tk_resmi(_kutu(boyut, yaricap, r["zemin"], r["kenar"])),
        border=kenar, sticky="nsew", **en_az,
    )
    stil.layout("TLabelframe", [("Yuv.Labelframe.border", {"sticky": "nswe"})])
    # Başlık clam'deki gibi çerçevenin dışında değil, açık temadaki gibi çizginin üstünde.
    stil.configure("TLabelframe", labeloutside=False, labelmargins=(px(6), 0, px(6), 0))

    # -- Kaydırma çubuğu (Windows 11'deki gibi oksuz, ince)
    genislik, kalinlik = px(12), px(4)
    tutamak = tk_resmi(_kaydirma(genislik, kalinlik, r["kaydirma"]))
    tutamak_uzerinde = tk_resmi(_kaydirma(genislik, kalinlik, r["soluk"]))
    stil.element_create(
        "Yuv.Vertical.Scrollbar.thumb", "image", tutamak,
        ("pressed", tutamak_uzerinde), ("active", tutamak_uzerinde),
        border=(0, kalinlik // 2 + 1, 0, kalinlik // 2 + 1), sticky="nsew",
    )
    stil.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
        ("Yuv.Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
