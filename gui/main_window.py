"""
Main application window for the Art Practice Assistant.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QSplitter,
    QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from services.pexels_client import pexels_client
from gui.session_setup import SessionSetupDialog
from gui.image_viewer import PracticeSessionWindow
from agent.practice_agent import practice_agent


class PexelsWorker(QThread):
    """Background thread for Pexels API calls (testing mode)."""

    response_ready = Signal(str)
    photos_ready = Signal(list)
    error = Signal(str)
    no_photos = Signal()

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        try:
            print(f"[PEXELS] Searching for: {self.query}")
            photos = pexels_client.search_photos(query=self.query, per_page=10)
            print(f"[PEXELS] API returned {len(photos)} photos")

            if photos:
                photo_list = [
                    {
                        "id": photo.id,
                        "url": photo.src_large,
                        "thumbnail": photo.src_medium,
                        "photographer": photo.photographer,
                        "alt": photo.alt,
                    }
                    for photo in photos
                ]
                self.response_ready.emit(f"Found {len(photo_list)} reference photos for '{self.query}'")
                self.photos_ready.emit(photo_list)
            else:
                self.response_ready.emit(f"No photos found for '{self.query}'")
                self.no_photos.emit()

        except Exception as e:
            print(f"[PEXELS] Error: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class AgentWorker(QThread):
    """Background thread for AI agent processing."""

    response_ready = Signal(str)
    photos_ready = Signal(list)
    tips_ready = Signal(dict)
    error = Signal(str)
    no_photos = Signal()

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def run(self):
        try:
            print(f"[AGENT] Processing: {self.message}")

            # Run the Agno agent with the user's message
            response = practice_agent.run(self.message)

            print(f"[AGENT] Response received")
            # Emit text response
            content = response.content if response.content else ""
            print(f"[AGENT] Response content: {content}")
            self.response_ready.emit(str(content))
            print(f"[AGENT] Extracting tools results")

            # Extract tool results from the response
            photos = []
            tips = {}

            if response.tools:
                print(f"[AGENT] Found {len(response.tools)} tool executions")
                for tool_exec in response.tools:
                    tool_name = getattr(tool_exec, 'tool_name', None) or getattr(tool_exec, 'name', None)
                    result_str = getattr(tool_exec, 'result', None) or getattr(tool_exec, 'content', None)

                    if result_str:
                        try:
                            if isinstance(result_str, str):
                                # Agno returns Python repr strings, not JSON
                                result = ast.literal_eval(result_str)
                            else:
                                result = result_str
                        except (ValueError, SyntaxError):
                            # Fallback to JSON parsing
                            try:
                                result = json.loads(result_str)
                            except (json.JSONDecodeError, TypeError):
                                print(f"[AGENT] Failed to parse tool result for {tool_name}")
                                result = result_str

                        if tool_name == "search_reference_photos" and isinstance(result, list):
                            photos = result
                        elif tool_name == "get_practice_tips" and isinstance(result, dict):
                            tips = result

            # Emit tips if found
            if tips:
                print(f"[AGENT] Extracted practice tips: {tips}")
                self.tips_ready.emit(tips)

            # Emit photos or no_photos signal
            if photos:
                self.photos_ready.emit(photos)
            else:
                self.no_photos.emit()

        except Exception as e:
            print(f"[AGENT] Agent has Error: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Timed Reference - Art Practice Assistant")
        self.setMinimumSize(900, 600)

        self.current_photos = []
        self.current_tips = {}

        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header = QLabel("Timed Reference - Art Practice")
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)

        chat_label = QLabel("Chat with your practice assistant:")
        left_layout.addWidget(chat_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText(
            "Tell me what you want to practice today!\n\n"
            "Examples:\n"
            "- I want to practice drawing hands\n"
            "- Help me with gesture drawing\n"
            "- I need vehicle references for sketching"
        )
        left_layout.addWidget(self.chat_display, 1)

        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.message_input, 1)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._send_message)
        input_layout.addWidget(self.send_button)

        left_layout.addLayout(input_layout)
        splitter.addWidget(left_panel)

        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        tips_label = QLabel("Practice Tips:")
        tips_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(tips_label)

        self.tips_display = QTextEdit()
        self.tips_display.setReadOnly(True)
        self.tips_display.setPlaceholderText("Tips will appear here after you describe what you want to practice.")
        right_layout.addWidget(self.tips_display, 1)

        self.status_label = QLabel("Ready")
        right_layout.addWidget(self.status_label)

        self.start_session_button = QPushButton("Start Practice Session")
        self.start_session_button.setEnabled(False)
        self.start_session_button.setMinimumHeight(50)
        self.start_session_button.clicked.connect(self._start_session)
        right_layout.addWidget(self.start_session_button)

        splitter.addWidget(right_panel)
        splitter.setSizes([500, 400])

    def _send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return

        self.chat_display.append(f"<b>You:</b> {message}")
        self.message_input.clear()

        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)
        self.status_label.setText("Thinking...")

        # Use AgentWorker for AI-powered processing
        self.worker = AgentWorker(message)
        self.worker.response_ready.connect(self._on_response)
        self.worker.photos_ready.connect(self._on_photos)
        self.worker.tips_ready.connect(self._on_tips)
        self.worker.error.connect(self._on_error)
        self.worker.no_photos.connect(self._on_no_photos)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_response(self, response: str):
        self.chat_display.append(f"<b>Assistant:</b> {response}")

    def _on_photos(self, photos: list):
        self.current_photos = photos
        self.status_label.setText(f"Found {len(photos)} reference photos")
        self.start_session_button.setEnabled(len(photos) > 0)

    def _on_tips(self, tips: dict):
        self.current_tips = tips
        self._display_tips(tips)

    def _display_tips(self, tips: dict):
        html = []

        if tips.get("practice_focus"):
            html.append(f"<b>Practice Focus:</b> {tips['practice_focus']}<br>")

        if tips.get("duration_advice"):
            html.append(f"<b>Duration tip:</b> {tips['duration_advice']}<br><br>")

        if tips.get("focus_areas"):
            html.append("<b>Focus Areas:</b><ul>")
            for area in tips["focus_areas"]:
                html.append(f"<li>{area}</li>")
            html.append("</ul>")

        if tips.get("common_mistakes"):
            html.append("<b>Avoid These Mistakes:</b><ul>")
            for mistake in tips["common_mistakes"]:
                html.append(f"<li>{mistake}</li>")
            html.append("</ul>")

        if tips.get("warm_up_suggestion"):
            html.append(f"<b>Warm-up:</b> {tips['warm_up_suggestion']}")

        self.tips_display.setHtml("".join(html))

    def _on_no_photos(self):
        self.status_label.setText("No photos found. Try a different search term.")
        self.start_session_button.setEnabled(False)

    def _on_error(self, error: str):
        self.chat_display.append(f"<b style='color: red;'>Error:</b> {error}")
        self.status_label.setText("Error occurred - check console for details")

    def _on_finished(self):
        self.send_button.setEnabled(True)
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        # Update status if still showing "Thinking..."
        if self.status_label.text() == "Thinking...":
            if self.current_photos:
                self.status_label.setText(f"Ready - {len(self.current_photos)} photos loaded")
            else:
                self.status_label.setText("Ready")

    def _start_session(self):
        if not self.current_photos:
            QMessageBox.warning(
                self,
                "No Photos",
                "Please describe what you want to practice first to get reference photos.",
            )
            return

        dialog = SessionSetupDialog(self.current_photos, self.current_tips, self)
        dialog.session_configured.connect(self._launch_practice_session)
        dialog.exec()

    def _launch_practice_session(self, photos: list, duration: int, play_sound: bool, tips: dict):
        """Launch the practice session window."""
        # Keep reference in MainWindow so it survives after dialog closes
        self.session_window = PracticeSessionWindow(
            photos=photos,
            duration_seconds=duration,
            play_sound=play_sound,
            tips=tips,
        )
        self.session_window.show()
