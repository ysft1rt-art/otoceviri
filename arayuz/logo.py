"""Uygulama simgesi: tepsi simgesi, pencere simgesi ve .exe simgesi aynı çizimden."""

from PIL import Image, ImageDraw, ImageFont

YESIL = (34, 160, 90)
GRI = (120, 120, 120)


def ciz(aktif: bool = True, boyut: int = 64) -> Image.Image:
    renk = YESIL if aktif else GRI
    o = boyut / 64  # çizim 64 piksele göre tasarlandı
    resim = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
    ciz = ImageDraw.Draw(resim)
    ciz.rounded_rectangle((2 * o, 2 * o, 62 * o, 62 * o), radius=14 * o, fill=renk)
    try:
        yazi_tipi = ImageFont.truetype("segoeuib.ttf", round(40 * o))
    except OSError:
        yazi_tipi = ImageFont.load_default(round(40 * o))
    ciz.text((32 * o, 33 * o), "Ç", font=yazi_tipi, fill="white", anchor="mm")
    return resim
