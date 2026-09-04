# 🎵 osu!finder

> **Fast & simple osu! beatmap finder for desktop.**

<p align="center">
  <img src="docs/screenshots/main.png" width="850">
</p>

<p align="center">
  Search, preview and download osu! beatmaps — without logging in.
</p>

---

## ✨ Features

* 🔎 Search osu! beatmaps
* 🎮 osu! / Taiko / Catch / Mania
* ⭐ Star difficulty filters
* 📊 Ranked, Loved, Qualified, Pending & Graveyard
* 🖼️ Beatmap covers & details
* ⬇️ Download `.osz`
* 📦 Import `.osz`, `.zip`, `.7z`, `.rar`
* 🎨 Custom themes & colors
* 🖼️ Custom background images
* ⚡ Smooth animations & responsive UI
* ⌨️ Keyboard shortcuts

---

## 📥 Installation

### 🪟 Windows `.exe`

Download the latest release and run:

```text
osu-finder.exe
```

No Python required.

### 🐍 Run with Python

**Requirements:** Python 3.11+

```bash
git clone https://github.com/YOUR_USERNAME/osu-finder.git
cd osu-finder

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python osu_finder.py
```

---

## 🧠 How does it work?

```text
Search
  ↓
osu! beatmap API
  ↓
Beatmap results
  ↓
Choose a map
  ↓
Download .osz
  ↓
Open / install in osu!
```

The app uses a public osu! API mirror and **does not require an osu! account**.

---

## 🎨 Customization

You can change:

* Background image
* Background opacity
* Accent color
* Text colors
* Panels & borders
* Theme presets

Themes are saved locally in:

```text
~/.osu-finder/
```

---

## ⌨️ Shortcuts

| Key        | Action       |
| ---------- | ------------ |
| `Ctrl + L` | Focus search |
| `/`        | Focus search |
| `Enter`    | Search       |
| `Esc`      | Close dialog |

---

## 🛠️ Built with

* Python
* PySide6
* Requests
* osu! beatmap APIs

---

## 📸 Screenshots

<p align="center">
  <img src="docs/screenshots/main.png" width="48%">
  <img src="docs/screenshots/details.png" width="48%">
</p>

---

## 🚧 Roadmap

* [ ] More beatmap sources
* [ ] Favorites
* [ ] Download history
* [ ] Automatic osu! installation
* [ ] More customization

---

## ⚠️ Disclaimer

osu!finder is an unofficial community project and is **not affiliated with osu! or ppy**.

---

⭐ **If you like the project, consider giving it a star!**
