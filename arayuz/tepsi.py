"""İkonlu tepsi menüsü. pystray menü öğelerine resim koymayı desteklemiyor; Windows
menüsü kurulurken her öğeye ikonlar.py'nin çizdiği bitmap'i ekliyoruz."""

import pystray

from arayuz import ikonlar

MIIM_BITMAP = 0x80


class Oge(pystray.MenuItem):
    """pystray.MenuItem + ikon adı (ikonlar.GLIFLER'deki anahtar)."""

    def __init__(self, ikon: str | None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ikon = ikon


class Simge(pystray.Icon):
    """koyu_mu: menünün o an koyu çizilip çizilmediğini söyleyen işlev (ikon rengi için).
    Tema değişince update_menu() çağrılmalı ki ikonlar yeni renkle kurulsun."""

    def __init__(self, *args, koyu_mu, **kwargs):
        self._koyu_mu = koyu_mu
        super().__init__(*args, **kwargs)

    def _create_menu_item(self, descriptor, callbacks):
        oge = super()._create_menu_item(descriptor, callbacks)
        ikon = getattr(descriptor, "ikon", None)
        if ikon:
            # İkonlu öğede Windows tik işaretini çizmiyor; işaretliyse vurgulu ikon.
            bitmap = ikonlar.menu_bitmapi(ikon, self._koyu_mu(), bool(descriptor.checked))
            if bitmap:
                oge.fMask |= MIIM_BITMAP
                oge.hbmpItem = bitmap
        return oge
