"""
Practice session window with image viewer and timer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QProgressBar,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QFont, QKeySequence, QShortcut

from services.image_cache import image_cache


class ImageLoader(QThread):
    """Background thread for loading images."""

    # Use QImage instead of QPixmap for thread safety (QPixmap must be created in main thread)
    image_loaded = Signal(QImage)
    error = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            print(f"[IMAGE_LOADER] Downloading: {self.url}")
            path = image_cache.download(self.url)
            print(f"[IMAGE_LOADER] Path: {path}, exists: {path.exists() if hasattr(path, 'exists') else 'N/A'}")
            # Load as QImage (thread-safe) instead of QPixmap
            image = QImage(str(path))
            print(f"[IMAGE_LOADER] QImage isNull: {image.isNull()}, size: {image.size()}")
            if not image.isNull():
                self.image_loaded.emit(image)
            else:
                self.error.emit("Failed to load image")
        except Exception as e:
            print(f"[IMAGE_LOADER] Error: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class TimerWidget(QFrame):
    """Timer display widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.7); border-radius: 10px;"
        )

        layout = QVBoxLayout(self)

        self.time_label = QLabel("0:00")
        self.time_label.setFont(QFont("Arial", 48, QFont.Bold))
        self.time_label.setStyleSheet("color: white;")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            """
            QProgressBar {
                border: none;
                background-color: #333;
                height: 8px;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
            """
        )
        layout.addWidget(self.progress)

    def set_time(self, seconds: int, total: int):
        minutes = seconds // 60
        secs = seconds % 60
        self.time_label.setText(f"{minutes}:{secs:02d}")

        if total > 0:
            self.progress.setValue(int((seconds / total) * 100))

        if seconds <= 10:
            self.time_label.setStyleSheet("color: #FF5722;")
        elif seconds <= 30:
            self.time_label.setStyleSheet("color: #FFC107;")
        else:
            self.time_label.setStyleSheet("color: white;")


class PracticeSessionWindow(QMainWindow):
    """Full practice session window with image display and timer."""

    def __init__(
        self,
        photos: list,
        duration_seconds: int,
        play_sound: bool = True,
        tips: dict = None,
        parent=None,
    ):
        super().__init__(parent)
        self.photos = photos
        self.duration_seconds = duration_seconds
        self.play_sound = play_sound
        self.tips = tips or {}

        self.current_index = 0
        self.time_remaining = duration_seconds
        self.is_paused = False

        self.setWindowTitle("Practice Session")
        self.setMinimumSize(1024, 768)

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_timer()

        self._load_current_image()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.image_container = QWidget()
        self.image_container.setStyleSheet("background-color: #1a1a1a;")
        image_layout = QVBoxLayout(self.image_container)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1a1a1a;")
        image_layout.addWidget(self.image_label, 1)

        layout.addWidget(self.image_container, 1)

        overlay_container = QWidget(self.image_container)
        overlay_container.setAttribute(Qt.WA_TranslucentBackground)
        overlay_layout = QVBoxLayout(overlay_container)
        overlay_layout.setContentsMargins(20, 20, 20, 20)

        top_bar = QHBoxLayout()

        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(
            "color: white; background-color: rgba(0,0,0,0.5); "
            "padding: 5px 15px; border-radius: 5px; font-size: 14px;"
        )
        top_bar.addWidget(self.counter_label)

        top_bar.addStretch()

        self.timer_widget = TimerWidget()
        self.timer_widget.setFixedSize(200, 100)
        top_bar.addWidget(self.timer_widget)

        overlay_layout.addLayout(top_bar)
        overlay_layout.addStretch()

        controls = QFrame()
        controls.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.7); border-radius: 10px;"
        )
        controls_layout = QHBoxLayout(controls)

        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self._prev_image)
        self.prev_btn.setStyleSheet(self._button_style())
        controls_layout.addWidget(self.prev_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.pause_btn.setStyleSheet(self._button_style())
        controls_layout.addWidget(self.pause_btn)

        self.next_btn = QPushButton("Skip")
        self.next_btn.clicked.connect(self._next_image)
        self.next_btn.setStyleSheet(self._button_style())
        controls_layout.addWidget(self.next_btn)

        controls_layout.addStretch()

        self.end_btn = QPushButton("End Session")
        self.end_btn.clicked.connect(self._end_session)
        self.end_btn.setStyleSheet(self._button_style("#f44336"))
        controls_layout.addWidget(self.end_btn)

        overlay_layout.addWidget(controls)

        credit_frame = QFrame()
        credit_frame.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.5); border-radius: 5px;"
        )
        credit_layout = QHBoxLayout(credit_frame)
        credit_layout.setContentsMargins(10, 5, 10, 5)

        self.credit_label = QLabel()
        self.credit_label.setStyleSheet("color: white; font-size: 12px;")
        credit_layout.addWidget(self.credit_label)

        overlay_layout.addWidget(credit_frame)

        overlay_container.setGeometry(0, 0, self.width(), self.height())
        self.overlay = overlay_container

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "overlay"):
            self.overlay.setGeometry(0, 0, self.width(), self.height())
        self._scale_current_image()

    def _button_style(self, color: str = "#4CAF50") -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
            }}
        """

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Space), self, self._toggle_pause)
        QShortcut(QKeySequence(Qt.Key_Right), self, self._next_image)
        QShortcut(QKeySequence(Qt.Key_Left), self, self._prev_image)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._end_session)

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        if self.is_paused:
            return

        self.time_remaining -= 1
        self.timer_widget.set_time(self.time_remaining, self.duration_seconds)

        if self.time_remaining <= 0:
            self._on_timer_end()

    def _on_timer_end(self):
        if self.play_sound:
            try:
                from PySide6.QtMultimedia import QSoundEffect
            except ImportError:
                pass

        if self.current_index < len(self.photos) - 1:
            self._next_image()
        else:
            self._session_complete()

    def _load_current_image(self):
        if self.current_index >= len(self.photos):
            return

        photo = self.photos[self.current_index]
        self.counter_label.setText(
            f"Image {self.current_index + 1} of {len(self.photos)}"
        )

        photographer = photo.get("photographer", "Unknown")
        self.credit_label.setText(f"Photo by {photographer} on Pexels")

        url = photo.get("url")
        if url:
            self.image_label.setText("Loading...")
            # Stop any previous loader before starting a new one
            if hasattr(self, "loader") and self.loader and self.loader.isRunning():
                self.loader.requestInterruption()
                self.loader.wait()
            self.loader = ImageLoader(url)
            self.loader.image_loaded.connect(self._on_image_loaded)
            self.loader.error.connect(self._on_image_error)
            self.loader.start()

    def _on_image_loaded(self, image: QImage):
        print(f"[IMAGE] _on_image_loaded called, image size: {image.size()}")
        # Convert QImage to QPixmap in the main thread (thread-safe)
        self.current_pixmap = QPixmap.fromImage(image)
        print(f"[IMAGE] Pixmap created, isNull: {self.current_pixmap.isNull()}")
        self._scale_current_image()

    def _scale_current_image(self):
        if not hasattr(self, "current_pixmap") or self.current_pixmap.isNull():
            print("[IMAGE] _scale_current_image: no valid pixmap")
            return

        available_size = self.image_label.size()
        print(f"[IMAGE] Scaling to: {available_size}")
        scaled = self.current_pixmap.scaled(
            available_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        print(f"[IMAGE] Setting pixmap, scaled size: {scaled.size()}")
        self.image_label.setPixmap(scaled)

    def _on_image_error(self, error: str):
        self.image_label.setText(f"Failed to load image: {error}")

    def _next_image(self):
        if self.current_index < len(self.photos) - 1:
            self.current_index += 1
            self.time_remaining = self.duration_seconds
            self.timer_widget.set_time(self.time_remaining, self.duration_seconds)
            self._load_current_image()
        else:
            self._session_complete()

    def _prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.time_remaining = self.duration_seconds
            self.timer_widget.set_time(self.time_remaining, self.duration_seconds)
            self._load_current_image()

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        self.pause_btn.setText("Resume" if self.is_paused else "Pause")

    def _end_session(self):
        reply = QMessageBox.question(
            self,
            "End Session",
            "Are you sure you want to end the practice session?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.timer.stop()
            if hasattr(self, "loader") and self.loader and self.loader.isRunning():
                self.loader.requestInterruption()
                self.loader.wait()
            self.close()

    def _session_complete(self):
        self.timer.stop()
        if hasattr(self, "loader") and self.loader and self.loader.isRunning():
            self.loader.requestInterruption()
            self.loader.wait()
        QMessageBox.information(
            self,
            "Session Complete",
            f"Great work! You completed {len(self.photos)} reference drawings.\n\n"
            "Keep practicing to improve your skills!",
        )
        self.close()

    def closeEvent(self, event):
        # Stop timer first
        if hasattr(self, "timer"):
            self.timer.stop()

        # Stop any running image loader with timeout
        if hasattr(self, "loader") and self.loader and self.loader.isRunning():
            self.loader.requestInterruption()
            self.loader.wait(5000)  # 5 second timeout to prevent infinite wait

        super().closeEvent(event)
