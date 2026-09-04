from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

try:
    from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
    from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap, QKeySequence, QShortcut, QPainterPath, QRegion, QLinearGradient, QBrush
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
        QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
        QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
        QSlider, QSpinBox, QSplitter, QStyle, QToolButton, QVBoxLayout, QWidget,
        QProgressBar, QGraphicsOpacityEffect
    )
except ImportError:
    print("Brak PySide6. Zainstaluj zależności poleceniem: python -m pip install -r requirements.txt")
    raise


APP_NAME = "osu!finder"
API_BASE = "https://mirror.hinamizawa.ai/api/v1/hinai"
USER_AGENT = "osu-finder-python/1.1"
APP_DIR = Path.home() / ".osu-finder"
SETTINGS_PATH = APP_DIR / "theme.json"
LANGUAGE_PATH = APP_DIR / "language.json"
DOWNLOAD_DIR = Path.home() / "Downloads" / "osu-finder"

STATUS_FILTERS = {
    "Wszystkie": None,
    "Ranked": 1,
    "Loved": 4,
    "Qualified": 3,
    "Pending": 0,
    "Graveyard": "graveyard",
}
STATUS_MAP = {
    1: ("Ranked", "ranked"),
    2: ("Approved", "ranked"),
    3: ("Qualified", "qualified"),
    4: ("Loved", "loved"),
    0: ("Pending", "pending"),
    -2: ("Graveyard", "graveyard"),
}
MODE_NAMES = {-1: "Wszystkie", 0: "osu!", 1: "Taiko", 2: "Catch", 3: "Mania"}
MODE_ICONS = {0: "○", 1: "🥁", 2: "🍎", 3: "🎹"}

DEFAULT_THEME = {
    "background": "#0f1115",
    "surface": "#171a1f",
    "panel": "#20242b",
    "panel_hover": "#292e36",
    "text": "#f3f5f7",
    "muted": "#929aa5",
    "border": "#363c46",
    "accent": "#ff669f",
    "accent_text": "#ffffff",
    "success": "#57d98c",
    "warning": "#e7b75b",
    "danger": "#ec6a6a",
    "background_image": "",
    "image_opacity": 42,
    "image_overlay": 10,
}


# ─────────────────────────────────────────────────────────────────────────────
#  Internationalisation (i18n)
# ─────────────────────────────────────────────────────────────────────────────

class I18n:
    """Simple translation manager for osu!finder."""

    def __init__(self):
        self.current_lang = "pl"
        self.translations = {
            "pl": {},
            "en": {},
            "de": {},
            "ru": {},
        }
        self._load_language_preference()
        self._init_translations()

    def _load_language_preference(self):
        try:
            if LANGUAGE_PATH.exists():
                data = json.loads(LANGUAGE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "language" in data:
                    lang = data["language"]
                    if lang in self.translations:
                        self.current_lang = lang
        except Exception:
            pass

    def _save_language_preference(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        LANGUAGE_PATH.write_text(
            json.dumps({"language": self.current_lang}, indent=2),
            encoding="utf-8"
        )

    def set_language(self, lang: str):
        if lang not in self.translations:
            return
        self.current_lang = lang
        self._save_language_preference()

    def tr(self, key: str, **kwargs) -> str:
        """Return translated string for current language."""
        translation = self.translations.get(self.current_lang, {}).get(key)
        if translation is None:
            # fallback to Polish (default)
            translation = self.translations.get("pl", {}).get(key, key)
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return translation

    def _init_translations(self):
        # Polish (default)
        self.translations["pl"] = {
            "app_name": "osu!finder",
            "search_placeholder": "Wyszukaj beatmapę, artystę lub mappera…",
            "search_button": "Szukaj",
            "import_button": "Importuj",
            "theme_button": "Motyw",
            "mode_label": "TRYB GRY",
            "mode_all": "Wszystkie",
            "mode_osu": "osu!",
            "mode_taiko": "Taiko",
            "mode_catch": "Catch",
            "mode_mania": "Mania",
            "status_label": "STATUS",
            "status_all": "Wszystkie",
            "status_ranked": "Ranked",
            "status_loved": "Loved",
            "status_qualified": "Qualified",
            "status_pending": "Pending",
            "status_graveyard": "Graveyard",
            "stars_label": "STAR RATING",
            "stars_min": "Min",
            "stars_max": "Max",
            "sort_label": "SORTOWANIE",
            "sort_relevance": "Trafność",
            "sort_title": "Tytuł",
            "sort_artist": "Artysta",
            "sort_difficulty": "Trudność",
            "sort_updated": "Ostatnia aktualizacja",
            "import_note": (
                "Pobieranie zapisuje .osz w folderze Downloads/osu-finder i otwiera go przez systemowe skojarzenie plików.\n\n"
                ".zip → .osz bez ponownego kompresowania. .7z i .rar wymagają odpowiednich bibliotek."
            ),
            "theme_info": "Motyw zapisuje się lokalnie • tapeta jest kopiowana do profilu aplikacji",
            "result_searching": "Wyszukiwanie…",
            "result_count": "{count} wyników",
            "page_label": "Strona {page}",
            "prev_button": "‹ Poprzednia",
            "next_button": "Następna ›",
            "error_connection": "Błąd połączenia: {error}",
            "error_generic": "Błąd: {error}",
            "error_search_title": "Nie udało się wyszukać beatmap",
            "error_search_text": "{error}",
            "card_loading_cover": "Ładowanie okładki…",
            "card_unknown_title": "Bez tytułu",
            "card_unknown_artist": "Nieznany artysta",
            "status_approved": "Approved",
            "details_title": "{title} — osu!finder",
            "details_creator": "👤 {creator}",
            "details_last_update": "📅 {date}",
            "details_video": "🎬 Wideo",
            "details_no_video": "Bez wideo",
            "details_download": "Pobierz .osz",
            "details_download_no_video": "Bez wideo",
            "details_open_osu": "Otwórz na osu!",
            "details_close": "Zamknij",
            "details_downloading": "Pobieranie…",
            "details_download_success_title": "Gotowe",
            "details_download_success_text": "Pobrano i otwarto plik:\n{path}\n\nJeśli osu! nie uruchomiło importu, przeciągnij plik do osu! lub otwórz go ręcznie.",
            "details_download_error_title": "Błąd pobierania",
            "details_download_error_text": "{error}",
            "details_ar": "AR",
            "details_cs": "CS",
            "details_od": "OD",
            "details_hp": "HP",
            "details_combo": "Combo",
            "theme_dialog_title": "Wygląd — osu!finder",
            "theme_background": "Tło",
            "theme_surface": "Powierzchnia",
            "theme_panel": "Panel / pola",
            "theme_text": "Tekst",
            "theme_muted": "Tekst drugorzędny",
            "theme_border": "Obramowania",
            "theme_accent": "Kolor akcentu",
            "theme_image_path": "Obraz tła",
            "theme_image_placeholder": "JPG / JPEG / PNG / WEBP / BMP / GIF — np. 1920×1020",
            "theme_image_select": "Wybierz…",
            "theme_image_opacity": "Widoczność obrazu",
            "theme_info_text": (
                "Tapeta jest kopiowana do folderu aplikacji, więc nie zniknie po przeniesieniu oryginalnego pliku. "
                "Możesz użyć JPG, JPEG, PNG, WEBP, BMP lub GIF; proporcje mogą być dowolne."
            ),
            "theme_export": "Eksportuj motyw…",
            "theme_import": "Importuj motyw…",
            "theme_reset": "Przywróć domyślny",
            "theme_save_title": "Motyw zapisany",
            "theme_save_text": "Zapisano motyw:\n{path}",
            "theme_import_title": "Wczytaj motyw",
            "theme_import_error_title": "Nieprawidłowy motyw",
            "theme_import_error_text": "{error}",
            "theme_background_error_title": "Nieprawidłowy obraz",
            "theme_background_error_text": "{error}",
            "language_label": "JĘZYK",
            "language_pl": "Polski",
            "language_en": "English",
            "language_de": "Deutsch",
            "language_ru": "Русский",
            "import_local_title": "Importuj beatmapę",
            "import_local_filter": "osu! / archiwa (*.osz *.zip *.7z *.rar)",
            "import_local_success_title": "Import gotowy",
            "import_local_success_text": "Gotowe:\n{path}\n\nPlik został otwarty przez systemowe skojarzenie osu!.",
            "import_local_error_title": "Nie udało się zaimportować pliku",
            "import_local_error_text": "{error}",
            "error_invalid_zip": "ZIP nie zawiera pliku .osu — to nie wygląda na beatmapę osu!.",
            "error_7z_missing": "Dla .7z doinstaluj bibliotekę py7zr: pip install py7zr",
            "error_rar_missing": "Dla .rar doinstaluj bibliotekę rarfile: pip install rarfile",
            "error_unsupported_format": "Nieobsługiwany format. Wybierz .osz, .zip, .7z lub .rar.",
            "error_no_osu_files": "Archiwum nie zawiera plików .osu — to nie wygląda na beatmapę osu!.",
            "error_file_not_found": "Nie znaleziono pliku: {path}",
            "error_invalid_image": "Obsługiwane obrazy: JPG, JPEG, PNG, WEBP, BMP, GIF.",
            "status_unknown": "Nieznany",
            "file_filter_images": "Obrazy (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
            "file_filter_theme_json": "Motyw JSON (*.json)",
            "error_theme_json_object": "Plik motywu musi zawierać obiekt JSON.",
            "error_invalid_v2_response": "Nieprawidłowa odpowiedź v2: brak listy wyników",
            "error_invalid_api_response": "API zwróciło nieprawidłowy format danych",
        }

        # English
        self.translations["en"] = {
            "app_name": "osu!finder",
            "search_placeholder": "Search beatmap, artist or mapper…",
            "search_button": "Search",
            "import_button": "Import",
            "theme_button": "Theme",
            "mode_label": "GAME MODE",
            "mode_all": "All",
            "mode_osu": "osu!",
            "mode_taiko": "Taiko",
            "mode_catch": "Catch",
            "mode_mania": "Mania",
            "status_label": "STATUS",
            "status_all": "All",
            "status_ranked": "Ranked",
            "status_loved": "Loved",
            "status_qualified": "Qualified",
            "status_pending": "Pending",
            "status_graveyard": "Graveyard",
            "stars_label": "STAR RATING",
            "stars_min": "Min",
            "stars_max": "Max",
            "sort_label": "SORTING",
            "sort_relevance": "Relevance",
            "sort_title": "Title",
            "sort_artist": "Artist",
            "sort_difficulty": "Difficulty",
            "sort_updated": "Last updated",
            "import_note": (
                "Downloading saves .osz in Downloads/osu-finder and opens it via the system file association.\n\n"
                ".zip → .osz without recompression. .7z and .rar require appropriate libraries."
            ),
            "theme_info": "Theme is saved locally • wallpaper is copied to the app profile",
            "result_searching": "Searching…",
            "result_count": "{count} results",
            "page_label": "Page {page}",
            "prev_button": "‹ Previous",
            "next_button": "Next ›",
            "error_connection": "Connection error: {error}",
            "error_generic": "Error: {error}",
            "error_search_title": "Failed to search beatmaps",
            "error_search_text": "{error}",
            "card_loading_cover": "Loading cover…",
            "card_unknown_title": "Untitled",
            "card_unknown_artist": "Unknown artist",
            "status_approved": "Approved",
            "details_title": "{title} — osu!finder",
            "details_creator": "👤 {creator}",
            "details_last_update": "📅 {date}",
            "details_video": "🎬 Video",
            "details_no_video": "No video",
            "details_download": "Download .osz",
            "details_download_no_video": "No video",
            "details_open_osu": "Open on osu!",
            "details_close": "Close",
            "details_downloading": "Downloading…",
            "details_download_success_title": "Done",
            "details_download_success_text": "Downloaded and opened file:\n{path}\n\nIf osu! did not start importing, drag the file into osu! or open it manually.",
            "details_download_error_title": "Download error",
            "details_download_error_text": "{error}",
            "details_ar": "AR",
            "details_cs": "CS",
            "details_od": "OD",
            "details_hp": "HP",
            "details_combo": "Combo",
            "theme_dialog_title": "Appearance — osu!finder",
            "theme_background": "Background",
            "theme_surface": "Surface",
            "theme_panel": "Panel / fields",
            "theme_text": "Text",
            "theme_muted": "Secondary text",
            "theme_border": "Borders",
            "theme_accent": "Accent color",
            "theme_image_path": "Background image",
            "theme_image_placeholder": "JPG / JPEG / PNG / WEBP / BMP / GIF — e.g. 1920×1020",
            "theme_image_select": "Choose…",
            "theme_image_opacity": "Image visibility",
            "theme_info_text": (
                "Wallpaper is copied to the app folder so it won't disappear if the original file is moved. "
                "You can use JPG, JPEG, PNG, WEBP, BMP or GIF; any aspect ratio is fine."
            ),
            "theme_export": "Export theme…",
            "theme_import": "Import theme…",
            "theme_reset": "Restore default",
            "theme_save_title": "Theme saved",
            "theme_save_text": "Theme saved:\n{path}",
            "theme_import_title": "Load theme",
            "theme_import_error_title": "Invalid theme",
            "theme_import_error_text": "{error}",
            "theme_background_error_title": "Invalid image",
            "theme_background_error_text": "{error}",
            "language_label": "LANGUAGE",
            "language_pl": "Polski",
            "language_en": "English",
            "language_de": "Deutsch",
            "language_ru": "Русский",
            "import_local_title": "Import beatmap",
            "import_local_filter": "osu! / archives (*.osz *.zip *.7z *.rar)",
            "import_local_success_title": "Import ready",
            "import_local_success_text": "Ready:\n{path}\n\nThe file was opened using the system osu! association.",
            "import_local_error_title": "Failed to import file",
            "import_local_error_text": "{error}",
            "error_invalid_zip": "ZIP does not contain .osu file — this does not look like an osu! beatmap.",
            "error_7z_missing": "For .7z install py7zr: pip install py7zr",
            "error_rar_missing": "For .rar install rarfile: pip install rarfile",
            "error_unsupported_format": "Unsupported format. Choose .osz, .zip, .7z or .rar.",
            "error_no_osu_files": "Archive does not contain .osu files — this does not look like an osu! beatmap.",
            "error_file_not_found": "File not found: {path}",
            "error_invalid_image": "Supported images: JPG, JPEG, PNG, WEBP, BMP, GIF.",
            "status_unknown": "Unknown",
            "file_filter_images": "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
            "file_filter_theme_json": "Theme JSON (*.json)",
            "error_theme_json_object": "The theme file must contain a JSON object.",
            "error_invalid_v2_response": "Invalid v2 response: missing results list",
            "error_invalid_api_response": "The API returned an invalid data format",
        }

        # German
        self.translations["de"] = {
            "app_name": "osu!finder",
            "search_placeholder": "Beatmap, Künstler oder Mapper suchen…",
            "search_button": "Suchen",
            "import_button": "Importieren",
            "theme_button": "Design",
            "mode_label": "SPIELMODUS",
            "mode_all": "Alle",
            "mode_osu": "osu!",
            "mode_taiko": "Taiko",
            "mode_catch": "Catch",
            "mode_mania": "Mania",
            "status_label": "STATUS",
            "status_all": "Alle",
            "status_ranked": "Ranked",
            "status_loved": "Loved",
            "status_qualified": "Qualified",
            "status_pending": "Pending",
            "status_graveyard": "Graveyard",
            "stars_label": "STERNENWERTUNG",
            "stars_min": "Min",
            "stars_max": "Max",
            "sort_label": "SORTIERUNG",
            "sort_relevance": "Relevanz",
            "sort_title": "Titel",
            "sort_artist": "Künstler",
            "sort_difficulty": "Schwierigkeit",
            "sort_updated": "Zuletzt aktualisiert",
            "import_note": (
                "Beim Herunterladen wird .osz im Ordner Downloads/osu-finder gespeichert und über die Systemdateizuordnung geöffnet.\n\n"
                ".zip → .osz ohne erneute Komprimierung. .7z und .rar erfordern entsprechende Bibliotheken."
            ),
            "theme_info": "Design wird lokal gespeichert • Hintergrundbild wird ins App‑Profil kopiert",
            "result_searching": "Suche läuft…",
            "result_count": "{count} Ergebnisse",
            "page_label": "Seite {page}",
            "prev_button": "‹ Zurück",
            "next_button": "Weiter ›",
            "error_connection": "Verbindungsfehler: {error}",
            "error_generic": "Fehler: {error}",
            "error_search_title": "Beatmaps konnten nicht gesucht werden",
            "error_search_text": "{error}",
            "card_loading_cover": "Cover wird geladen…",
            "card_unknown_title": "Ohne Titel",
            "card_unknown_artist": "Unbekannter Künstler",
            "status_approved": "Approved",
            "details_title": "{title} — osu!finder",
            "details_creator": "👤 {creator}",
            "details_last_update": "📅 {date}",
            "details_video": "🎬 Video",
            "details_no_video": "Kein Video",
            "details_download": ".osz herunterladen",
            "details_download_no_video": "Ohne Video",
            "details_open_osu": "Auf osu! öffnen",
            "details_close": "Schließen",
            "details_downloading": "Wird heruntergeladen…",
            "details_download_success_title": "Fertig",
            "details_download_success_text": "Datei heruntergeladen und geöffnet:\n{path}\n\nFalls osu! den Import nicht gestartet hat, ziehe die Datei in osu! oder öffne sie manuell.",
            "details_download_error_title": "Downloadfehler",
            "details_download_error_text": "{error}",
            "details_ar": "AR",
            "details_cs": "CS",
            "details_od": "OD",
            "details_hp": "HP",
            "details_combo": "Combo",
            "theme_dialog_title": "Erscheinungsbild — osu!finder",
            "theme_background": "Hintergrund",
            "theme_surface": "Oberfläche",
            "theme_panel": "Panel / Felder",
            "theme_text": "Text",
            "theme_muted": "Sekundärtext",
            "theme_border": "Rahmen",
            "theme_accent": "Akzentfarbe",
            "theme_image_path": "Hintergrundbild",
            "theme_image_placeholder": "JPG / JPEG / PNG / WEBP / BMP / GIF — z. B. 1920×1020",
            "theme_image_select": "Auswählen…",
            "theme_image_opacity": "Bildsichtbarkeit",
            "theme_info_text": (
                "Das Hintergrundbild wird in den App‑Ordner kopiert, sodass es nicht verschwindet, wenn die Originaldatei verschoben wird. "
                "Du kannst JPG, JPEG, PNG, WEBP, BMP oder GIF verwenden; jedes Seitenverhältnis ist möglich."
            ),
            "theme_export": "Design exportieren…",
            "theme_import": "Design importieren…",
            "theme_reset": "Standard wiederherstellen",
            "theme_save_title": "Design gespeichert",
            "theme_save_text": "Design gespeichert:\n{path}",
            "theme_import_title": "Design laden",
            "theme_import_error_title": "Ungültiges Design",
            "theme_import_error_text": "{error}",
            "theme_background_error_title": "Ungültiges Bild",
            "theme_background_error_text": "{error}",
            "language_label": "SPRACHE",
            "language_pl": "Polski",
            "language_en": "English",
            "language_de": "Deutsch",
            "language_ru": "Русский",
            "import_local_title": "Beatmap importieren",
            "import_local_filter": "osu! / Archive (*.osz *.zip *.7z *.rar)",
            "import_local_success_title": "Import bereit",
            "import_local_success_text": "Bereit:\n{path}\n\nDie Datei wurde über die Systemzuordnung von osu! geöffnet.",
            "import_local_error_title": "Datei konnte nicht importiert werden",
            "import_local_error_text": "{error}",
            "error_invalid_zip": "ZIP enthält keine .osu‑Datei — dies sieht nicht wie eine osu!-Beatmap aus.",
            "error_7z_missing": "Für .7z installiere py7zr: pip install py7zr",
            "error_rar_missing": "Für .rar installiere rarfile: pip install rarfile",
            "error_unsupported_format": "Nicht unterstütztes Format. Wähle .osz, .zip, .7z oder .rar.",
            "error_no_osu_files": "Archiv enthält keine .osu‑Dateien — dies sieht nicht wie eine osu!-Beatmap aus.",
            "error_file_not_found": "Datei nicht gefunden: {path}",
            "error_invalid_image": "Unterstützte Bilder: JPG, JPEG, PNG, WEBP, BMP, GIF.",
            "status_unknown": "Unbekannt",
            "file_filter_images": "Bilder (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
            "file_filter_theme_json": "Design JSON (*.json)",
            "error_theme_json_object": "Die Design-Datei muss ein JSON-Objekt enthalten.",
            "error_invalid_v2_response": "Ungültige v2-Antwort: Ergebnisliste fehlt",
            "error_invalid_api_response": "Die API hat ein ungültiges Datenformat zurückgegeben",
        }

        # Russian
        self.translations["ru"] = {
            "app_name": "osu!finder",
            "search_placeholder": "Поиск карты, исполнителя или маппера…",
            "search_button": "Искать",
            "import_button": "Импорт",
            "theme_button": "Тема",
            "mode_label": "РЕЖИМ ИГРЫ",
            "mode_all": "Все",
            "mode_osu": "osu!",
            "mode_taiko": "Taiko",
            "mode_catch": "Catch",
            "mode_mania": "Mania",
            "status_label": "СТАТУС",
            "status_all": "Все",
            "status_ranked": "Ranked",
            "status_loved": "Loved",
            "status_qualified": "Qualified",
            "status_pending": "Pending",
            "status_graveyard": "Graveyard",
            "stars_label": "ЗВЁЗДЫ",
            "stars_min": "Мин",
            "stars_max": "Макс",
            "sort_label": "СОРТИРОВКА",
            "sort_relevance": "Релевантность",
            "sort_title": "Название",
            "sort_artist": "Исполнитель",
            "sort_difficulty": "Сложность",
            "sort_updated": "Последнее обновление",
            "import_note": (
                "При скачивании .osz сохраняется в Downloads/osu-finder и открывается через системную ассоциацию файлов.\n\n"
                ".zip → .osz без повторной компрессии. .7z и .rar требуют соответствующих библиотек."
            ),
            "theme_info": "Тема сохраняется локально • обои копируются в профиль приложения",
            "result_searching": "Поиск…",
            "result_count": "{count} результатов",
            "page_label": "Страница {page}",
            "prev_button": "‹ Предыдущая",
            "next_button": "Следующая ›",
            "error_connection": "Ошибка соединения: {error}",
            "error_generic": "Ошибка: {error}",
            "error_search_title": "Не удалось выполнить поиск",
            "error_search_text": "{error}",
            "card_loading_cover": "Загрузка обложки…",
            "card_unknown_title": "Без названия",
            "card_unknown_artist": "Неизвестный исполнитель",
            "status_approved": "Approved",
            "details_title": "{title} — osu!finder",
            "details_creator": "👤 {creator}",
            "details_last_update": "📅 {date}",
            "details_video": "🎬 Видео",
            "details_no_video": "Без видео",
            "details_download": "Скачать .osz",
            "details_download_no_video": "Без видео",
            "details_open_osu": "Открыть на osu!",
            "details_close": "Закрыть",
            "details_downloading": "Скачивание…",
            "details_download_success_title": "Готово",
            "details_download_success_text": "Файл скачан и открыт:\n{path}\n\nЕсли osu! не начал импорт, перетащите файл в osu! или откройте вручную.",
            "details_download_error_title": "Ошибка скачивания",
            "details_download_error_text": "{error}",
            "details_ar": "AR",
            "details_cs": "CS",
            "details_od": "OD",
            "details_hp": "HP",
            "details_combo": "Комбо",
            "theme_dialog_title": "Внешний вид — osu!finder",
            "theme_background": "Фон",
            "theme_surface": "Поверхность",
            "theme_panel": "Панель / поля",
            "theme_text": "Текст",
            "theme_muted": "Вторичный текст",
            "theme_border": "Рамки",
            "theme_accent": "Акцентный цвет",
            "theme_image_path": "Фоновое изображение",
            "theme_image_placeholder": "JPG / JPEG / PNG / WEBP / BMP / GIF — напр. 1920×1020",
            "theme_image_select": "Выбрать…",
            "theme_image_opacity": "Видимость изображения",
            "theme_info_text": (
                "Обои копируются в папку приложения, поэтому не исчезнут при перемещении исходного файла. "
                "Можно использовать JPG, JPEG, PNG, WEBP, BMP или GIF; пропорции любые."
            ),
            "theme_export": "Экспорт темы…",
            "theme_import": "Импорт темы…",
            "theme_reset": "Восстановить по умолчанию",
            "theme_save_title": "Тема сохранена",
            "theme_save_text": "Тема сохранена:\n{path}",
            "theme_import_title": "Загрузить тему",
            "theme_import_error_title": "Неверная тема",
            "theme_import_error_text": "{error}",
            "theme_background_error_title": "Неверное изображение",
            "theme_background_error_text": "{error}",
            "language_label": "ЯЗЫК",
            "language_pl": "Polski",
            "language_en": "English",
            "language_de": "Deutsch",
            "language_ru": "Русский",
            "import_local_title": "Импорт карты",
            "import_local_filter": "osu! / архивы (*.osz *.zip *.7z *.rar)",
            "import_local_success_title": "Импорт готов",
            "import_local_success_text": "Готово:\n{path}\n\nФайл открыт через системную ассоциацию osu!.",
            "import_local_error_title": "Не удалось импортировать файл",
            "import_local_error_text": "{error}",
            "error_invalid_zip": "ZIP не содержит .osu файла — это не похоже на карту osu!.",
            "error_7z_missing": "Для .7z установите py7zr: pip install py7zr",
            "error_rar_missing": "Для .rar установите rarfile: pip install rarfile",
            "error_unsupported_format": "Неподдерживаемый формат. Выберите .osz, .zip, .7z или .rar.",
            "error_no_osu_files": "Архив не содержит .osu файлов — это не похоже на карту osu!.",
            "error_file_not_found": "Файл не найден: {path}",
            "error_invalid_image": "Поддерживаемые изображения: JPG, JPEG, PNG, WEBP, BMP, GIF.",
            "status_unknown": "Неизвестно",
            "file_filter_images": "Изображения (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
            "file_filter_theme_json": "Тема JSON (*.json)",
            "error_theme_json_object": "Файл темы должен содержать объект JSON.",
            "error_invalid_v2_response": "Некорректный ответ v2: отсутствует список результатов",
            "error_invalid_api_response": "API вернул некорректный формат данных",
        }


# Global translator instance
i18n = I18n()


def _tr(key: str, **kwargs) -> str:
    """Shortcut for i18n.tr."""
    return i18n.tr(key, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
#  Theme classes (unchanged except for translated strings)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SearchFilters:
    query: str = ""
    mode: int = -1
    status: object = 1
    page: int = 0
    min_stars: float = 0.0
    max_stars: float = 10.0
    sort: str = "relevance"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return (32, 36, 43)
    try:
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    except ValueError:
        return (32, 36, 43)


def rgba(value: str, alpha: int) -> str:
    r, g, b = hex_to_rgb(value)
    return f"rgba({r}, {g}, {b}, {max(0, min(255, int(alpha)))})"


class ThemeManager:
    def __init__(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.data = dict(DEFAULT_THEME)
        self.load()

    def load(self) -> None:
        try:
            if SETTINGS_PATH.exists():
                saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    self.data.update(saved)
        except Exception:
            self.data = dict(DEFAULT_THEME)

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def reset(self) -> None:
        self.data = dict(DEFAULT_THEME)
        self.save()

    def css(self) -> str:
        t = self.data
        surface = rgba(t['surface'], 232)
        panel = rgba(t['panel'], 238)
        hover = rgba(t['panel_hover'], 245)
        return f"""
        QWidget {{
            color: {t['text']};
            font-family: "Inter", "Segoe UI", "Cantarell", "Noto Sans", "Ubuntu", "Helvetica Neue", Arial, sans-serif;
            font-size: 13px;
        }}
        QMainWindow, QDialog {{ background: transparent; }}
        QFrame#Toolbar {{
            background: {surface};
            border: 1px solid {t['border']};
            border-radius: 5px;
        }}
        QFrame#Sidebar {{
            background: {surface};
            border-right: 1px solid {t['border']};
            border-radius: 5px;
        }}
        QFrame#ResultsBar {{
            background: {surface};
            border: 1px solid {t['border']};
            border-radius: 5px;
        }}
        QFrame#Card {{
            background: {surface};
            border: 1px solid {t['border']};
            border-radius: 5px;
        }}
        QFrame#Card:hover {{
            background: {hover};
            border-color: {t['accent']};
        }}
        QFrame#ModalFrame {{
            background: {surface};
            border: 1px solid {t['border']};
            border-radius: 5px;
        }}
        QLineEdit, QComboBox, QSpinBox {{
            background: {panel};
            color: {t['text']};
            border: 1px solid {t['border']};
            border-radius: 4px;
            padding: 6px 8px;
            selection-background-color: {t['accent']};
            selection-color: {t['accent_text']};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {t['accent']}; }}
        QComboBox QAbstractItemView {{
            background: {t['panel']}; color: {t['text']};
            border: 1px solid {t['border']};
            selection-background-color: {t['accent']};
        }}
        QPushButton, QToolButton {{
            background: {panel};
            color: {t['text']};
            border: 1px solid {t['border']};
            border-radius: 4px;
            padding: 6px 10px;
        }}
        QPushButton:hover, QToolButton:hover {{ background: {hover}; border-color: {t['accent']}; }}
        QPushButton:pressed, QToolButton:pressed {{ background: {t['accent']}; color: {t['accent_text']}; }}
        QPushButton#accentButton {{ background: {t['accent']}; color: {t['accent_text']}; border-color: {t['accent']}; font-weight: 600; }}
        QPushButton:disabled {{ color: {t['muted']}; border-color: {t['border']}; }}
        QGroupBox {{ border: none; margin-top: 0; padding-top: 0; font-weight: 600; }}
        QGroupBox::title {{ color: {t['muted']}; }}
        QSlider::groove:horizontal {{ height: 4px; background: {t['border']}; border-radius: 2px; }}
        QSlider::handle:horizontal {{ width: 12px; margin: -4px 0; background: {t['accent']}; border-radius: 6px; }}
        QProgressBar {{ border: 1px solid {t['border']}; border-radius: 3px; background: {panel}; text-align: center; }}
        QProgressBar::chunk {{ background: {t['accent']}; border-radius: 2px; }}
        QScrollArea {{ border: none; background: transparent; }}
        QSplitter {{ background: transparent; }}
        QSplitter::handle {{ background: transparent; }}
        #ContentArea, #ResultsGrid, #ScrollViewport {{ background: transparent; }}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 4px; min-height: 30px; }}
        QScrollBar::handle:vertical:hover {{ background: {t['accent']}; }}
        QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {t['border']}; border-radius: 2px; background: {panel}; }}
        QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; }}
        """


class BackgroundWidget(QWidget):
    def __init__(self, theme: ThemeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.pixmap: Optional[QPixmap] = None
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.reload_image()

    def reload_image(self) -> None:
        path = str(self.theme.data.get("background_image", "")).strip()
        self.pixmap = None
        if path:
            candidate = Path(path).expanduser()
            if candidate.exists() and candidate.is_file():
                pm = QPixmap()
                if pm.load(str(candidate)) and not pm.isNull():
                    self.pixmap = pm
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.fillRect(self.rect(), QColor(self.theme.data["background"]))
        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            opacity = max(0, min(100, int(self.theme.data.get("image_opacity", 42)))) / 100.0
            p.setOpacity(opacity)
            p.drawPixmap(x, y, scaled)
            p.setOpacity(1.0)
            overlay = max(0, min(255, int(self.theme.data.get("image_overlay", 10))))
            if overlay:
                p.fillRect(self.rect(), QColor(0, 0, 0, overlay))
        p.end()


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class SearchWorker(QRunnable):
    def __init__(self, filters: SearchFilters, generation: int) -> None:
        super().__init__()
        self.filters = filters
        self.generation = generation
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            f = self.filters
            if f.status == "graveyard":
                params: dict[str, object] = {
                    "query": f.query,
                    "status": "graveyard",
                    "limit": 100,
                    "page": f.page,
                }
                if f.mode >= 0:
                    params["mode"] = f.mode
                if f.min_stars > 0:
                    params["min_stars"] = f.min_stars
                if f.max_stars < 10:
                    params["max_stars"] = f.max_stars
                r = requests.get(
                    "https://mirror.hinamizawa.ai/v3/osu/beatmaps/search/v2",
                    params=params, headers={"User-Agent": USER_AGENT}, timeout=(7, 25)
                )
                r.raise_for_status()
                payload = r.json()
                data = normalize_v2_results(payload)
            else:
                params = {
                    "query": f.query,
                    "mode": f.mode,
                    "amount": 100,
                    "offset": f.page * 100,
                }
                if f.status is not None:
                    params["status"] = f.status
                if f.min_stars > 0:
                    params["min_stars"] = f.min_stars
                if f.max_stars < 10:
                    params["max_stars"] = f.max_stars
                if f.sort == "title":
                    params["sort"] = "title_asc"
                elif f.sort == "difficulty":
                    pass
                r = requests.get(
                    f"{API_BASE}/search",
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=(7, 25),
                )
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, list):
                    raise ValueError(_tr("error_invalid_api_response"))

            data = sort_results(data, f.sort)
            self.signals.finished.emit((self.generation, data))
        except requests.RequestException as exc:
            self.signals.error.emit(_tr("error_connection", error=str(exc)))
        except Exception as exc:
            self.signals.error.emit(str(exc))


class DownloadSignals(QObject):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)


class DownloadWorker(QRunnable):
    def __init__(self, url: str, target: Path) -> None:
        super().__init__()
        self.url = url
        self.target = target
        self.signals = DownloadSignals()

    @Slot()
    def run(self) -> None:
        temp_target = self.target.with_suffix(self.target.suffix + ".part")
        try:
            self.target.parent.mkdir(parents=True, exist_ok=True)
            with requests.get(
                self.url,
                headers={"User-Agent": USER_AGENT},
                timeout=(10, 90),
                stream=True,
            ) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length") or 0)
                received = 0
                with open(temp_target, "wb") as f:
                    for chunk in r.iter_content(chunk_size=256 * 1024):
                        if not chunk:
                            continue
                        f.write(chunk)
                        received += len(chunk)
                        if total:
                            self.signals.progress.emit(min(100, int(received * 100 / total)))
                if total:
                    self.signals.progress.emit(100)
            os.replace(temp_target, self.target)
            self.signals.finished.emit(str(self.target))
        except Exception as exc:
            try:
                temp_target.unlink(missing_ok=True)
            except Exception:
                pass
            self.signals.error.emit(str(exc))


class CoverSignals(QObject):
    loaded = Signal(str, object)


class CoverWorker(QRunnable):
    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self.signals = CoverSignals()

    @Slot()
    def run(self) -> None:
        try:
            r = requests.get(self.url, timeout=12, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            image = QImage()
            image.loadFromData(r.content)
            if not image.isNull():
                self.signals.loaded.emit(self.url, image)
        except Exception:
            pass


def normalize_v2_results(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("beatmapsets") or payload.get("results") or payload.get("items") or payload.get("data") or []
    else:
        rows = []
    if not isinstance(rows, list):
        raise ValueError(_tr("error_invalid_v2_response"))

    status_map = {"ranked": 1, "approved": 2, "qualified": 3, "loved": 4, "pending": 0, "graveyard": -2}
    normalized: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        set_id = item.get("SetID") or item.get("setId") or item.get("beatmapset_id") or item.get("id")
        beatmaps = item.get("ChildrenBeatmaps") or item.get("beatmaps") or item.get("difficulties") or []
        children: list[dict[str, Any]] = []
        if isinstance(beatmaps, list):
            for d in beatmaps:
                if not isinstance(d, dict):
                    continue
                mode_value = d.get("Mode", d.get("mode_int", d.get("mode", 0)))
                child = {
                    "BeatmapID": d.get("BeatmapID") or d.get("id") or d.get("beatmap_id"),
                    "DiffName": d.get("DiffName") or d.get("version") or d.get("difficulty_name") or "?",
                    "DifficultyRating": d.get("DifficultyRating", d.get("difficulty_rating", d.get("stars", 0))) or 0,
                    "AR": d.get("AR", d.get("ar", "?")),
                    "CS": d.get("CS", d.get("cs", "?")),
                    "OD": d.get("OD", d.get("od", "?")),
                    "HP": d.get("HP", d.get("hp", "?")),
                    "Mode": mode_value,
                    "MaxCombo": d.get("MaxCombo", d.get("max_combo", "?")),
                    "ParentSetID": set_id,
                    "TotalLength": d.get("TotalLength", d.get("total_length", 0)),
                    "HitLength": d.get("HitLength", d.get("hit_length", 0)),
                    "FileMD5": d.get("FileMD5", d.get("checksum", "")),
                }
                try:
                    child["Mode"] = int(child["Mode"])
                except Exception:
                    child["Mode"] = 0
                try:
                    child["DifficultyRating"] = float(child["DifficultyRating"])
                except Exception:
                    child["DifficultyRating"] = 0.0
                children.append(child)
        status_raw = item.get("RankedStatus", item.get("status", -2))
        if isinstance(status_raw, str):
            status_value = status_map.get(status_raw.lower(), -2)
        else:
            try:
                status_value = int(status_raw)
            except Exception:
                status_value = -2
        normalized.append({
            "SetID": set_id,
            "Artist": item.get("Artist", item.get("artist", "Unknown artist")),
            "Title": item.get("Title", item.get("title", "Untitled")),
            "Creator": item.get("Creator", item.get("creator", "?")),
            "RankedStatus": status_value,
            "LastUpdate": item.get("LastUpdate", item.get("lastUpdate", item.get("last_updated", "?"))),
            "HasVideo": int(bool(item.get("HasVideo", item.get("hasVideo", False)))),
            "ChildrenBeatmaps": children,
        })
    return normalized


def sort_results(data: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    copy = list(data)
    if sort == "title":
        return sorted(copy, key=lambda a: str(a.get("Title", "")).casefold())
    if sort == "artist":
        return sorted(copy, key=lambda a: str(a.get("Artist", "")).casefold())
    if sort == "difficulty":
        return sorted(copy, key=lambda a: max([float(d.get("DifficultyRating", 0)) for d in (a.get("ChildrenBeatmaps") or [])] or [0]), reverse=True)
    if sort == "updated":
        def key(a: dict[str, Any]) -> str:
            return str(a.get("LastUpdate", ""))
        return sorted(copy, key=key, reverse=True)
    return copy


def get_diff_class(stars: float) -> str:
    if stars < 2:
        return "easy"
    if stars < 2.7:
        return "normal"
    if stars < 4:
        return "hard"
    if stars < 5.3:
        return "insane"
    if stars < 6.5:
        return "expert"
    return "extreme"


def escape_filename(value: str, max_len: int = 80) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip().rstrip(".")
    return value[:max_len] or "beatmap"


def rounded_top_pixmap(pix: QPixmap, radius: int) -> QPixmap:
    if pix.isNull():
        return pix
    result = QPixmap(pix.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    rect = result.rect()
    path.moveTo(rect.left(), rect.bottom())
    path.lineTo(rect.left(), rect.top() + radius)
    path.quadTo(rect.left(), rect.top(), rect.left() + radius, rect.top())
    path.lineTo(rect.right() - radius, rect.top())
    path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + radius)
    path.lineTo(rect.right(), rect.bottom())
    path.closeSubpath()
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pix)
    painter.end()
    return result


def app_font(size: int, weight: QFont.Weight = QFont.Normal) -> QFont:
    font = QFont()
    font.setFamilies(["Inter", "Segoe UI", "Cantarell", "Noto Sans", "Ubuntu", "Helvetica Neue", "Arial"])
    font.setPointSize(size)
    font.setWeight(weight)
    return font


def install_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class ColorButton(QPushButton):
    changed = Signal(str)

    def __init__(self, color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.color = color
        self.setFixedHeight(34)
        self.clicked.connect(self.pick)
        self.update_text()

    def update_text(self) -> None:
        self.setText(self.color)
        self.setStyleSheet(
            f"QPushButton{{background:{self.color}; color:{'#000' if QColor(self.color).lightnessF() > 0.65 else '#fff'}; border:1px solid rgba(255,255,255,0.18); border-radius:6px;}}"
        )

    def pick(self) -> None:
        color = QColorDialog.getColor(QColor(self.color), self, _tr("theme_accent"))
        if color.isValid():
            self.color = color.name().upper()
            self.update_text()
            self.changed.emit(self.color)


class ThemeDialog(QDialog):
    applied = Signal()

    def __init__(self, theme: ThemeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle(_tr("theme_dialog_title"))
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.colors: dict[str, ColorButton] = {}
        labels = [
            ("background", "theme_background"),
            ("surface", "theme_surface"),
            ("panel", "theme_panel"),
            ("text", "theme_text"),
            ("muted", "theme_muted"),
            ("border", "theme_border"),
            ("accent", "theme_accent"),
        ]
        for key, label_key in labels:
            btn = ColorButton(theme.data[key])
            self.colors[key] = btn
            form.addRow(_tr(label_key), btn)

        image_row = QHBoxLayout()
        self.image_path = QLineEdit(theme.data.get("background_image", ""))
        self.image_path.setPlaceholderText(_tr("theme_image_placeholder"))
        image_btn = QPushButton(_tr("theme_image_select"))
        image_btn.clicked.connect(self.select_image)
        image_row.addWidget(self.image_path, 1)
        image_row.addWidget(image_btn)
        form.addRow(_tr("theme_image_path"), image_row)

        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(int(theme.data.get("image_opacity", 42)))
        self.opacity_label = QLabel(f"{self.opacity.value()}%")
        self.opacity.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        op_row = QHBoxLayout()
        op_row.addWidget(self.opacity, 1)
        op_row.addWidget(self.opacity_label)
        form.addRow(_tr("theme_image_opacity"), op_row)

        layout.addLayout(form)
        info = QLabel(_tr("theme_info_text"))
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{theme.data['muted']}; padding:6px 0;")
        layout.addWidget(info)

        utility_row = QHBoxLayout()
        export_btn = QPushButton(_tr("theme_export"))
        import_btn = QPushButton(_tr("theme_import"))
        export_btn.clicked.connect(self.export_theme)
        import_btn.clicked.connect(self.import_theme)
        utility_row.addWidget(export_btn)
        utility_row.addWidget(import_btn)
        utility_row.addStretch(1)
        layout.addLayout(utility_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        reset = buttons.addButton(_tr("theme_reset"), QDialogButtonBox.ResetRole)
        reset.clicked.connect(self.reset_theme)
        buttons.accepted.connect(self.apply_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _store_background_image(self, path: str) -> str:
        src = Path(path).expanduser()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(_tr("error_file_not_found", path=src))
        if src.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
            raise ValueError(_tr("error_invalid_image"))
        folder = APP_DIR / "backgrounds"
        folder.mkdir(parents=True, exist_ok=True)
        safe = escape_filename(src.stem, 60) + src.suffix.lower()
        target = folder / safe
        if src.resolve() != target.resolve():
            shutil.copy2(src, target)
        return str(target)

    def select_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            _tr("theme_image_select"),
            "",
            _tr("file_filter_images")
        )
        if path:
            self.image_path.setText(path)

    def export_theme(self) -> None:
        self.apply_fields_to_memory(temporary=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            _tr("theme_export"),
            "osu-finder-theme.json",
            _tr("file_filter_theme_json")
        )
        if not path:
            return
        try:
            Path(path).write_text(
                json.dumps(self.theme.data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            QMessageBox.information(
                self,
                _tr("theme_save_title"),
                _tr("theme_save_text", path=path)
            )
        except Exception as exc:
            QMessageBox.critical(self, _tr("theme_import_error_title"), str(exc))

    def import_theme(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            _tr("theme_import"),
            "",
            _tr("file_filter_theme_json")
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(_tr("error_theme_json_object"))
            merged = dict(DEFAULT_THEME)
            for key in DEFAULT_THEME:
                if key in data:
                    merged[key] = data[key]
            image_path = str(merged.get("background_image", "") or "").strip()
            if image_path and not Path(image_path).is_absolute():
                image_path = str((Path(path).parent / image_path).resolve())
            merged["background_image"] = image_path
            self.theme.data = merged
            for key, btn in self.colors.items():
                btn.color = str(self.theme.data[key])
                btn.update_text()
            self.image_path.setText(str(self.theme.data.get("background_image", "")))
            self.opacity.setValue(int(self.theme.data.get("image_opacity", 18)))
        except Exception as exc:
            QMessageBox.critical(self, _tr("theme_import_error_title"), str(exc))

    def apply_fields_to_memory(self, temporary: bool = False) -> None:
        for key, btn in self.colors.items():
            self.theme.data[key] = btn.color
        self.theme.data["background_image"] = self.image_path.text().strip()
        self.theme.data["image_opacity"] = self.opacity.value()

    def reset_theme(self) -> None:
        self.theme.reset()
        self.theme.load()
        for key, btn in self.colors.items():
            btn.color = self.theme.data[key]
            btn.update_text()
        self.image_path.setText(self.theme.data.get("background_image", ""))
        self.opacity.setValue(int(self.theme.data.get("image_opacity", 18)))
        self.applied.emit()

    def apply_and_close(self) -> None:
        self.apply_fields_to_memory()
        image = self.theme.data["background_image"]
        if image:
            try:
                image = self._store_background_image(image)
            except Exception as exc:
                QMessageBox.warning(self, _tr("theme_background_error_title"), str(exc))
                return
        self.theme.data["background_image"] = image
        self.theme.data["image_opacity"] = self.opacity.value()
        self.theme.data["image_overlay"] = 8
        self.theme.save()
        self.applied.emit()
        self.accept()


class DifficultyPill(QLabel):
    def __init__(self, text: str, diff_class: str, theme: ThemeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        colors = {
            "easy": "#7cdb8c",
            "normal": "#78b9df",
            "hard": "#e4bd69",
            "insane": "#e88b8b",
            "expert": "#b88fe3",
            "extreme": theme.data["accent"],
        }
        c = colors[diff_class]
        self.setFont(app_font(10, QFont.DemiBold))
        self.setStyleSheet(f"QLabel{{color:{c}; background:transparent; border:none; padding:0 6px 0 0; font-weight:600;}}")


class BeatmapCard(QFrame):
    clicked = Signal(object)

    def __init__(self, set_data: dict[str, Any], theme: ThemeManager, pool: QThreadPool, cache: dict[str, QImage], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.data = set_data
        self.theme = theme
        self.cache = cache
        self.pool = pool
        self.cover_url = f"https://assets.ppy.sh/beatmaps/{set_data.get('SetID', '')}/covers/cover.jpg"
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(245)
        self.setMaximumWidth(390)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)
        self._fade_anim: Optional[QPropertyAnimation] = None
        self._cover_effect = QGraphicsOpacityEffect(self)
        self.cover_loaded_once = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.cover = QLabel()
        self.cover.setFixedHeight(125)
        self.cover.setAlignment(Qt.AlignCenter)
        self.cover.setStyleSheet(f"background:{theme.data['panel']}; border-top-left-radius:8px; border-top-right-radius:8px;")
        self.cover.setGraphicsEffect(self._cover_effect)
        self._cover_effect.setOpacity(0.0)
        outer.addWidget(self.cover)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 8, 10, 9)
        body_layout.setSpacing(4)
        title = QLabel(str(set_data.get("Title", _tr("card_unknown_title"))))
        title.setFont(app_font(10, QFont.Bold))
        title.setToolTip(title.text())
        title.setTextInteractionFlags(Qt.NoTextInteraction)
        artist = QLabel(str(set_data.get("Artist", _tr("card_unknown_artist"))))
        artist.setStyleSheet(f"color:{theme.data['muted']};")
        creator = QLabel(f"👤 {set_data.get('Creator', '?')}")
        creator.setStyleSheet(f"color:{theme.data['muted']}; font-size:11px;")

        row = QHBoxLayout()
        row.addWidget(creator)
        row.addStretch(1)
        status_name, status_class = STATUS_MAP.get(int(set_data.get("RankedStatus", 0)), (_tr("status_unknown"), "pending"))
        status_name = _tr(f"status_{status_class}") if status_class in ["ranked", "loved", "qualified", "pending", "graveyard"] else _tr("status_unknown")
        status = QLabel(status_name)
        status_color = {
            "ranked": theme.data["success"],
            "loved": theme.data["accent"],
            "qualified": theme.data["warning"],
            "pending": theme.data["muted"],
            "graveyard": "#7d838d",
        }.get(status_class, theme.data["muted"])
        status.setStyleSheet(f"QLabel{{color:{status_color}; background:{status_color}18; border:1px solid {status_color}35; border-radius:5px; padding:2px 7px; font-size:10px; font-weight:700;}}")
        row.addWidget(status)

        diffs = set_data.get("ChildrenBeatmaps") or []
        diff_row = QHBoxLayout()
        diff_row.setSpacing(4)
        for d in diffs[:5]:
            stars = float(d.get("DifficultyRating", 0))
            diff_row.addWidget(DifficultyPill(f"★{stars:.2f}", get_diff_class(stars), theme))
        if len(diffs) > 5:
            more = QLabel(f"+{len(diffs)-5}")
            more.setStyleSheet(f"color:{theme.data['muted']}; background:{theme.data['panel']}; border:1px solid {theme.data['border']}; padding:3px 7px; border-radius:10px;")
            diff_row.addWidget(more)
        diff_row.addStretch(1)

        body_layout.addWidget(title)
        body_layout.addWidget(artist)
        body_layout.addLayout(row)
        body_layout.addLayout(diff_row)
        outer.addWidget(body)

        if self.cover_url in cache:
            self.set_cover(cache[self.cover_url])
        else:
            self.cover.setText(_tr("card_loading_cover"))
            worker = CoverWorker(self.cover_url)
            worker.signals.loaded.connect(self.cover_loaded)
            pool.start(worker)

    @Slot(str, object)
    def cover_loaded(self, url: str, image: object) -> None:
        if url != self.cover_url or not isinstance(image, QImage):
            return
        self.cache[url] = image
        self.set_cover(image)

    def set_cover(self, image: QImage) -> None:
        pix = QPixmap.fromImage(image).scaled(self.cover.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (pix.width() - self.cover.width()) // 2)
        y = max(0, (pix.height() - self.cover.height()) // 2)
        cropped = pix.copy(x, y, self.cover.width(), self.cover.height())
        self.cover.setPixmap(rounded_top_pixmap(cropped, 8))
        if not self.cover_loaded_once:
            self.cover_loaded_once = True
            anim = QPropertyAnimation(self._cover_effect, b"opacity", self)
            anim.setDuration(260)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(self._detach_cover_effect)
            self._cover_anim = anim
            anim.start()

    def _detach_cover_effect(self) -> None:
        try:
            self.cover.setGraphicsEffect(None)
        except RuntimeError:
            pass
        self._cover_effect = None
        self._cover_anim = None

    def animate_in(self, delay_ms: int = 0) -> None:
        def start() -> None:
            try:
                if self._fade_anim:
                    self._fade_anim.stop()
                anim = QPropertyAnimation(self._opacity_effect, b"opacity", self)
                anim.setDuration(320)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.finished.connect(self._detach_card_effect)
                self._fade_anim = anim
                anim.start()
            except RuntimeError:
                pass
        QTimer.singleShot(delay_ms, start)

    def _detach_card_effect(self) -> None:
        try:
            self.setGraphicsEffect(None)
        except RuntimeError:
            pass
        self._opacity_effect = None
        self._fade_anim = None

    def stop_animations(self) -> None:
        for anim_attr in ("_fade_anim", "_cover_anim"):
            anim = getattr(self, anim_attr, None)
            if anim is not None:
                try:
                    anim.stop()
                except RuntimeError:
                    pass
        if self._opacity_effect is not None:
            try:
                self._opacity_effect.setOpacity(1.0)
            except RuntimeError:
                pass

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(event)


class ResultsGrid(QWidget):
    card_clicked = Signal(object)

    def __init__(self, theme: ThemeManager, pool: QThreadPool, cache: dict[str, QImage], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.pool = pool
        self.cache = cache
        self.cards: list[BeatmapCard] = []
        self.layout_grid = QGridLayout(self)
        self.layout_grid.setContentsMargins(1, 1, 1, 12)
        self.layout_grid.setSpacing(9)
        self.layout_grid.setAlignment(Qt.AlignTop)
        self.data: list[dict[str, Any]] = []
        self._columns = 0
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(120)
        self._resize_timer.timeout.connect(self.reflow)

    def _columns_for_width(self, width: int) -> int:
        return 1 if width < 650 else 2 if width < 980 else 3

    def set_data(self, data: list[dict[str, Any]]) -> None:
        self.data = data
        self._teardown_cards()
        cols = self._columns_for_width(self.width())
        self._columns = cols
        for i, item in enumerate(self.data):
            card = BeatmapCard(item, self.theme, self.pool, self.cache)
            card.clicked.connect(self.card_clicked)
            self.cards.append(card)
            self.layout_grid.addWidget(card, i // cols, i % cols)
            card.animate_in(min(i, 12) * 28)
        for c in range(cols):
            self.layout_grid.setColumnStretch(c, 1)

    def _teardown_cards(self) -> None:
        for card in self.cards:
            card.stop_animations()
            card.deleteLater()
        self.cards.clear()
        while self.layout_grid.count():
            item = self.layout_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def rebuild(self) -> None:
        self.set_data(self.data)

    def reflow(self) -> None:
        cols = self._columns_for_width(self.width())
        if cols == self._columns or not self.cards:
            self._columns = cols
            return
        self._columns = cols
        while self.layout_grid.count():
            self.layout_grid.takeAt(0)
        for i, card in enumerate(self.cards):
            self.layout_grid.addWidget(card, i // cols, i % cols)
        for c in range(cols):
            self.layout_grid.setColumnStretch(c, 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.data:
            cols = self._columns_for_width(max(1, self.width()))
            if cols != self._columns:
                self._resize_timer.start()


class DetailsDialog(QDialog):
    def __init__(self, set_data: dict[str, Any], theme: ThemeManager, pool: QThreadPool, cache: dict[str, QImage], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.set_data = set_data
        self.theme = theme
        self.pool = pool
        self.cache = cache
        self.setWindowTitle(_tr("details_title", title=set_data.get('Title', _tr("card_unknown_title"))))
        self.resize(760, 610)
        self.download_button: Optional[QPushButton] = None
        self.no_video_button: Optional[QPushButton] = None
        self.progress = QProgressBar()
        self.progress.setVisible(False)

        root = QVBoxLayout(self)
        frame = QFrame()
        frame.setObjectName("ModalFrame")
        self._modal_frame = frame
        self._dialog_opacity = QGraphicsOpacityEffect(frame)
        self._dialog_opacity.setOpacity(0.0)
        frame.setGraphicsEffect(self._dialog_opacity)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)
        header = QLabel()
        header.setFixedHeight(210)
        header.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        header.setStyleSheet(f"padding:20px; background:{theme.data['surface']};")
        cover_url = f"https://assets.ppy.sh/beatmaps/{set_data.get('SetID', '')}/covers/cover.jpg"
        if cover_url in cache:
            self._set_header_image(header, cache[cover_url])
        else:
            worker = CoverWorker(cover_url)
            worker.signals.loaded.connect(lambda url, image: self._header_loaded(url, image, cover_url, header))
            pool.start(worker)
        title = QLabel(str(set_data.get("Title", _tr("card_unknown_title"))))
        title.setFont(app_font(17, QFont.Bold))
        title.setStyleSheet("background:transparent; color:white;")
        artist = QLabel(str(set_data.get("Artist", _tr("card_unknown_artist"))))
        artist.setStyleSheet("background:transparent; color:#e8e8e8;")
        overlay = QVBoxLayout(header)
        overlay.setContentsMargins(20, 20, 20, 16)
        overlay.addStretch(1)
        overlay.addWidget(title)
        overlay.addWidget(artist)
        fl.addWidget(header)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(18, 16, 18, 18)
        bl.setSpacing(10)
        video_str = _tr("details_video") if set_data.get('HasVideo') else _tr("details_no_video")
        info = QLabel(
            f"👤 {set_data.get('Creator', '?')}    •    📅 {set_data.get('LastUpdate', '?')}    •    {video_str}"
        )
        info.setStyleSheet(f"color:{theme.data['muted']};")
        bl.addWidget(info)

        diff_scroll = QScrollArea()
        diff_scroll.setWidgetResizable(True)
        diff_scroll.setFrameShape(QFrame.NoFrame)
        diff_scroll.setAttribute(Qt.WA_TranslucentBackground, True)
        diff_scroll.viewport().setObjectName("ScrollViewport")
        diff_scroll.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        diff_container = QWidget()
        diff_container.setObjectName("ScrollViewport")
        diffs = QVBoxLayout(diff_container)
        diffs.setContentsMargins(0, 0, 4, 0)
        diffs.setSpacing(6)
        diffs.setAlignment(Qt.AlignTop)
        row_border = rgba(theme.data['border'], 90)
        row_bg = rgba(theme.data['panel'], 46)
        for d in sorted(set_data.get("ChildrenBeatmaps") or [], key=lambda x: float(x.get("DifficultyRating", 0))):
            row = QHBoxLayout()
            row.setContentsMargins(12, 0, 12, 0)
            row.setSpacing(10)
            stars = float(d.get("DifficultyRating", 0))
            star_label = QLabel(f"★{stars:.2f}")
            star_label.setFixedWidth(58)
            star_label.setFont(app_font(11, QFont.Bold))
            star_label.setStyleSheet(f"color:{theme.data['accent']}; background:transparent;")
            mode_icon = MODE_ICONS.get(int(d.get("Mode", 0)), "○")
            name = QLabel(f"{mode_icon} {d.get('DiffName', '?')}")
            name.setStyleSheet("background:transparent;")
            name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            fm_metrics = name.fontMetrics()
            name.setToolTip(name.text())
            name.setText(fm_metrics.elidedText(name.text(), Qt.ElideRight, 320))
            stats = QLabel(
                f"AR {d.get('AR','?')}   CS {d.get('CS','?')}   OD {d.get('OD','?')}   HP {d.get('HP','?')}   {_tr('details_combo')} {d.get('MaxCombo','?')}"
            )
            stats.setStyleSheet(f"color:{theme.data['muted']}; font-size:11px; background:transparent;")
            stats.setMinimumWidth(230)
            stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(star_label)
            row.addWidget(name, 1)
            row.addWidget(stats)
            holder = QFrame()
            holder.setFixedHeight(40)
            holder.setStyleSheet(
                f"QFrame{{background:{row_bg}; border:1px solid {row_border}; border-radius:6px;}}"
            )
            holder.setLayout(row)
            diffs.addWidget(holder)
        diff_scroll.setWidget(diff_container)
        bl.addWidget(diff_scroll, 1)

        actions = QHBoxLayout()
        self.download_button = QPushButton(_tr("details_download"))
        self.download_button.setObjectName("accentButton")
        self.no_video_button = QPushButton(_tr("details_download_no_video"))
        open_btn = QPushButton(_tr("details_open_osu"))
        close_btn = QPushButton(_tr("details_close"))
        self.download_button.clicked.connect(lambda: self.download(False))
        self.no_video_button.clicked.connect(lambda: self.download(True))
        open_btn.clicked.connect(self.open_on_osu)
        close_btn.clicked.connect(self.reject)
        actions.addWidget(self.download_button)
        actions.addWidget(self.no_video_button)
        actions.addWidget(open_btn)
        actions.addStretch(1)
        actions.addWidget(close_btn)
        bl.addLayout(actions)
        bl.addWidget(self.progress)
        fl.addWidget(body)
        root.addWidget(frame)
        QTimer.singleShot(0, self._animate_open)

    def _animate_open(self) -> None:
        anim = QPropertyAnimation(self._dialog_opacity, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._detach_dialog_effect)
        self._dialog_anim = anim
        anim.start()

    def _detach_dialog_effect(self) -> None:
        try:
            self._modal_frame.setGraphicsEffect(None)
        except RuntimeError:
            pass
        self._dialog_opacity = None

    def _set_header_image(self, label: QLabel, image: QImage) -> None:
        pix = QPixmap.fromImage(image).scaled(label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (pix.width() - label.width()) // 2)
        y = max(0, (pix.height() - label.height()) // 2)
        cropped = pix.copy(x, y, label.width(), label.height())
        result = QPixmap(cropped.size())
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.drawPixmap(0, 0, cropped)
        gradient = QLinearGradient(0, 0, 0, cropped.height())
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.45, QColor(0, 0, 0, 40))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 190))
        painter.fillRect(cropped.rect(), QBrush(gradient))
        painter.end()
        label.setPixmap(result)

    def _header_loaded(self, url: str, image: object, expected_url: str, label: QLabel) -> None:
        if url == expected_url and isinstance(image, QImage):
            self.cache[url] = image
            self._set_header_image(label, image)

    def download(self, no_video: bool) -> None:
        set_id = self.set_data.get("SetID")
        if not set_id:
            return
        url = f"{API_BASE}/d/{set_id}{'n' if no_video else ''}"
        name = escape_filename(f"{set_id}_{self.set_data.get('Title', 'beatmap')}") + ".osz"
        target = DOWNLOAD_DIR / name
        btn = self.no_video_button if no_video else self.download_button
        if btn:
            btn.setEnabled(False)
            btn.setText(_tr("details_downloading"))
        self.progress.setVisible(True)
        self.progress.setValue(0)
        worker = DownloadWorker(url, target)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.finished.connect(lambda p: self.download_finished(p, btn))
        worker.signals.error.connect(lambda e: self.download_error(e, btn))
        self.pool.start(worker)

    def download_finished(self, path: str, btn: Optional[QPushButton]) -> None:
        if btn:
            btn.setEnabled(True)
            btn.setText(_tr("details_download") if btn is self.download_button else _tr("details_download_no_video"))
        try:
            install_file(Path(path))
        except Exception as exc:
            QMessageBox.warning(
                self,
                _tr("details_download_success_title"),
                _tr("details_download_success_text", path=path) + f"\n\n{exc}"
            )
        else:
            QMessageBox.information(
                self,
                _tr("details_download_success_title"),
                _tr("details_download_success_text", path=path)
            )
        self.progress.setVisible(False)

    def download_error(self, message: str, btn: Optional[QPushButton]) -> None:
        if btn:
            btn.setEnabled(True)
            btn.setText(_tr("details_download") if btn is self.download_button else _tr("details_download_no_video"))
        self.progress.setVisible(False)
        QMessageBox.critical(
            self,
            _tr("details_download_error_title"),
            _tr("details_download_error_text", error=message)
        )

    def open_on_osu(self) -> None:
        webbrowser.open(f"https://osu.ppy.sh/beatmapsets/{self.set_data.get('SetID')}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.theme = ThemeManager()
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max(4, min(10, self.pool.maxThreadCount())))
        self.cover_cache: dict[str, QImage] = {}
        self.results: list[dict[str, Any]] = []
        self.generation = 0
        self.filters = SearchFilters()
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(450)
        self.search_timer.timeout.connect(self.start_search)

        self.setWindowTitle(_tr("app_name"))
        self.resize(1280, 760)
        self.setMinimumSize(980, 620)
        self.build_ui()
        self.apply_theme()
        self.install_shortcuts()
        self.start_search()

    def build_ui(self) -> None:
        self.bg = BackgroundWidget(self.theme)
        self.setCentralWidget(self.bg)
        root = QVBoxLayout(self.bg)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(7)

        toolbar = QFrame()
        toolbar.setObjectName("Toolbar")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 6, 8, 6)
        self.logo_label = QLabel(_tr("app_name"))
        self.logo_label.setFont(app_font(12, QFont.Bold))
        self.logo_label.setToolTip(_tr("app_name"))
        tl.addWidget(self.logo_label)
        tl.addSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_tr("search_placeholder"))
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.start_search)
        self.search.textChanged.connect(self.schedule_search)
        tl.addWidget(self.search, 1)
        self.search_btn = QPushButton(_tr("search_button"))
        self.search_btn.setObjectName("accentButton")
        self.search_btn.clicked.connect(self.start_search)
        tl.addWidget(self.search_btn)
        self.import_btn = QPushButton(_tr("import_button"))
        self.import_btn.clicked.connect(self.import_local)
        tl.addWidget(self.import_btn)
        self.theme_btn = QToolButton()
        self.theme_btn.setText(_tr("theme_button"))
        self.theme_btn.clicked.connect(self.open_theme)
        tl.addWidget(self.theme_btn)
        root.addWidget(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(205)
        sidebar.setMaximumWidth(255)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(10, 10, 10, 10)
        sl.setSpacing(9)

        self.mode_label_heading = self.add_sidebar_label(sl, _tr("mode_label"))
        self.mode_buttons: list[QPushButton] = []
        mode_grid = QGridLayout()
        modes = [
            ( -1, _tr("mode_all")),
            (0, _tr("mode_osu")),
            (1, _tr("mode_taiko")),
            (2, _tr("mode_catch")),
            (3, _tr("mode_mania")),
        ]
        for idx, (mode, label) in enumerate(modes):
            b = QPushButton(label)
            b.setCheckable(True)
            b.clicked.connect(lambda checked=False, m=mode: self.set_mode(m))
            self.mode_buttons.append(b)
            mode_grid.addWidget(b, idx // 2, idx % 2)
        sl.addLayout(mode_grid)
        self.mode_buttons[0].setChecked(True)

        self.status_label_heading = self.add_sidebar_label(sl, _tr("status_label"))
        self.status_combo = QComboBox()
        status_items = [
            (_tr("status_all"), None),
            (_tr("status_ranked"), 1),
            (_tr("status_loved"), 4),
            (_tr("status_qualified"), 3),
            (_tr("status_pending"), 0),
            (_tr("status_graveyard"), "graveyard"),
        ]
        for label, data in status_items:
            self.status_combo.addItem(label, data)
        self.status_combo.currentIndexChanged.connect(self.set_status)
        self.status_combo.setCurrentText(_tr("status_ranked"))
        sl.addWidget(self.status_combo)

        self.stars_label_heading = self.add_sidebar_label(sl, _tr("stars_label"))
        star_box = QGroupBox()
        sgl = QFormLayout(star_box)
        self.min_slider = QSlider(Qt.Horizontal)
        self.max_slider = QSlider(Qt.Horizontal)
        for slider, value in [(self.min_slider, 0), (self.max_slider, 100)]:
            slider.setRange(0, 100)
            slider.setValue(value)
        self.min_label = QLabel("0.0★")
        self.max_label = QLabel("10.0★")
        self.min_slider.valueChanged.connect(self.star_changed)
        self.max_slider.valueChanged.connect(self.star_changed)
        min_row = QHBoxLayout(); min_row.addWidget(self.min_slider, 1); min_row.addWidget(self.min_label)
        max_row = QHBoxLayout(); max_row.addWidget(self.max_slider, 1); max_row.addWidget(self.max_label)
        self.stars_min_row_label = QLabel(_tr("stars_min"))
        self.stars_max_row_label = QLabel(_tr("stars_max"))
        sgl.addRow(self.stars_min_row_label, min_row)
        sgl.addRow(self.stars_max_row_label, max_row)
        sl.addWidget(star_box)

        self.sort_label_heading = self.add_sidebar_label(sl, _tr("sort_label"))
        self.sort_combo = QComboBox()
        sort_items = [
            (_tr("sort_relevance"), "relevance"),
            (_tr("sort_title"), "title"),
            (_tr("sort_artist"), "artist"),
            (_tr("sort_difficulty"), "difficulty"),
            (_tr("sort_updated"), "updated"),
        ]
        for label, data in sort_items:
            self.sort_combo.addItem(label, data)
        self.sort_combo.currentIndexChanged.connect(self.change_sort)
        sl.addWidget(self.sort_combo)

        self.language_label_heading = self.add_sidebar_label(sl, _tr("language_label"))
        self.language_combo = QComboBox()
        languages = [
            ("Polski", "pl"),
            ("English", "en"),
            ("Deutsch", "de"),
            ("Русский", "ru"),
        ]
        for label, code in languages:
            self.language_combo.addItem(label, code)
        idx = self.language_combo.findData(i18n.current_lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        sl.addWidget(self.language_combo)

        self.import_label_heading = self.add_sidebar_label(sl, _tr("import_button"))
        self.note_label = QLabel(_tr("import_note"))
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet(f"color:{self.theme.data['muted']}; line-height:1.4;")
        sl.addWidget(self.note_label)
        sl.addStretch(1)
        self.theme_info_label = QLabel(_tr("theme_info"))
        self.theme_info_label.setStyleSheet(f"color:{self.theme.data['muted']}; font-size:10px;")
        sl.addWidget(self.theme_info_label)

        splitter.addWidget(sidebar)

        main = QWidget()
        main.setObjectName("ContentArea")
        main.setAttribute(Qt.WA_TranslucentBackground, True)
        ml = QVBoxLayout(main)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(6)
        result_bar = QFrame()
        result_bar.setObjectName("ResultsBar")
        rbl = QHBoxLayout(result_bar)
        rbl.setContentsMargins(9, 6, 9, 6)
        self.result_count = QLabel(_tr("result_searching"))
        self.result_count.setStyleSheet(f"color:{self.theme.data['muted']};")
        self.page_label = QLabel(_tr("page_label", page=1))
        self.page_label.setStyleSheet(f"color:{self.theme.data['muted']};")
        self.prev_btn = QPushButton(_tr("prev_button"))
        self.next_btn = QPushButton(_tr("next_button"))
        self.prev_btn.clicked.connect(lambda: self.change_page(-1))
        self.next_btn.clicked.connect(lambda: self.change_page(1))
        rbl.addWidget(self.result_count, 1)
        rbl.addWidget(self.page_label)
        rbl.addWidget(self.prev_btn)
        rbl.addWidget(self.next_btn)
        ml.addWidget(result_bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setAttribute(Qt.WA_TranslucentBackground, True)
        self.scroll.viewport().setObjectName("ScrollViewport")
        self.scroll.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        self.grid = ResultsGrid(self.theme, self.pool, self.cover_cache)
        self.grid.setObjectName("ResultsGrid")
        self.grid.setAttribute(Qt.WA_TranslucentBackground, True)
        self.grid.card_clicked.connect(self.open_details)
        self.scroll.setWidget(self.grid)
        ml.addWidget(self.scroll, 1)
        splitter.addWidget(main)
        splitter.setSizes([225, 1000])

    def add_sidebar_label(self, layout: QVBoxLayout, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color:{self.theme.data['muted']}; font-size:10px; font-weight:700; letter-spacing:1px;")
        layout.addWidget(label)
        return label

    def install_shortcuts(self) -> None:
        self.shortcuts = []
        for sequence, callback in [
            ("Ctrl+L", self.search.setFocus),
            ("/", self.focus_search),
            ("Escape", self.clear_search_focus),
        ]:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def clear_search_focus(self) -> None:
        self.search.clearFocus()

    def apply_theme(self) -> None:
        QApplication.instance().setStyleSheet(self.theme.css())  # type: ignore[union-attr]
        self.bg.theme = self.theme
        self.bg.reload_image()
        self.grid.theme = self.theme
        self.grid.rebuild()

    def open_theme(self) -> None:
        dialog = ThemeDialog(self.theme, self)
        dialog.applied.connect(self.apply_theme)
        dialog.exec()

    def change_language(self) -> None:
        lang = self.language_combo.currentData()
        if not lang or lang == i18n.current_lang:
            return
        i18n.set_language(lang)
        self.retranslate_ui()
        self.grid.rebuild()

    def retranslate_ui(self) -> None:
        """Update all static texts after language change."""
        self.setWindowTitle(_tr("app_name"))

        # Toolbar
        self.logo_label.setText(_tr("app_name"))
        self.logo_label.setToolTip(_tr("app_name"))
        self.search.setPlaceholderText(_tr("search_placeholder"))
        self.search_btn.setText(_tr("search_button"))
        self.import_btn.setText(_tr("import_button"))
        self.theme_btn.setText(_tr("theme_button"))

        # Sidebar section headings
        self.mode_label_heading.setText(_tr("mode_label"))
        self.status_label_heading.setText(_tr("status_label"))
        self.stars_label_heading.setText(_tr("stars_label"))
        self.sort_label_heading.setText(_tr("sort_label"))
        self.language_label_heading.setText(_tr("language_label"))
        self.import_label_heading.setText(_tr("import_button"))
        self.stars_min_row_label.setText(_tr("stars_min"))
        self.stars_max_row_label.setText(_tr("stars_max"))
        self.note_label.setText(_tr("import_note"))
        self.theme_info_label.setText(_tr("theme_info"))

        # Results bar
        self.result_count.setText(_tr("result_searching") if not self.results else _tr("result_count", count=len(self.results)))
        self.page_label.setText(_tr("page_label", page=self.filters.page + 1))
        self.prev_btn.setText(_tr("prev_button"))
        self.next_btn.setText(_tr("next_button"))

        # Mode buttons
        modes = [_tr("mode_all"), _tr("mode_osu"), _tr("mode_taiko"), _tr("mode_catch"), _tr("mode_mania")]
        for i, b in enumerate(self.mode_buttons):
            b.setText(modes[i])

        # Status combo (keep current selection)
        current_status = self.status_combo.currentData()
        self.status_combo.blockSignals(True)
        self.status_combo.clear()
        status_items = [
            (_tr("status_all"), None),
            (_tr("status_ranked"), 1),
            (_tr("status_loved"), 4),
            (_tr("status_qualified"), 3),
            (_tr("status_pending"), 0),
            (_tr("status_graveyard"), "graveyard"),
        ]
        for label, data in status_items:
            self.status_combo.addItem(label, data)
        restored_idx = self.status_combo.findData(current_status)
        self.status_combo.setCurrentIndex(restored_idx if restored_idx >= 0 else 1)
        self.status_combo.blockSignals(False)

        # Sort combo (keep current selection)
        current_sort = self.sort_combo.currentData()
        self.sort_combo.blockSignals(True)
        self.sort_combo.clear()
        sort_items = [
            (_tr("sort_relevance"), "relevance"),
            (_tr("sort_title"), "title"),
            (_tr("sort_artist"), "artist"),
            (_tr("sort_difficulty"), "difficulty"),
            (_tr("sort_updated"), "updated"),
        ]
        for label, data in sort_items:
            self.sort_combo.addItem(label, data)
        restored_idx = self.sort_combo.findData(current_sort)
        self.sort_combo.setCurrentIndex(restored_idx if restored_idx >= 0 else 0)
        self.sort_combo.blockSignals(False)

    def schedule_search(self) -> None:
        self.search_timer.start()

    def set_mode(self, mode: int) -> None:
        self.filters.mode = mode
        for i, b in enumerate(self.mode_buttons):
            b.setChecked((i == 0 and mode == -1) or (i == mode + 1))
        self.filters.page = 0
        self.start_search()

    def set_status(self) -> None:
        self.filters.status = self.status_combo.currentData()
        self.filters.page = 0
        self.start_search()

    def star_changed(self) -> None:
        min_v = self.min_slider.value() / 10
        max_v = self.max_slider.value() / 10
        if min_v > max_v:
            if self.sender() is self.min_slider:
                min_v = max_v
                self.min_slider.blockSignals(True)
                self.min_slider.setValue(int(max_v * 10))
                self.min_slider.blockSignals(False)
            else:
                max_v = min_v
                self.max_slider.blockSignals(True)
                self.max_slider.setValue(int(min_v * 10))
                self.max_slider.blockSignals(False)
        self.min_label.setText(f"{min_v:.1f}★")
        self.max_label.setText(f"{max_v:.1f}★")
        changed = (min_v != self.filters.min_stars or max_v != self.filters.max_stars)
        self.filters.min_stars = min_v
        self.filters.max_stars = max_v
        if changed:
            self.filters.page = 0
            self.start_search()

    def change_sort(self) -> None:
        self.filters.sort = str(self.sort_combo.currentData())
        self.results = sort_results(self.results, self.filters.sort)
        self.grid.set_data(self.results)

    def change_page(self, delta: int) -> None:
        new_page = self.filters.page + delta
        if new_page < 0:
            return
        if delta > 0 and not self.results:
            return
        self.filters.page = new_page
        self.start_search()
        bar = self.scroll.verticalScrollBar()
        anim = QPropertyAnimation(bar, b"value", self)
        anim.setDuration(260)
        anim.setStartValue(bar.value())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_anim = anim
        anim.start()

    def start_search(self) -> None:
        self.search_timer.stop()
        self.filters.query = self.search.text().strip()
        self.generation += 1
        generation = self.generation
        filters = SearchFilters(**asdict(self.filters))
        self.result_count.setText(_tr("result_searching"))
        self.next_btn.setEnabled(False)
        worker = SearchWorker(filters, generation)
        worker.signals.finished.connect(self.search_finished)
        worker.signals.error.connect(lambda msg, gen=generation: self.search_error(msg, gen))
        self.pool.start(worker)

    @Slot(object)
    def search_finished(self, payload: object) -> None:
        generation, data = payload
        if generation != self.generation:
            return
        self.results = list(data)
        self.grid.set_data(self.results)
        self.result_count.setText(_tr("result_count", count=len(self.results)))
        self.page_label.setText(_tr("page_label", page=self.filters.page + 1))
        self.prev_btn.setEnabled(self.filters.page > 0)
        self.next_btn.setEnabled(bool(self.results))

    def search_error(self, message: str, generation: int) -> None:
        if generation != self.generation:
            return
        self.result_count.setText(_tr("error_search_title"))
        self.grid.set_data([])
        self.next_btn.setEnabled(False)
        self.show_error(_tr("error_search_title"), _tr("error_search_text", error=message))

    def open_details(self, data: dict[str, Any]) -> None:
        dialog = DetailsDialog(data, self.theme, self.pool, self.cover_cache, self)
        dialog.exec()

    def import_local(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            _tr("import_local_title"),
            "",
            _tr("import_local_filter")
        )
        if not path:
            return
        try:
            result = convert_local_to_osz(Path(path))
            install_file(result)
            QMessageBox.information(
                self,
                _tr("import_local_success_title"),
                _tr("import_local_success_text", path=str(result))
            )
        except Exception as exc:
            self.show_error(_tr("import_local_error_title"), _tr("import_local_error_text", error=str(exc)))

    def show_error(self, title: str, text: str) -> None:
        QMessageBox.critical(self, title, text)


def convert_local_to_osz(source: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(_tr("error_file_not_found", path=source))
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".osz":
        target = DOWNLOAD_DIR / source.name
        shutil.copy2(source, target)
        return target

    temp_root = Path(tempfile.mkdtemp(prefix="osu_finder_"))
    extract_root = temp_root / "extracted"
    extract_root.mkdir()
    try:
        suffix = source.suffix.lower()
        if suffix == ".zip":
            with zipfile.ZipFile(source) as zf:
                if not any(n.lower().endswith(".osu") for n in zf.namelist()):
                    raise ValueError(_tr("error_invalid_zip"))
                zf.extractall(extract_root)
        elif suffix == ".7z":
            try:
                import py7zr
            except ImportError as exc:
                raise RuntimeError(_tr("error_7z_missing")) from exc
            with py7zr.SevenZipFile(source, mode="r") as zf:
                zf.extractall(path=extract_root)
        elif suffix == ".rar":
            try:
                import rarfile
            except ImportError as exc:
                raise RuntimeError(_tr("error_rar_missing")) from exc
            with rarfile.RarFile(source) as rf:
                rf.extractall(path=extract_root)
        else:
            raise ValueError(_tr("error_unsupported_format"))

        osu_files = list(extract_root.rglob("*.osu"))
        if not osu_files:
            raise ValueError(_tr("error_no_osu_files"))
        target = DOWNLOAD_DIR / f"{escape_filename(source.stem)}.osz"
        counter = 1
        while target.exists():
            target = DOWNLOAD_DIR / f"{escape_filename(source.stem)}_{counter}.osz"
            counter += 1
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file in extract_root.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(extract_root).as_posix())
        return target
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("osu-finder")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())