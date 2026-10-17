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
        self._tik_yeri = []  # iç içe kurulan menülerin her biri için: tik yeri var mı
        super().__init__(*args, **kwargs)

    def _create_menu(self, descriptors, callbacks):
        # Menüde işaretlenebilir öğe varsa tüm ikonlu öğelere tik yeri açılır; ikonlar hizalı kalır.
        self._tik_yeri.append(any(
            getattr(d, "ikon", None) and d.checked is not None for d in descriptors or ()
        ))
        try:
            return super()._create_menu(descriptors, callbacks)
        finally:
            self._tik_yeri.pop()

    def _create_menu_item(self, descriptor, callbacks):
        oge = super()._create_menu_item(descriptor, callbacks)
        ikon = getattr(descriptor, "ikon", None)
        if ikon:
            # İkonlu öğede Windows tik işaretini çizmiyor; tik ikonun yanına çizilir.
            isaret = bool(descriptor.checked) if self._tik_yeri[-1] else None
            bitmap = ikonlar.menu_bitmapi(ikon, self._koyu_mu(), isaret)
            if bitmap:
                oge.fMask |= MIIM_BITMAP
                oge.hbmpItem = bitmap
        return oge
