"""
Session setup dialog for configuring practice sessions.

Supports random image selection to avoid repetition.
"""

import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QComboBox,
    QScrollArea,
    QWidget,
    QGridLayout,
    QFrame,
    QCheckBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QFont

from services.image_cache import image_cache
from services.session_store import session_store


class ThumbnailLoader(QThread):
    """Background thread for loading thumbnails."""

    thumbnail_loaded = Signal(int, QPixmap)
    finished_loading = Signal()

    def __init__(self, photos: list):
        super().__init__()
        self.photos = photos

    def run(self):
        for i, photo in enumerate(self.photos):
            if self.isInterruptionRequested():
                break
            try:
                # Use thumbnail if available, fallback to main url (for Pinterest local paths)
                thumbnail_url = photo.get("thumbnail") or photo.get("url")
                if thumbnail_url:
                    path = image_cache.download(thumbnail_url)
                    pixmap = QPixmap(str(path))
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(
                            150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                        self.thumbnail_loaded.emit(i, scaled)
                    else:
                        print(f"[THUMBNAIL] Pixmap is null for {thumbnail_url}")
            except Exception as e:
                print(f"[THUMBNAIL] Failed to load thumbnail {i}: {e}")
                import traceback
                traceback.print_exc()

        self.finished_loading.emit()


class SessionSetupDialog(QDialog):
    """Dialog for configuring the practice session."""

    # Signal emitted when session is configured, passing: photos, duration, play_sound, tips, theme
    session_configured = Signal(list, int, bool, dict, str)

    def __init__(self, photos: list, tips: dict, theme: str = "", parent=None):
        super().__init__(parent)
        self.photos = photos
        self.tips = tips
        self.theme = theme
        self.selected_photos = list(range(len(photos)))
        self.thumbnail_labels = []

        self.setWindowTitle("Setup Practice Session")
        self.setMinimumSize(700, 500)

        self._setup_ui()
        self._load_thumbnails()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Configure Your Practice Session")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        timer_frame = QFrame()
        timer_layout = QHBoxLayout(timer_frame)

        timer_layout.addWidget(QLabel("Time per image:"))

        self.timer_combo = QComboBox()
        self.timer_combo.addItems(["30 seconds", "1 minute", "2 minutes", "5 minutes", "10 minutes", "Custom"])
        self.timer_combo.setCurrentIndex(1)
        self.timer_combo.currentTextChanged.connect(self._on_timer_changed)
        timer_layout.addWidget(self.timer_combo)

        self.custom_timer = QSpinBox()
        self.custom_timer.setRange(10, 3600)
        self.custom_timer.setValue(60)
        self.custom_timer.setSuffix(" seconds")
        self.custom_timer.setVisible(False)
        timer_layout.addWidget(self.custom_timer)

        timer_layout.addStretch()

        timer_layout.addWidget(QLabel("Number of images:"))
        self.image_count = QSpinBox()
        self.image_count.setRange(1, len(self.photos))
        self.image_count.setValue(min(10, len(self.photos)))
        timer_layout.addWidget(self.image_count)

        layout.addWidget(timer_frame)

        photos_label = QLabel(f"Reference Photos ({len(self.photos)} available):")
        photos_label.setFont(QFont("Arial", 13, QFont.Bold))
        layout.addWidget(photos_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        self.photos_grid = QGridLayout(scroll_content)
        self.photos_grid.setSpacing(10)

        for i, photo in enumerate(self.photos):
            frame = QFrame()
            frame.setFrameStyle(QFrame.Box)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(5, 5, 5, 5)

            thumb_label = QLabel()
            thumb_label.setFixedSize(150, 150)
            thumb_label.setAlignment(Qt.AlignCenter)
            thumb_label.setText("Loading...")
            thumb_label.setStyleSheet("background-color: #f0f0f0;")
            frame_layout.addWidget(thumb_label)
            self.thumbnail_labels.append(thumb_label)

            photographer = photo.get("photographer", "Unknown")
            credit = QLabel(f"by {photographer[:20]}")
            credit.setAlignment(Qt.AlignCenter)
            credit.setStyleSheet("font-size: 10px; color: #666;")
            frame_layout.addWidget(credit)

            row = i // 4
            col = i % 4
            self.photos_grid.addWidget(frame, row, col)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        options_layout = QHBoxLayout()

        self.shuffle_check = QCheckBox("Shuffle order")
        self.shuffle_check.setChecked(True)
        options_layout.addWidget(self.shuffle_check)

        self.sound_check = QCheckBox("Play sound on timer end")
        self.sound_check.setChecked(True)
        options_layout.addWidget(self.sound_check)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        button_layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()

        self.start_btn = QPushButton("Start Practice Session")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setDefault(True)
        self.start_btn.clicked.connect(self._start_session)
        button_layout.addWidget(self.start_btn)

        layout.addLayout(button_layout)

    def _on_timer_changed(self, text: str):
        self.custom_timer.setVisible(text == "Custom")

    def _get_duration_seconds(self) -> int:
        text = self.timer_combo.currentText()
        durations = {
            "30 seconds": 30,
            "1 minute": 60,
            "2 minutes": 120,
            "5 minutes": 300,
            "10 minutes": 600,
        }
        if text in durations:
            return durations[text]
        return self.custom_timer.value()

    def _load_thumbnails(self):
        self.loader = ThumbnailLoader(self.photos)
        self.loader.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        self.loader.start()

    def _on_thumbnail_loaded(self, index: int, pixmap: QPixmap):
        if 0 <= index < len(self.thumbnail_labels):
            self.thumbnail_labels[index].setPixmap(pixmap)

    def _start_session(self):
        photo_count = self.image_count.value()

        # Get recently used images to prefer fresh ones
        try:
            recently_used = session_store.get_images_shown_recently(days=3)
        except Exception:
            recently_used = set()

        # Separate fresh and recently used photos
        fresh_photos = []
        used_photos = []
        for photo in self.photos:
            pexels_id = photo.get('id') or photo.get('pexels_id')
            if pexels_id and pexels_id in recently_used:
                used_photos.append(photo)
            else:
                fresh_photos.append(photo)

        # Prioritize fresh photos, fill remainder with used if needed
        if len(fresh_photos) >= photo_count:
            if self.shuffle_check.isChecked():
                photos_to_use = random.sample(fresh_photos, photo_count)
            else:
                photos_to_use = fresh_photos[:photo_count]
        else:
            # Use all fresh photos + some used ones
            photos_to_use = fresh_photos.copy()
            remaining = photo_count - len(photos_to_use)
            if remaining > 0 and used_photos:
                if self.shuffle_check.isChecked():
                    extra = random.sample(used_photos, min(remaining, len(used_photos)))
                else:
                    extra = used_photos[:remaining]
                photos_to_use.extend(extra)

            # Shuffle the final selection
            if self.shuffle_check.isChecked():
                random.shuffle(photos_to_use)

        duration = self._get_duration_seconds()
        play_sound = self.sound_check.isChecked()

        # Ensure thumbnail loader is stopped before closing dialog
        if hasattr(self, "loader") and self.loader and self.loader.isRunning():
            self.loader.requestInterruption()
            self.loader.wait()

        # Emit configuration signal - MainWindow will create the session window
        self.session_configured.emit(photos_to_use, duration, play_sound, self.tips, self.theme)
        self.accept()

    def closeEvent(self, event):
        # Stop loader thread cleanly when dialog closes
        if hasattr(self, "loader") and self.loader and self.loader.isRunning():
            self.loader.requestInterruption()
            self.loader.wait()
        super().closeEvent(event)
