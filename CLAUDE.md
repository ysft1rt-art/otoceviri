# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

OtoÇeviri is a Windows-only tray app (Python 3.10+, developed on 3.13) that intercepts Enter or a hotkey, copies the focused text box, translates it via Google Translate's free web endpoint, restores the user's writing style (case, trailing punctuation, emojis), pastes it back and (in Enter mode) sends it. All identifiers, comments, log messages and commit messages are in Turkish — keep it that way. User-facing docs exist in English (`README.md`, primary) and Turkish (`README.tr.md`); keep both in sync.

## Commands

```bash
pip install -r requirements.txt          # runtime deps: keyboard, pyperclip, pystray, pillow
python otoceviri.py                      # run from source (baslat.bat runs it via pythonw, no console)
python -m cekirdek.ceviri en "metin"     # test translation + style preservation alone, no hooks/tray
pip install -r derleme/gereksinimler.txt # adds PyInstaller
python derleme/derle.py                  # build → dist/OtoCeviri/ and dist/OtoCeviri-<SURUM>.zip
```

There is no test suite or linter configured. Only one instance can run at a time (named mutex); if the user's own copy is running, a second launch just shows "already running".

## Architecture

**Threads.** `otoceviri.py` (`OtoCeviri` class) owns everything. The main thread runs the pystray icon (`arayuz/tepsi.py`). `keyboard` hooks fire on the hook thread and must return fast: the Enter hook (`suppress=True`) swallows the key and hands work to a daemon thread (`_enter_isle`), guarded by the `_mesgul` lock; `_gecir` prevents re-catching the Enter the app itself sends. Tkinter windows run on a single persistent Tk thread in `arayuz/pencere.py` — open windows only through `pencere.ac(Sinif, uygulama)` from any thread; never create a new Tk root or touch Tk objects from other threads (doing so crashed tcl86t.dll). All windows subclass `pencere.TemaliPencere`.

**Translation (`cekirdek/ceviri.py`).** A hand-rolled keep-alive HTTPS connection (`_KaliciBaglanti`) per Google host, with fallback host, LRU cache and warm-up (`isit()`, called at startup and while the user types when `isinmali_mi()`). Connections are **forced to IPv4** (`AF_INET`) — the developer's network has broken IPv6 TLS to Google, so don't remove this. Google drops idle connections after ~240 s. `cevrilmeli_mi()` decides skips (commands, links, emoji-only, already target language); `tarzi_koru()` restores style. Keep Google as the engine unless asked otherwise.

**Settings.** `ayarlar.json` next to the script/exe (git-ignored), merged over `VARSAYILAN_AYARLAR` in `otoceviri.py`; invalid values fall back to defaults. "Start with Windows" lives in the HKCU Run registry key (`cekirdek/baslangic.py`), not in the JSON. When adding a setting, update the defaults, the settings window, and the config table in both READMEs.

**UI text.** All strings go through `t(key, **kw)` from `cekirdek/metinler.py`, which holds `tr` and `en` blocks with identical keys — add every new key to both. Theme (light/dark/system, live-follows Windows) is in `arayuz/tema.py`; dark-mode widgets in `arayuz/koyu_ogeler.py`; icons are Segoe Fluent glyphs (`arayuz/ikonlar.py`); the app logo is drawn in code (`arayuz/logo.py`) and reused for tray, windows and the `.exe` icon.

**Frozen vs source.** Code branches on `sys.frozen` (app dir = exe dir when frozen), so the build must stay PyInstaller `--onedir`.

**Auto-update (`cekirdek/guncelleme.py`).** Only works in the built exe. Checks the latest GitHub release for an asset named exactly `OtoCeviri-<version>.zip`, verifies sha256 from the API digest, extracts to a temp dir and launches the new exe with `--guncellemeyi-kur <install_dir> <pid>` (handled at the top of `main()`), which waits for the old process, swaps files (leaving `ayarlar.json`/log alone) and relaunches.

## Releasing

Bump `SURUM` in `cekirdek/surum.py` (also stamped into the exe's version info), build, then the user creates the GitHub release by hand and uploads the zip without renaming it (no `gh` CLI on this machine). For end-to-end testing of a build, don't clobber a released zip in `dist/` (`derle.py` always writes to `<repo>/dist`, so test from a copy of the repo elsewhere), and note that running a test exe rewrites the HKCU Run entry to its path — restore it afterwards.
