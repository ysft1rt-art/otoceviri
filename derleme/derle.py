"""Windows sürümünü derler: dist/OtoCeviri/ klasörü ve dist/OtoCeviri-<sürüm>.zip.

Kullanım (proje kökünden):
    pip install -r derleme/gereksinimler.txt
    python derleme/derle.py
"""

import os
import shutil
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

import PyInstaller.__main__  # noqa: E402

from arayuz import logo  # noqa: E402
from cekirdek import surum  # noqa: E402

AD = "OtoCeviri"
GECICI = os.path.join(KOK, "build")
CIKTI = os.path.join(KOK, "dist")

SURUM_BILGISI = """\
VSVersionInfo(
  ffi=FixedFileInfo(filevers={dortlu}, prodvers={dortlu}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041F04B0', [
      StringStruct('CompanyName', 'ysft1rt-art'),
      StringStruct('FileDescription', 'OtoÇeviri'),
      StringStruct('FileVersion', '{surum}'),
      StringStruct('InternalName', '{ad}'),
      StringStruct('LegalCopyright', 'MIT License'),
      StringStruct('OriginalFilename', '{ad}.exe'),
      StringStruct('ProductName', 'OtoÇeviri'),
      StringStruct('ProductVersion', '{surum}'),
    ])]),
    VarFileInfo([VarStruct('Translation', [0x041F, 1200])]),
  ]
)
"""


def simge_olustur(yol):
    boyutlar = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    # Her boyut ayrı çizilir; tek resimden küçültmek küçük boyutlarda bulanık oluyor.
    resimler = [logo.ciz(True, b) for b in boyutlar]
    resimler[-1].save(yol, sizes=[(b, b) for b in boyutlar], append_images=resimler[:-1])


def surum_bilgisi_olustur(yol):
    parcalar = [int(p) for p in surum.SURUM.split(".")]
    dortlu = tuple((parcalar + [0, 0, 0, 0])[:4])
    with open(yol, "w", encoding="utf-8") as f:
        f.write(SURUM_BILGISI.format(dortlu=dortlu, surum=surum.SURUM, ad=AD))


def main():
    os.makedirs(GECICI, exist_ok=True)
    simge = os.path.join(GECICI, "otoceviri.ico")
    bilgi = os.path.join(GECICI, "surum_bilgisi.txt")
    simge_olustur(simge)
    surum_bilgisi_olustur(bilgi)

    PyInstaller.__main__.run([
        os.path.join(KOK, "otoceviri.py"),
        "--name", AD,
        "--onedir",  # tek dosyaya göre çok daha hızlı açılır, antivirüsler de daha az takılır
        "--noconsole",
        "--noconfirm",
        "--clean",
        "--icon", simge,
        "--version-file", bilgi,
        "--paths", KOK,
        # pyperclip ve pystray başka platformlar için Qt/GTK'yı da dener; Windows'ta
        # gereksiz, ortamda kuruluysa paketi 100 MB'tan fazla şişiriyor.
        *[a for m in ("PySide6", "PySide2", "PyQt5", "PyQt6", "qtpy", "shiboken6",
                      "shiboken2", "gi", "Xlib", "AppKit", "Foundation")
          for a in ("--exclude-module", m)],
        "--distpath", CIKTI,
        "--workpath", os.path.join(GECICI, "pyinstaller"),
        "--specpath", GECICI,
    ])

    klasor = os.path.join(CIKTI, AD)
    shutil.copy(os.path.join(KOK, "LICENSE"), os.path.join(klasor, "LICENSE.txt"))
    zip_adi = os.path.join(CIKTI, f"{AD}-{surum.SURUM}")
    shutil.make_archive(zip_adi, "zip", CIKTI, AD)
    print(f"\nHazır: {klasor}\n       {zip_adi}.zip")


if __name__ == "__main__":
    main()
