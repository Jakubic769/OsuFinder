<!-- 🎵 osu!finder --> <div align="center">
🎵 osu!finder

Fast & simple osu! beatmap finder for desktop.

<p> <img src="docs/screenshots/main.png" width="850" alt="Main window screenshot"> </p> <p> Search, preview and download osu! beatmaps — without logging in. </p> <p> <a href="https://github.com/jakubic769/OsuFinder/releases"> <img src="https://img.shields.io/github/v/release/jakubic769/OsuFinder?style=for-the-badge" alt="GitHub release"> </a> <a href="https://github.com/jakubic769/OsuFinder/stargazers"> <img src="https://img.shields.io/github/stars/jakubic769/OsuFinder?style=for-the-badge" alt="GitHub stars"> </a> <a href="https://github.com/jakubic769/OsuFinder/issues"> <img src="https://img.shields.io/github/issues/jakubic769/OsuFinder?style=for-the-badge" alt="GitHub issues"> </a> <a href="LICENSE"> <img src="https://img.shields.io/github/license/jakubic769/OsuFinder?style=for-the-badge" alt="License"> </a> </p> </div>
✨ Features
🔎 Search osu! beatmaps by title, artist, or mapper
🎮 Game modes: osu!, Taiko, Catch, Mania
⭐ Star difficulty filter with sliders
📊 Status filter: Ranked, Loved, Qualified, Pending, Graveyard
🖼️ Beatmap covers and detailed beatmap view
⬇️ Download .osz files directly to your system
📦 Import .osz, .zip, .7z, and .rar files
🎨 Custom themes — colors, backgrounds, opacity, and more
🖼️ Custom background images copied locally to the application folder
⚡ Smooth animations and responsive UI
⌨️ Keyboard shortcuts
🌍 Multi-language support: English, Polish, German, Russian
📥 Installation
🪟 Windows .exe

Download the latest version from the Releases page and run:

osu-finder.exe


No Python installation required.

🐍 Run with Python

Requirements:

Python 3.11+
Git

Clone the repository:

git clone https://github.com/jakubic769/OsuFinder.git
cd OsuFinder


Create and activate a virtual environment:

Windows:

python -m venv .venv
.venv\Scripts\activate


macOS / Linux:

python3 -m venv .venv
source .venv/bin/activate


Install dependencies:

pip install -r requirements.txt


Run the application:

python osu_finder.py

🧠 How It Works
Search
  ↓
osu! beatmap API (mirror)
  ↓
Beatmap results
  ↓
Choose a map
  ↓
Download .osz
  ↓
Open / install in osu!


The application uses a public osu! API mirror and does not require an osu! account.

🎨 Customization

osu!finder provides extensive customization options.

You can change:

🖼️ Background image
🌫️ Background opacity
🎨 Accent color
🔤 Text colors
🪟 Panels and borders
🎭 Theme presets

Background images can have any aspect ratio and are copied locally to the application folder.

💾 Themes

Theme presets can be exported and imported as JSON files.

Application settings are stored locally in:

~/.osu-finder/

🌍 Languages

The interface is currently available in:

Language	Code
🇵🇱 Polish	pl
🇬🇧 English	en
🇩🇪 German	de
🇷🇺 Russian	ru

You can switch the language at any time using the „JĘZYK” section in the sidebar.

Your language preference is saved automatically in:

~/.osu-finder/language.json

⌨️ Keyboard Shortcuts
Key	Action
Ctrl + L	Focus search
/	Focus search
Enter	Search
Esc	Close dialog
📸 Screenshots
<p align="center"> <img src="docs/screenshots/main.png" width="48%" alt="Main window"> <img src="docs/screenshots/details.png" width="48%" alt="Details dialog"> </p>
🛠️ Built With
🐍 Python
🖥️ PySide6 — Qt for Python
🌐 Requests
🎵 osu! beatmap API mirrors
🚧 Roadmap
 More beatmap sources
 Favorites
 Download history
 Automatic osu! installation
 More customization options
 Additional languages
⚠️ Disclaimer

osu!finder is an unofficial community project and is not affiliated with osu! or ppy.

🤝 Contributing

Contributions are welcome!

If you have an idea, find a bug, or want to improve the project, feel free to:

Open an issue
Suggest a new feature
Submit a pull request
📄 License

This project is licensed under the MIT License.

See the LICENSE file for more information.

⭐ Support the Project

If you like osu!finder, consider giving the project a ⭐ on GitHub!

<p align="center"> <a href="https://github.com/jakubic769/OsuFinder"> <strong>⭐ Star osu!finder on GitHub</strong> </a> </p>
