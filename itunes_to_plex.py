#!/usr/bin/env python3
"""
iTunes → Plex Rating Transfer
Parses iTunes Music Library XML and transfers star ratings to Plex Media Server.
"""

import sys
import json
import plistlib
import unicodedata
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional
from urllib.parse import unquote, urlparse

import requests
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSettings, QSize, QTimer
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QTextEdit, QSpinBox, QCheckBox, QComboBox, QGroupBox,
    QSplitter, QStatusBar, QMessageBox, QAbstractItemView,
    QFrame, QScrollArea, QSizePolicy
)

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

SETTINGS_FILE = Path.home() / ".itunes_plex_sync.json"
APP_NAME = "iTunes → Plex Ratings"
APP_VERSION = "1.2.0"

DARK_PALETTE = {
    "bg_deep":    "#0d0d0f",
    "bg_panel":   "#141418",
    "bg_card":    "#1c1c22",
    "bg_input":   "#22222a",
    "border":     "#2e2e3a",
    "border_hi":  "#4a4a5e",
    "accent":     "#7c6af7",
    "accent_dim": "#4a3fa0",
    "accent_glow":"#a594ff",
    "text_hi":    "#f0eeff",
    "text_mid":   "#b0aac8",
    "text_dim":   "#6b6480",
    "success":    "#4ade80",
    "warning":    "#fbbf24",
    "error":      "#f87171",
    "star":       "#fbbf24",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {DARK_PALETTE['bg_deep']};
    color: {DARK_PALETTE['text_hi']};
    font-family: 'SF Pro Display', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}}

QTabWidget::pane {{
    border: 1px solid {DARK_PALETTE['border']};
    background-color: {DARK_PALETTE['bg_panel']};
    border-radius: 8px;
}}

QTabBar::tab {{
    background-color: {DARK_PALETTE['bg_card']};
    color: {DARK_PALETTE['text_dim']};
    padding: 10px 22px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
    letter-spacing: 0.3px;
}}
QTabBar::tab:selected {{
    background-color: {DARK_PALETTE['accent']};
    color: {DARK_PALETTE['text_hi']};
}}
QTabBar::tab:hover:!selected {{
    background-color: {DARK_PALETTE['bg_input']};
    color: {DARK_PALETTE['text_mid']};
}}

QGroupBox {{
    border: 1px solid {DARK_PALETTE['border']};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    background-color: {DARK_PALETTE['bg_card']};
    color: {DARK_PALETTE['text_mid']};
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {DARK_PALETTE['text_dim']};
}}

QLineEdit, QSpinBox, QComboBox {{
    background-color: {DARK_PALETTE['bg_input']};
    border: 1px solid {DARK_PALETTE['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {DARK_PALETTE['text_hi']};
    selection-background-color: {DARK_PALETTE['accent']};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {DARK_PALETTE['accent']};
    background-color: #26262e;
}}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border-color: {DARK_PALETTE['border_hi']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {DARK_PALETTE['bg_card']};
    border: 1px solid {DARK_PALETTE['border']};
    selection-background-color: {DARK_PALETTE['accent_dim']};
    color: {DARK_PALETTE['text_hi']};
}}

QPushButton {{
    background-color: {DARK_PALETTE['bg_input']};
    border: 1px solid {DARK_PALETTE['border']};
    border-radius: 6px;
    padding: 8px 18px;
    color: {DARK_PALETTE['text_mid']};
    font-weight: 500;
}}
QPushButton:hover {{
    border-color: {DARK_PALETTE['accent']};
    color: {DARK_PALETTE['text_hi']};
    background-color: {DARK_PALETTE['bg_card']};
}}
QPushButton:pressed {{
    background-color: {DARK_PALETTE['accent_dim']};
}}
QPushButton:disabled {{
    color: {DARK_PALETTE['text_dim']};
    border-color: {DARK_PALETTE['border']};
    background-color: {DARK_PALETTE['bg_deep']};
}}

QPushButton#primary {{
    background-color: {DARK_PALETTE['accent']};
    border-color: {DARK_PALETTE['accent']};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background-color: {DARK_PALETTE['accent_glow']};
    border-color: {DARK_PALETTE['accent_glow']};
}}
QPushButton#primary:disabled {{
    background-color: {DARK_PALETTE['accent_dim']};
    border-color: {DARK_PALETTE['accent_dim']};
    color: {DARK_PALETTE['text_dim']};
}}

QPushButton#danger {{
    border-color: {DARK_PALETTE['error']};
    color: {DARK_PALETTE['error']};
}}
QPushButton#danger:hover {{
    background-color: rgba(248, 113, 113, 0.15);
}}

QTableWidget {{
    background-color: {DARK_PALETTE['bg_panel']};
    gridline-color: {DARK_PALETTE['border']};
    border: 1px solid {DARK_PALETTE['border']};
    border-radius: 6px;
    selection-background-color: {DARK_PALETTE['accent_dim']};
    color: {DARK_PALETTE['text_hi']};
    alternate-background-color: {DARK_PALETTE['bg_card']};
}}
QTableWidget::item {{
    padding: 6px 10px;
    border: none;
}}
QTableWidget::item:selected {{
    background-color: {DARK_PALETTE['accent_dim']};
    color: {DARK_PALETTE['text_hi']};
}}
QHeaderView::section {{
    background-color: {DARK_PALETTE['bg_card']};
    color: {DARK_PALETTE['text_dim']};
    border: none;
    border-bottom: 1px solid {DARK_PALETTE['border']};
    padding: 8px 10px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

QProgressBar {{
    background-color: {DARK_PALETTE['bg_input']};
    border: 1px solid {DARK_PALETTE['border']};
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {DARK_PALETTE['accent']}, stop:1 {DARK_PALETTE['accent_glow']});
    border-radius: 4px;
}}

QTextEdit {{
    background-color: {DARK_PALETTE['bg_deep']};
    border: 1px solid {DARK_PALETTE['border']};
    border-radius: 6px;
    color: {DARK_PALETTE['text_mid']};
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
    padding: 8px;
}}

QCheckBox {{
    color: {DARK_PALETTE['text_mid']};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {DARK_PALETTE['border_hi']};
    border-radius: 4px;
    background-color: {DARK_PALETTE['bg_input']};
}}
QCheckBox::indicator:checked {{
    background-color: {DARK_PALETTE['accent']};
    border-color: {DARK_PALETTE['accent']};
}}

QScrollBar:vertical {{
    background: {DARK_PALETTE['bg_deep']};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {DARK_PALETTE['border_hi']};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {DARK_PALETTE['text_dim']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {DARK_PALETTE['bg_deep']};
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {DARK_PALETTE['border_hi']};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QStatusBar {{
    background-color: {DARK_PALETTE['bg_card']};
    color: {DARK_PALETTE['text_dim']};
    border-top: 1px solid {DARK_PALETTE['border']};
    font-size: 11px;
}}

QLabel#heading {{
    font-size: 22px;
    font-weight: 700;
    color: {DARK_PALETTE['text_hi']};
    letter-spacing: -0.5px;
}}
QLabel#subheading {{
    font-size: 13px;
    color: {DARK_PALETTE['text_dim']};
}}
QLabel#stat_value {{
    font-size: 28px;
    font-weight: 700;
    color: {DARK_PALETTE['accent_glow']};
}}
QLabel#stat_label {{
    font-size: 11px;
    color: {DARK_PALETTE['text_dim']};
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

QFrame#separator {{
    background-color: {DARK_PALETTE['border']};
    max-height: 1px;
}}
QFrame#card {{
    background-color: {DARK_PALETTE['bg_card']};
    border: 1px solid {DARK_PALETTE['border']};
    border-radius: 10px;
}}
"""


# ──────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────

DEFAULT_SETTINGS = {
    "plex_url": "http://localhost:32400",
    "plex_token": "",
    "plex_library": "Music",
    "xml_path": "",
    "match_threshold": 85,
    "dry_run": False,
    "skip_unrated": True,
    "overwrite_existing": False,
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                saved = json.load(f)
            return {**DEFAULT_SETTINGS, **saved}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(s: dict) -> None:
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)


# ──────────────────────────────────────────────────────────────
# iTunes XML parser
# ──────────────────────────────────────────────────────────────

def itunes_rating_to_stars(raw: int) -> int:
    """Convert iTunes 0-100 rating to 1-5 stars. Returns 0 if unrated."""
    if raw <= 0:
        return 0
    return max(1, min(5, round(raw / 20)))


def itunes_location_to_path(location: str) -> str:
    """
    Convert an iTunes XML Location URL to a normalised file path string.

    iTunes stores locations as RFC-2396 file URLs, e.g.:
      file:///A:/Apple%20Music/Artist/Album/Track.mp3   (Windows, via macOS iTunes)
      file://localhost/A:/Apple%20Music/…               (older iTunes on Windows)

    Returns a lower-cased, forward-slash path for case-insensitive comparison,
    e.g. "a:/apple music/artist/album/track.mp3".
    """
    if not location:
        return ""
    try:
        parsed = urlparse(location)
        # unquote percent-encoding (%20 → space, etc.)
        path = unquote(parsed.path)
        # On Windows the path starts with /A:/… — strip the leading slash
        if re.match(r"^/[A-Za-z]:/", path):
            path = path[1:]
        # Normalise separators and case for comparison
        return path.replace("\\", "/").lower()
    except Exception:
        return ""


def parse_itunes_xml(path: str) -> tuple[list[dict], list[dict]]:
    """
    Returns (tracks, playlists).

    tracks: list of dicts with keys: track_id, title, artist, album,
            rating_raw, stars, location.
    playlists: list of dicts with keys: name, track_ids (set of int).
    """
    with open(path, "rb") as f:
        lib = plistlib.load(f)

    # ── Tracks ──
    tracks = []
    for track_id_str, info in lib.get("Tracks", {}).items():
        if info.get("Track Type") == "URL":
            continue  # skip radio streams
        rating_raw = info.get("Rating", 0)
        tracks.append({
            "track_id":   int(track_id_str),
            "title":      info.get("Name", ""),
            "artist":     info.get("Artist", ""),
            "album":      info.get("Album", ""),
            "rating_raw": rating_raw,
            "stars":      itunes_rating_to_stars(rating_raw),
            "location":   itunes_location_to_path(info.get("Location", "")),
        })

    # ── Playlists ──
    playlists = []
    for pl in lib.get("Playlists", []):
        name = pl.get("Name", "")
        if not name:
            continue
        track_ids = {
            item["Track ID"]
            for item in pl.get("Playlist Items", [])
            if "Track ID" in item
        }
        if not track_ids:
            continue
        playlists.append({"name": name, "track_ids": track_ids})

    # Sort playlists alphabetically for display
    playlists.sort(key=lambda p: p["name"].lower())
    return tracks, playlists


# ──────────────────────────────────────────────────────────────
# Plex API
# ──────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Lowercase, strip accents, remove non-alphanum for fuzzy comparison."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def similarity(a: str, b: str) -> int:
    """Simple token overlap score 0–100."""
    a_tokens = set(normalize(a).split())
    b_tokens = set(normalize(b).split())
    if not a_tokens or not b_tokens:
        return 0
    overlap = len(a_tokens & b_tokens)
    return int(100 * overlap / max(len(a_tokens), len(b_tokens)))


def plex_file_path(plex_track: dict) -> str:
    """
    Extract and normalise the file path from a Plex track's Media.Part info.
    Returns lower-cased forward-slash path, e.g. "a:/apple music/…/track.mp3".
    """
    try:
        media_list = plex_track.get("Media", [])
        if media_list:
            parts = media_list[0].get("Part", [])
            if parts:
                raw = parts[0].get("file", "")
                return raw.replace("\\", "/").lower()
    except Exception:
        pass
    return ""


class PlexClient:
    def __init__(self, url: str, token: str, library: str):
        self.base = url.rstrip("/")
        self.token = token
        self.library = library
        self.session = requests.Session()
        self.session.headers.update({
            "X-Plex-Token": token,
            "Accept": "application/json",
        })

    def _get(self, path: str, **params) -> dict:
        r = self.session.get(f"{self.base}{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, **params) -> None:
        params["X-Plex-Token"] = self.token
        r = self.session.put(f"{self.base}{path}", params=params, timeout=15)
        r.raise_for_status()

    def test_connection(self) -> tuple[bool, str]:
        try:
            data = self._get("/identity")
            version = data.get("MediaContainer", {}).get("version", "unknown")
            return True, f"Plex Media Server v{version}"
        except Exception as e:
            return False, str(e)

    def get_library_key(self) -> Optional[str]:
        data = self._get("/library/sections")
        for section in data.get("MediaContainer", {}).get("Directory", []):
            if section.get("title") == self.library and section.get("type") == "artist":
                return section["key"]
        return None

    def get_all_tracks(self, library_key: str) -> list[dict]:
        """Fetch all tracks from Plex library, including file path via Media.Part."""
        data = self._get(f"/library/sections/{library_key}/all",
                         type=10,          # type 10 = track
                         includeMedia=1)   # include Media.Part with file paths
        items = data.get("MediaContainer", {}).get("Metadata", [])
        return items

    def set_rating(self, rating_key: str, stars: int) -> None:
        """Set rating. Plex uses 0-10 (2 per star)."""
        plex_rating = stars * 2
        self._put(f"/:/rate", key=rating_key, identifier="com.plexapp.plugins.library",
                  rating=plex_rating)


# ──────────────────────────────────────────────────────────────
# Worker thread
# ──────────────────────────────────────────────────────────────

class TransferWorker(QThread):
    progress = pyqtSignal(int, int)       # current, total
    track_done = pyqtSignal(dict)         # result per track
    finished = pyqtSignal(dict)           # summary
    log = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, settings: dict, matched: list[dict]):
        super().__init__()
        self.settings = settings
        self.matched = matched  # list of {itunes_track, plex_track}
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        plex = PlexClient(
            self.settings["plex_url"],
            self.settings["plex_token"],
            self.settings["plex_library"],
        )
        total = len(self.matched)
        ok = skipped = failed = 0

        for i, pair in enumerate(self.matched):
            if self._cancelled:
                self.log.emit("⚠ Transfer cancelled by user.")
                break

            it = pair["itunes_track"]
            px = pair["plex_track"]
            label = f"{it['artist']} — {it['title']}"

            if self.settings["dry_run"]:
                self.log.emit(f"[DRY RUN] Would set {label} → {'★' * it['stars']}")
                ok += 1
                self.track_done.emit({"status": "dry_run", "label": label})
                self.progress.emit(i + 1, total)
                continue

            # Skip if track already has a rating and overwrite is disabled
            existing = px.get("userRating", 0) or 0
            if existing > 0 and not self.settings["overwrite_existing"]:
                self.log.emit(f"↷ Skip (already rated): {label}")
                skipped += 1
                self.track_done.emit({"status": "skipped", "label": label})
                self.progress.emit(i + 1, total)
                continue

            try:
                plex.set_rating(px["ratingKey"], it["stars"])
                self.log.emit(f"✓ {label} → {'★' * it['stars']}")
                ok += 1
                self.track_done.emit({"status": "ok", "label": label})
            except Exception as e:
                self.log.emit(f"✗ FAILED: {label} — {e}")
                failed += 1
                self.track_done.emit({"status": "failed", "label": label, "error": str(e)})

            self.progress.emit(i + 1, total)

        self.finished.emit({"ok": ok, "skipped": skipped, "failed": failed, "total": total})


class MatchWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list, list)   # matched, unmatched
    log = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, settings: dict, itunes_tracks: list[dict]):
        super().__init__()
        self.settings = settings
        self.itunes_tracks = itunes_tracks

    def run(self):
        try:
            plex = PlexClient(
                self.settings["plex_url"],
                self.settings["plex_token"],
                self.settings["plex_library"],
            )

            self.log.emit("Connecting to Plex…")
            ok, msg = plex.test_connection()
            if not ok:
                self.error.emit(f"Cannot connect to Plex: {msg}")
                return

            self.log.emit(f"Connected: {msg}")
            lib_key = plex.get_library_key()
            if not lib_key:
                self.error.emit(f"Library '{self.settings['plex_library']}' not found.")
                return

            self.log.emit("Fetching Plex library tracks (with file paths)…")
            plex_tracks = plex.get_all_tracks(lib_key)
            self.log.emit(f"Found {len(plex_tracks)} Plex tracks.")

            # ── Build path index (primary) ──
            # key: normalised file path → plex_track
            plex_by_path: dict[str, dict] = {}
            for pt in plex_tracks:
                fp = plex_file_path(pt)
                if fp:
                    plex_by_path[fp] = pt

            path_index_size = len(plex_by_path)
            self.log.emit(
                f"Path index built: {path_index_size} Plex tracks have file paths. "
                f"{'Fuzzy fallback active for the rest.' if path_index_size < len(plex_tracks) else ''}"
            )

            # ── Build text index (fuzzy fallback) ──
            plex_by_text: dict[tuple, list] = {}
            for pt in plex_tracks:
                key = (normalize(pt.get("title", "")), normalize(pt.get("grandparentTitle", "")))
                plex_by_text.setdefault(key, []).append(pt)

            threshold = self.settings["match_threshold"]
            matched = []
            unmatched = []
            total = len(self.itunes_tracks)

            for i, it in enumerate(self.itunes_tracks):
                if self.settings["skip_unrated"] and it["stars"] == 0:
                    self.progress.emit(i + 1, total)
                    continue

                # ── 1. Path match (exact, highest confidence) ──
                it_path = it.get("location", "")
                if it_path and it_path in plex_by_path:
                    matched.append({
                        "itunes_track": it,
                        "plex_track":   plex_by_path[it_path],
                        "score":        100,
                        "method":       "path",
                    })
                    self.progress.emit(i + 1, total)
                    continue

                # ── 2. Text exact match ──
                it_title  = normalize(it["title"])
                it_artist = normalize(it["artist"])
                exact = plex_by_text.get((it_title, it_artist))
                if exact:
                    matched.append({
                        "itunes_track": it,
                        "plex_track":   exact[0],
                        "score":        100,
                        "method":       "text-exact",
                    })
                    self.progress.emit(i + 1, total)
                    continue

                # ── 3. Fuzzy text match ──
                best_score = 0
                best_pt = None
                for pt in plex_tracks:
                    pt_title  = normalize(pt.get("title", ""))
                    pt_artist = normalize(pt.get("grandparentTitle", ""))
                    score = (similarity(it_title, pt_title) * 0.7 +
                             similarity(it_artist, pt_artist) * 0.3)
                    if score > best_score:
                        best_score = score
                        best_pt = pt

                if best_score >= threshold and best_pt:
                    matched.append({
                        "itunes_track": it,
                        "plex_track":   best_pt,
                        "score":        int(best_score),
                        "method":       "fuzzy",
                    })
                else:
                    unmatched.append({
                        "itunes_track": it,
                        "best_plex":    best_pt,
                        "score":        int(best_score),
                    })

                self.progress.emit(i + 1, total)

            # Summary log
            path_count  = sum(1 for m in matched if m["method"] == "path")
            exact_count = sum(1 for m in matched if m["method"] == "text-exact")
            fuzzy_count = sum(1 for m in matched if m["method"] == "fuzzy")
            self.log.emit(
                f"Matching done — Path: {path_count}, Text-exact: {exact_count}, "
                f"Fuzzy: {fuzzy_count}, Unmatched: {len(unmatched)}"
            )
            self.finished.emit(matched, unmatched)

        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────────────────────
# UI helpers
# ──────────────────────────────────────────────────────────────

def stars_widget(stars: int, total: int = 5) -> str:
    filled = "★" * stars
    empty  = "☆" * (total - stars)
    return filled + empty


def make_label(text: str, obj_name: str = "", bold: bool = False) -> QLabel:
    lbl = QLabel(text)
    if obj_name:
        lbl.setObjectName(obj_name)
    if bold:
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
    return lbl


def hsep() -> QFrame:
    f = QFrame()
    f.setObjectName("separator")
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def stat_box(value: str, label: str) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(16, 12, 16, 12)
    v.setSpacing(2)
    v_lbl = QLabel(value)
    v_lbl.setObjectName("stat_value")
    v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    l_lbl = QLabel(label.upper())
    l_lbl.setObjectName("stat_label")
    l_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    v.addWidget(v_lbl)
    v.addWidget(l_lbl)
    w.setObjectName("card")
    w.setStyleSheet(f"QWidget#card {{ background: {DARK_PALETTE['bg_card']}; "
                    f"border: 1px solid {DARK_PALETTE['border']}; border-radius: 10px; }}")
    return w, v_lbl


# ──────────────────────────────────────────────────────────────
# Settings Tab
# ──────────────────────────────────────────────────────────────

class SettingsTab(QWidget):
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings.copy()
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(20)

        # Title
        outer.addWidget(make_label("Configuration", "heading"))
        outer.addWidget(make_label("Connection settings and transfer preferences", "subheading"))
        outer.addWidget(hsep())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner_w = QWidget()
        inner = QVBoxLayout(inner_w)
        inner.setSpacing(20)
        inner.setContentsMargins(0, 0, 0, 0)

        # ── Plex connection ──
        plex_group = QGroupBox("Plex Media Server")
        pg = QVBoxLayout(plex_group)
        pg.setSpacing(12)

        self.url_edit = QLineEdit(self.settings["plex_url"])
        self.url_edit.setPlaceholderText("http://localhost:32400")
        self.token_edit = QLineEdit(self.settings["plex_token"])
        self.token_edit.setPlaceholderText("Your Plex auth token")
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.library_edit = QLineEdit(self.settings["plex_library"])
        self.library_edit.setPlaceholderText("Music")

        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        self.test_result = QLabel("")
        self.test_result.setStyleSheet(f"color: {DARK_PALETTE['text_dim']};")

        for lbl, widget in [
            ("Server URL", self.url_edit),
            ("Auth Token", self.token_edit),
            ("Library Name", self.library_edit),
        ]:
            row = QHBoxLayout()
            l = QLabel(lbl)
            l.setFixedWidth(110)
            l.setStyleSheet(f"color: {DARK_PALETTE['text_mid']};")
            row.addWidget(l)
            row.addWidget(widget)
            pg.addLayout(row)

        help_token = QLabel(
            "Find your token: open Plex Web → any media item → ··· → Get Info → "
            "View XML. The token is in the URL (?X-Plex-Token=…)"
        )
        help_token.setStyleSheet(f"color: {DARK_PALETTE['text_dim']}; font-size: 11px;")
        help_token.setWordWrap(True)
        pg.addWidget(help_token)

        test_row = QHBoxLayout()
        test_row.addWidget(test_btn)
        test_row.addWidget(self.test_result)
        test_row.addStretch()
        pg.addLayout(test_row)
        inner.addWidget(plex_group)

        # ── Transfer options ──
        opt_group = QGroupBox("Transfer Options")
        og = QVBoxLayout(opt_group)
        og.setSpacing(12)

        thresh_row = QHBoxLayout()
        thresh_lbl = QLabel("Match threshold")
        thresh_lbl.setFixedWidth(160)
        thresh_lbl.setStyleSheet(f"color: {DARK_PALETTE['text_mid']};")
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(50, 100)
        self.threshold_spin.setValue(self.settings["match_threshold"])
        self.threshold_spin.setSuffix("%")
        self.threshold_spin.setFixedWidth(80)
        thresh_help = QLabel("Minimum fuzzy match score to auto-match a track")
        thresh_help.setStyleSheet(f"color: {DARK_PALETTE['text_dim']}; font-size: 11px;")
        thresh_row.addWidget(thresh_lbl)
        thresh_row.addWidget(self.threshold_spin)
        thresh_row.addWidget(thresh_help)
        thresh_row.addStretch()
        og.addLayout(thresh_row)

        self.skip_unrated_cb = QCheckBox("Skip unrated tracks (don't transfer 0-star tracks)")
        self.skip_unrated_cb.setChecked(self.settings["skip_unrated"])
        self.overwrite_cb = QCheckBox("Overwrite existing Plex ratings")
        self.overwrite_cb.setChecked(self.settings["overwrite_existing"])
        self.dry_run_cb = QCheckBox("Dry run (preview changes without writing to Plex)")
        self.dry_run_cb.setChecked(self.settings["dry_run"])

        og.addWidget(self.skip_unrated_cb)
        og.addWidget(self.overwrite_cb)
        og.addWidget(self.dry_run_cb)
        inner.addWidget(opt_group)

        # ── Save ──
        save_row = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primary")
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(self._save)
        save_row.addStretch()
        save_row.addWidget(save_btn)
        inner.addLayout(save_row)
        inner.addStretch()

        scroll.setWidget(inner_w)
        outer.addWidget(scroll)

    def _test_connection(self):
        self.test_result.setText("Testing…")
        self.test_result.setStyleSheet(f"color: {DARK_PALETTE['text_dim']};")
        QApplication.processEvents()
        plex = PlexClient(
            self.url_edit.text().strip(),
            self.token_edit.text().strip(),
            self.library_edit.text().strip(),
        )
        ok, msg = plex.test_connection()
        if ok:
            self.test_result.setText(f"✓ {msg}")
            self.test_result.setStyleSheet(f"color: {DARK_PALETTE['success']};")
        else:
            self.test_result.setText(f"✗ {msg}")
            self.test_result.setStyleSheet(f"color: {DARK_PALETTE['error']};")

    def _save(self):
        self.settings.update({
            "plex_url":           self.url_edit.text().strip(),
            "plex_token":         self.token_edit.text().strip(),
            "plex_library":       self.library_edit.text().strip(),
            "match_threshold":    self.threshold_spin.value(),
            "skip_unrated":       self.skip_unrated_cb.isChecked(),
            "overwrite_existing": self.overwrite_cb.isChecked(),
            "dry_run":            self.dry_run_cb.isChecked(),
        })
        save_settings(self.settings)
        self.settings_saved.emit(self.settings)
        QMessageBox.information(self, "Saved", "Settings saved successfully.")

    def get_settings(self) -> dict:
        return {
            "plex_url":           self.url_edit.text().strip(),
            "plex_token":         self.token_edit.text().strip(),
            "plex_library":       self.library_edit.text().strip(),
            "match_threshold":    self.threshold_spin.value(),
            "skip_unrated":       self.skip_unrated_cb.isChecked(),
            "overwrite_existing": self.overwrite_cb.isChecked(),
            "dry_run":            self.dry_run_cb.isChecked(),
            "xml_path":           self.settings.get("xml_path", ""),
        }


# ──────────────────────────────────────────────────────────────
# Main Tab  (load + match)
# ──────────────────────────────────────────────────────────────

class MainTab(QWidget):
    match_ready = pyqtSignal(list, list)   # matched, unmatched
    log_msg = pyqtSignal(str)

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.itunes_tracks: list[dict] = []
        self.playlists: list[dict] = []          # [{name, track_ids}, …]
        self.worker: Optional[MatchWorker] = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(20)

        outer.addWidget(make_label("Import & Match", "heading"))
        outer.addWidget(make_label("Load your iTunes XML and match tracks against Plex", "subheading"))
        outer.addWidget(hsep())

        # ── XML file chooser ──
        xml_group = QGroupBox("iTunes Library XML")
        xg = QHBoxLayout(xml_group)
        self.xml_path_edit = QLineEdit(self.settings.get("xml_path", ""))
        self.xml_path_edit.setPlaceholderText("Path to iTunes Music Library.xml…")
        self.xml_path_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_xml)
        xg.addWidget(self.xml_path_edit)
        xg.addWidget(browse_btn)
        outer.addWidget(xml_group)

        # ── Main content: splitter with playlist panel + track preview ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {DARK_PALETTE['border']}; }}")

        # Left: playlist selector (hidden until XML loaded)
        self._playlist_panel = QWidget()
        pl_layout = QVBoxLayout(self._playlist_panel)
        pl_layout.setContentsMargins(0, 0, 8, 0)
        pl_layout.setSpacing(6)

        pl_header = QHBoxLayout()
        pl_title = QLabel("Playlists")
        pl_title.setStyleSheet(
            f"font-weight: 600; font-size: 11px; letter-spacing: 0.8px; "
            f"color: {DARK_PALETTE['text_dim']}; text-transform: uppercase;"
        )
        self._pl_count_lbl = QLabel("")
        self._pl_count_lbl.setStyleSheet(f"color: {DARK_PALETTE['text_dim']}; font-size: 11px;")
        pl_header.addWidget(pl_title)
        pl_header.addStretch()
        pl_header.addWidget(self._pl_count_lbl)
        pl_layout.addLayout(pl_header)

        # Select all / none buttons
        pl_btn_row = QHBoxLayout()
        pl_btn_row.setSpacing(6)
        self._pl_all_btn = QPushButton("All")
        self._pl_all_btn.setFixedHeight(24)
        self._pl_all_btn.setStyleSheet(f"font-size: 11px; padding: 2px 10px;")
        self._pl_all_btn.clicked.connect(self._select_all_playlists)
        self._pl_none_btn = QPushButton("None")
        self._pl_none_btn.setFixedHeight(24)
        self._pl_none_btn.setStyleSheet(f"font-size: 11px; padding: 2px 10px;")
        self._pl_none_btn.clicked.connect(self._select_no_playlists)
        pl_btn_row.addWidget(self._pl_all_btn)
        pl_btn_row.addWidget(self._pl_none_btn)
        pl_btn_row.addStretch()
        pl_layout.addLayout(pl_btn_row)

        # Scrollable checklist
        pl_scroll = QScrollArea()
        pl_scroll.setWidgetResizable(True)
        pl_scroll.setFrameShape(QFrame.Shape.NoFrame)
        pl_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._pl_list_widget = QWidget()
        self._pl_list_layout = QVBoxLayout(self._pl_list_widget)
        self._pl_list_layout.setContentsMargins(4, 4, 4, 4)
        self._pl_list_layout.setSpacing(2)
        self._pl_list_layout.addStretch()
        pl_scroll.setWidget(self._pl_list_widget)
        pl_layout.addWidget(pl_scroll, stretch=1)

        self._pl_mode_lbl = QLabel("▸ All tracks (no playlist selected)")
        self._pl_mode_lbl.setStyleSheet(
            f"color: {DARK_PALETTE['accent_glow']}; font-size: 11px; font-style: italic;"
        )
        self._pl_mode_lbl.setWordWrap(True)
        pl_layout.addWidget(self._pl_mode_lbl)

        self._playlist_panel.setVisible(False)
        self._playlist_panel.setMinimumWidth(180)
        self._playlist_panel.setMaximumWidth(280)

        # Right: stats + progress + preview table (existing content)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # ── Stats row ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._stat_total_w, self._stat_total = stat_box("—", "iTunes Tracks")
        self._stat_rated_w, self._stat_rated = stat_box("—", "With Ratings")
        self._stat_match_w, self._stat_match = stat_box("—", "Matched")
        self._stat_unmatch_w, self._stat_unmatch = stat_box("—", "Unmatched")
        for w, _ in [(self._stat_total_w, None), (self._stat_rated_w, None),
                     (self._stat_match_w, None), (self._stat_unmatch_w, None)]:
            stats_row.addWidget(w)
        right_layout.addLayout(stats_row)

        # ── Progress ──
        self.match_progress = QProgressBar()
        self.match_progress.setVisible(False)
        self.match_status = QLabel("")
        self.match_status.setStyleSheet(f"color: {DARK_PALETTE['text_dim']};")
        right_layout.addWidget(self.match_progress)
        right_layout.addWidget(self.match_status)

        # ── Track preview table ──
        self.preview_table = QTableWidget(0, 5)
        self.preview_table.setHorizontalHeaderLabels(
            ["Artist", "Title", "Album", "Stars", "iTunes Rating"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.preview_table, stretch=1)

        splitter.addWidget(self._playlist_panel)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, stretch=1)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("Load XML")
        self.load_btn.setObjectName("primary")
        self.load_btn.clicked.connect(self._load_xml)

        self.match_btn = QPushButton("Match Against Plex")
        self.match_btn.setEnabled(False)
        self.match_btn.clicked.connect(self._start_match)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_match)

        btn_row.addStretch()
        btn_row.addWidget(self.load_btn)
        btn_row.addWidget(self.match_btn)
        btn_row.addWidget(self.cancel_btn)
        outer.addLayout(btn_row)

    # ── Playlist helpers ──

    def _populate_playlist_panel(self):
        """Rebuild the checklist from self.playlists."""
        # Clear existing checkboxes (leave the stretch at end)
        while self._pl_list_layout.count() > 1:
            item = self._pl_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._pl_checkboxes: list[QCheckBox] = []
        for pl in self.playlists:
            cb = QCheckBox(f"{pl['name']}  ({len(pl['track_ids'])})")
            cb.setChecked(False)
            cb.setStyleSheet(f"color: {DARK_PALETTE['text_mid']}; font-size: 12px;")
            cb.stateChanged.connect(self._on_playlist_selection_changed)
            self._pl_list_layout.insertWidget(
                self._pl_list_layout.count() - 1, cb  # insert before stretch
            )
            self._pl_checkboxes.append(cb)

        self._pl_count_lbl.setText(f"{len(self.playlists)}")
        self._playlist_panel.setVisible(True)
        self._on_playlist_selection_changed()

    def _select_all_playlists(self):
        for cb in self._pl_checkboxes:
            cb.setChecked(True)

    def _select_no_playlists(self):
        for cb in self._pl_checkboxes:
            cb.setChecked(False)

    def _on_playlist_selection_changed(self):
        selected = self._selected_playlist_names()
        if not selected:
            self._pl_mode_lbl.setText("▸ All tracks (no playlist selected)")
            self._pl_mode_lbl.setStyleSheet(
                f"color: {DARK_PALETTE['accent_glow']}; font-size: 11px; font-style: italic;"
            )
            display = [t for t in self.itunes_tracks if t["stars"] > 0] or self.itunes_tracks[:200]
        else:
            track_ids = self._selected_track_ids()
            filtered = [t for t in self.itunes_tracks if t["track_id"] in track_ids]
            rated_count = sum(1 for t in filtered if t["stars"] > 0)
            self._pl_mode_lbl.setText(
                f"▸ {len(selected)} playlist{'s' if len(selected) != 1 else ''} · "
                f"{len(filtered)} tracks · {rated_count} rated"
            )
            self._pl_mode_lbl.setStyleSheet(
                f"color: {DARK_PALETTE['success']}; font-size: 11px; font-style: italic;"
            )
            display = [t for t in filtered if t["stars"] > 0] or filtered[:200]
        self._populate_preview(display)

    def _selected_playlist_names(self) -> list[str]:
        return [
            self.playlists[i]["name"]
            for i, cb in enumerate(self._pl_checkboxes)
            if cb.isChecked()
        ]

    def _selected_track_ids(self) -> set[int]:
        """Union of track IDs across all checked playlists."""
        ids: set[int] = set()
        for i, cb in enumerate(self._pl_checkboxes):
            if cb.isChecked():
                ids |= self.playlists[i]["track_ids"]
        return ids

    def _filtered_tracks(self) -> list[dict]:
        """Tracks to match: playlist-filtered if any selected, else all tracks."""
        selected_ids = self._selected_track_ids()
        if not selected_ids:
            return self.itunes_tracks
        return [t for t in self.itunes_tracks if t["track_id"] in selected_ids]

    # ── Existing methods (unchanged except _load_xml and _start_match) ──

    def update_settings(self, settings: dict):
        self.settings = settings

    def _browse_xml(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open iTunes Library XML",
            str(Path.home() / "Music"),
            "iTunes Library XML (*.xml);;All Files (*)"
        )
        if path:
            self.xml_path_edit.setText(path)
            self.settings["xml_path"] = path

    def _load_xml(self):
        path = self.xml_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No File", "Please select an iTunes XML file first.")
            return
        try:
            self.itunes_tracks, self.playlists = parse_itunes_xml(path)
            rated = [t for t in self.itunes_tracks if t["stars"] > 0]

            self._stat_total.setText(str(len(self.itunes_tracks)))
            self._stat_rated.setText(str(len(rated)))
            self._stat_match.setText("—")
            self._stat_unmatch.setText("—")
            self.match_status.setText(
                f"Loaded {len(self.itunes_tracks)} tracks "
                f"({len(rated)} rated). Select playlists or match all."
            )
            self.match_status.setStyleSheet(f"color: {DARK_PALETTE['success']};")

            self._populate_playlist_panel()
            self.match_btn.setEnabled(True)
            self.settings["xml_path"] = path
            save_settings(self.settings)

        except Exception as e:
            QMessageBox.critical(self, "Parse Error", f"Failed to parse iTunes XML:\n{e}")

    def _populate_preview(self, tracks: list[dict]):
        self.preview_table.setRowCount(0)
        for t in tracks:
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)
            for col, val in enumerate([
                t["artist"], t["title"], t["album"],
                stars_widget(t["stars"]),
                str(t["rating_raw"]),
            ]):
                item = QTableWidgetItem(val)
                if col == 3:
                    item.setForeground(QColor(DARK_PALETTE["star"]))
                self.preview_table.setItem(row, col, item)

    def _start_match(self):
        tracks_to_match = self._filtered_tracks()
        if not tracks_to_match:
            QMessageBox.warning(self, "Nothing to Match",
                                "No tracks in the selected playlists.")
            return
        s = self.settings.copy()
        if not s.get("plex_token"):
            QMessageBox.warning(self, "No Token",
                                "Please configure your Plex token in Settings first.")
            return

        selected = self._selected_playlist_names()
        if selected:
            self.log_msg.emit(
                f"Matching {len(tracks_to_match)} tracks from "
                f"{len(selected)} playlist(s): {', '.join(selected)}"
            )
        else:
            self.log_msg.emit(f"Matching all {len(tracks_to_match)} tracks…")

        self.match_btn.setEnabled(False)
        self.match_progress.setVisible(True)
        self.match_progress.setValue(0)
        self.cancel_btn.setVisible(True)
        self.match_status.setText("Matching tracks…")
        self.match_status.setStyleSheet(f"color: {DARK_PALETTE['text_dim']};")

        self.worker = MatchWorker(s, tracks_to_match)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_match_done)
        self.worker.log.connect(self.log_msg)
        self.worker.error.connect(self._on_match_error)
        self.worker.start()

    def _cancel_match(self):
        if self.worker:
            self.worker.quit()
        self._reset_match_ui()

    def _on_progress(self, cur, total):
        self.match_progress.setMaximum(total)
        self.match_progress.setValue(cur)
        self.match_status.setText(f"Matching {cur}/{total}…")

    def _on_match_done(self, matched: list, unmatched: list):
        self._reset_match_ui()
        self._stat_match.setText(str(len(matched)))
        self._stat_unmatch.setText(str(len(unmatched)))
        self.match_status.setText(
            f"Matching complete: {len(matched)} matched, {len(unmatched)} unmatched."
        )
        self.match_status.setStyleSheet(f"color: {DARK_PALETTE['success']};")
        self.match_ready.emit(matched, unmatched)

    def _on_match_error(self, msg: str):
        self._reset_match_ui()
        self.match_status.setText(f"Error: {msg}")
        self.match_status.setStyleSheet(f"color: {DARK_PALETTE['error']};")
        QMessageBox.critical(self, "Match Error", msg)

    def _reset_match_ui(self):
        self.match_progress.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.match_btn.setEnabled(True)


# ──────────────────────────────────────────────────────────────
# Unmatched Tab
# ──────────────────────────────────────────────────────────────

class UnmatchedTab(QWidget):
    def __init__(self):
        super().__init__()
        self._unmatched: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(20)

        outer.addWidget(make_label("Unmatched Tracks", "heading"))
        self._subtitle = QLabel("Tracks from iTunes that could not be matched in your Plex library")
        self._subtitle.setObjectName("subheading")
        outer.addWidget(self._subtitle)
        outer.addWidget(hsep())

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["iTunes Artist", "iTunes Title", "iTunes Album", "Stars",
             "Best Plex Match", "Score"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        outer.addWidget(self.table, stretch=1)

        export_btn = QPushButton("Export Unmatched to CSV")
        export_btn.clicked.connect(self._export_csv)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(export_btn)
        outer.addLayout(row)

    def load(self, unmatched: list[dict]):
        self._unmatched = unmatched
        self.table.setRowCount(0)
        self._subtitle.setText(
            f"{len(unmatched)} tracks from iTunes could not be matched in your Plex library"
        )
        for u in unmatched:
            it = u["itunes_track"]
            bp = u.get("best_plex")
            score = u.get("score", 0)
            r = self.table.rowCount()
            self.table.insertRow(r)
            best_str = ""
            if bp:
                best_str = f"{bp.get('grandparentTitle','')} — {bp.get('title','')}"
            score_item = QTableWidgetItem(f"{score}%")
            if score >= 70:
                score_item.setForeground(QColor(DARK_PALETTE["warning"]))
            else:
                score_item.setForeground(QColor(DARK_PALETTE["error"]))
            for col, val in enumerate([
                it["artist"], it["title"], it["album"],
                stars_widget(it["stars"]), best_str,
            ]):
                item = QTableWidgetItem(val)
                if col == 3:
                    item.setForeground(QColor(DARK_PALETTE["star"]))
                self.table.setItem(r, col, item)
            self.table.setItem(r, 5, score_item)

    def _export_csv(self):
        if not self._unmatched:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Unmatched", str(Path.home() / "unmatched_tracks.csv"),
            "CSV Files (*.csv)"
        )
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Artist", "Title", "Album", "Stars", "Best Plex Match", "Score"])
            for u in self._unmatched:
                it = u["itunes_track"]
                bp = u.get("best_plex")
                score = u.get("score", 0)
                best_str = ""
                if bp:
                    best_str = f"{bp.get('grandparentTitle','')} — {bp.get('title','')}"
                writer.writerow([it["artist"], it["title"], it["album"],
                                 it["stars"], best_str, f"{score}%"])
        QMessageBox.information(self, "Exported", f"Saved to:\n{path}")


# ──────────────────────────────────────────────────────────────
# Transfer Tab
# ──────────────────────────────────────────────────────────────

class TransferTab(QWidget):
    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.matched: list[dict] = []
        self.worker: Optional[TransferWorker] = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(20)

        outer.addWidget(make_label("Transfer Ratings", "heading"))
        self._subtitle = QLabel("Review matched tracks and transfer ratings to Plex")
        self._subtitle.setObjectName("subheading")
        outer.addWidget(self._subtitle)
        outer.addWidget(hsep())

        # Matched tracks table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["iTunes Artist", "iTunes Title", "Plex Title", "Stars", "Match", "Status"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        outer.addWidget(self.table, stretch=1)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(f"color: {DARK_PALETTE['text_dim']};")
        outer.addWidget(self.progress_bar)
        outer.addWidget(self.progress_label)

        # Log
        log_group = QGroupBox("Transfer Log")
        lg = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(160)
        lg.addWidget(self.log_view)
        outer.addWidget(log_group)

        # Buttons
        btn_row = QHBoxLayout()
        self.transfer_btn = QPushButton("Transfer Ratings to Plex")
        self.transfer_btn.setObjectName("primary")
        self.transfer_btn.setEnabled(False)
        self.transfer_btn.clicked.connect(self._start_transfer)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("danger")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel)

        btn_row.addStretch()
        btn_row.addWidget(self.transfer_btn)
        btn_row.addWidget(self.cancel_btn)
        outer.addLayout(btn_row)

    def load_matched(self, matched: list[dict]):
        self.matched = matched
        self.table.setRowCount(0)
        self._subtitle.setText(
            f"{len(matched)} tracks ready to transfer. "
            f"{'[DRY RUN MODE] ' if self.settings.get('dry_run') else ''}"
            f"Check settings before proceeding."
        )
        for pair in matched:
            it = pair["itunes_track"]
            px = pair["plex_track"]
            method = pair.get("method", "fuzzy")
            r = self.table.rowCount()
            self.table.insertRow(r)
            plex_title = f"{px.get('grandparentTitle','')} — {px.get('title','')}"

            method_labels = {
                "path":       "📁 Path",
                "text-exact": "🔤 Exact",
                "fuzzy":      f"~ Fuzzy",
            }
            method_colors = {
                "path":       DARK_PALETTE["success"],
                "text-exact": DARK_PALETTE["accent_glow"],
                "fuzzy":      DARK_PALETTE["warning"],
            }

            for col, val in enumerate([
                it["artist"], it["title"], plex_title,
                stars_widget(it["stars"]),
                method_labels.get(method, method),
                "Pending",
            ]):
                item = QTableWidgetItem(val)
                if col == 3:
                    item.setForeground(QColor(DARK_PALETTE["star"]))
                if col == 4:
                    item.setForeground(QColor(method_colors.get(method, DARK_PALETTE["text_dim"])))
                if col == 5:
                    item.setForeground(QColor(DARK_PALETTE["text_dim"]))
                self.table.setItem(r, col, item)
        self.transfer_btn.setEnabled(len(matched) > 0)
        self.log_view.clear()

    def update_settings(self, settings: dict):
        self.settings = settings

    def append_log(self, msg: str):
        self.log_view.append(msg)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def _start_transfer(self):
        dry = self.settings.get("dry_run", False)
        confirm = QMessageBox.question(
            self,
            "Confirm Transfer",
            f"{'[DRY RUN] ' if dry else ''}Transfer ratings for "
            f"{len(self.matched)} tracks to Plex?\n\n"
            f"Server: {self.settings.get('plex_url', '')}\n"
            f"Library: {self.settings.get('plex_library', '')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.transfer_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.matched))

        # Reset status column (col 5)
        for row in range(self.table.rowCount()):
            item = QTableWidgetItem("Pending")
            item.setForeground(QColor(DARK_PALETTE["text_dim"]))
            self.table.setItem(row, 5, item)

        self.worker = TransferWorker(self.settings, self.matched)
        self.worker.progress.connect(self._on_progress)
        self.worker.track_done.connect(self._on_track_done)
        self.worker.finished.connect(self._on_finished)
        self.worker.log.connect(self.append_log)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
        self.cancel_btn.setVisible(False)

    def _on_progress(self, cur, total):
        self.progress_bar.setValue(cur)
        self.progress_label.setText(f"Processing {cur}/{total}…")

    def _on_track_done(self, result: dict):
        row = self.progress_bar.value() - 1
        if row < 0 or row >= self.table.rowCount():
            return
        status = result["status"]
        colors = {
            "ok":      DARK_PALETTE["success"],
            "dry_run": DARK_PALETTE["accent"],
            "skipped": DARK_PALETTE["warning"],
            "failed":  DARK_PALETTE["error"],
        }
        labels = {
            "ok": "✓ Done", "dry_run": "~ Dry run",
            "skipped": "↷ Skipped", "failed": "✗ Failed",
        }
        item = QTableWidgetItem(labels.get(status, status))
        item.setForeground(QColor(colors.get(status, DARK_PALETTE["text_mid"])))
        self.table.setItem(row, 5, item)

    def _on_finished(self, summary: dict):
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.transfer_btn.setEnabled(True)
        msg = (
            f"Transfer complete!\n\n"
            f"✓ Success:  {summary['ok']}\n"
            f"↷ Skipped:  {summary['skipped']}\n"
            f"✗ Failed:   {summary['failed']}\n"
            f"Total:      {summary['total']}"
        )
        self.progress_label.setText(
            f"Done — {summary['ok']} transferred, "
            f"{summary['skipped']} skipped, {summary['failed']} failed."
        )
        QMessageBox.information(self, "Transfer Complete", msg)

    def _on_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.transfer_btn.setEnabled(True)
        QMessageBox.critical(self, "Transfer Error", msg)


# ──────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 780)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header bar ──
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(
            f"background-color: {DARK_PALETTE['bg_card']}; "
            f"border-bottom: 1px solid {DARK_PALETTE['border']};"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)

        logo = QLabel("♫")
        logo.setStyleSheet(f"font-size: 22px; color: {DARK_PALETTE['accent_glow']};")
        title = QLabel(APP_NAME)
        title.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {DARK_PALETTE['text_hi']}; "
            f"letter-spacing: -0.3px;"
        )
        version = QLabel(f"v{APP_VERSION}")
        version.setStyleSheet(
            f"font-size: 11px; color: {DARK_PALETTE['text_dim']}; "
            f"background: {DARK_PALETTE['bg_input']}; "
            f"padding: 2px 8px; border-radius: 10px; "
            f"border: 1px solid {DARK_PALETTE['border']};"
        )
        hl.addWidget(logo)
        hl.addWidget(title)
        hl.addWidget(version)
        hl.addStretch()

        dry_badge = QLabel()
        self._dry_badge = dry_badge
        hl.addWidget(dry_badge)
        self._update_dry_badge()

        layout.addWidget(header)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.main_tab     = MainTab(self.settings)
        self.unmatched_tab = UnmatchedTab()
        self.transfer_tab  = TransferTab(self.settings)
        self.settings_tab  = SettingsTab(self.settings)

        self.tabs.addTab(self.main_tab,      "  Import & Match  ")
        self.tabs.addTab(self.unmatched_tab, "  Unmatched  ")
        self.tabs.addTab(self.transfer_tab,  "  Transfer  ")
        self.tabs.addTab(self.settings_tab,  "  Settings  ")

        layout.addWidget(self.tabs, stretch=1)

        # ── Status bar ──
        status = QStatusBar()
        self.setStatusBar(status)
        self._status_label = QLabel("Ready  —  Load an iTunes XML to begin")
        status.addWidget(self._status_label)
        self._settings_file_label = QLabel(f"Settings: {SETTINGS_FILE}")
        self._settings_file_label.setStyleSheet(f"color: {DARK_PALETTE['text_dim']};")
        status.addPermanentWidget(self._settings_file_label)

        # ── Signals ──
        self.main_tab.match_ready.connect(self._on_match_ready)
        self.main_tab.log_msg.connect(self._on_log)
        self.settings_tab.settings_saved.connect(self._on_settings_saved)

    def _update_dry_badge(self):
        if self.settings.get("dry_run"):
            self._dry_badge.setText("DRY RUN")
            self._dry_badge.setStyleSheet(
                f"color: {DARK_PALETTE['warning']}; "
                f"background: rgba(251,191,36,0.12); "
                f"font-size: 11px; font-weight: 700; letter-spacing: 1px; "
                f"padding: 3px 10px; border-radius: 10px; "
                f"border: 1px solid {DARK_PALETTE['warning']};"
            )
        else:
            self._dry_badge.setText("")
            self._dry_badge.setStyleSheet("")

    def _on_match_ready(self, matched: list, unmatched: list):
        self.unmatched_tab.load(unmatched)
        self.transfer_tab.load_matched(matched)
        self._status_label.setText(
            f"{len(matched)} tracks matched  ·  "
            f"{len(unmatched)} unmatched  —  Go to Transfer to apply ratings"
        )
        # Switch to transfer tab
        self.tabs.setCurrentIndex(2)

    def _on_log(self, msg: str):
        self._status_label.setText(msg)

    def _on_settings_saved(self, settings: dict):
        self.settings = settings
        self.main_tab.update_settings(settings)
        self.transfer_tab.update_settings(settings)
        self._update_dry_badge()


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(STYLESHEET)

    # Force dark palette at OS level too
    palette = QPalette()
    bg = QColor(DARK_PALETTE["bg_deep"])
    palette.setColor(QPalette.ColorRole.Window,          bg)
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(DARK_PALETTE["text_hi"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(DARK_PALETTE["bg_input"]))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(DARK_PALETTE["bg_card"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     bg)
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(DARK_PALETTE["text_hi"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(DARK_PALETTE["text_hi"]))
    palette.setColor(QPalette.ColorRole.Button,          QColor(DARK_PALETTE["bg_card"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(DARK_PALETTE["text_mid"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(DARK_PALETTE["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
