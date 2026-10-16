"""Kısayol metinlerini ('ctrl+shift+u') doğrulama ve normalleştirme."""

import keyboard

DEGISTIRICILER = ("ctrl", "shift", "alt", "windows")
_ESANLAMLAR = {"control": "ctrl", "win": "windows", "left windows": "windows",
               "right windows": "windows", "alt gr": "alt"}


def normallestir(ham: str) -> tuple[str | None, str | None]:
    """(normal_kisayol, hata_mesaji) döndürür; ikisinden biri None'dır."""
    parcalar = []
    for p in ham.split("+"):
        p = p.strip().lower().replace("left ", "").replace("right ", "")
        p = _ESANLAMLAR.get(p, p)
        if p and p not in parcalar:
            parcalar.append(p)
    degistiriciler = [d for d in DEGISTIRICILER if d in parcalar]
    tuslar = [p for p in parcalar if p not in DEGISTIRICILER]

    if len(tuslar) != 1:
        return None, "Bir harf ya da tuş ile birlikte Ctrl/Alt/Win kullan (ör. Ctrl+Shift+U)."
    if not {"ctrl", "alt", "windows"} & set(degistiriciler):
        return None, "Kısayol Ctrl, Alt ya da Win tuşu içermeli; yoksa yazı yazmayı engeller."
    try:
        keyboard.key_to_scan_codes(tuslar[0])
    except ValueError:
        return None, f"'{tuslar[0]}' tuşu tanınmadı."
    return "+".join(degistiriciler + tuslar), None


def ayristir(kisayol: str) -> tuple[str, set[str]]:
    """'ctrl+shift+u' -> ('u', {'ctrl', 'shift'})"""
    parcalar = kisayol.split("+")
    return parcalar[-1], set(parcalar[:-1])


def goster(kisayol: str) -> str:
    """'ctrl+shift+u' -> 'Ctrl+Shift+U'"""
    return "+".join(p.capitalize() if len(p) > 1 else p.upper() for p in kisayol.split("+"))
