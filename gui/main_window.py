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
    QStackedWidget,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from services.pexels_client import pexels_client
from gui.session_setup import SessionSetupDialog
from gui.image_viewer import EmbeddedPracticeWidget
from gui.markdown_chat import MarkdownChatWidget
from agent.practice_agent import practice_agent
from agent.subagents.tips_generator import generate_practice_tips
from agent.tools.tips_tool import record_tips
from agent.tools.session_control_tool import get_current_config


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
    session_start = Signal(dict)  # Signal to start the practice session
    error = Signal(str)
    no_photos = Signal()

    def __init__(self, message: str, conversation_history: list[dict] = None):
        super().__init__()
        self.message = message
        self.conversation_history = conversation_history or []

    def run(self):
        try:
            print(f"[AGENT] Processing: {self.message}")

            # Build context from conversation history
            if self.conversation_history:
                # Include recent context in the message
                context_parts = []
                # Only include last 4 exchanges to keep context manageable
                recent_history = self.conversation_history[-8:]
                for msg in recent_history:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if role == 'user':
                        context_parts.append(f"User: {content}")
                    elif role == 'assistant':
                        # Truncate long assistant responses
                        short_content = content[:200] + "..." if len(content) > 200 else content
                        context_parts.append(f"Assistant: {short_content}")

                context = "\n".join(context_parts)
                full_message = f"""Previous conversation:
{context}

Current user message: {self.message}"""
            else:
                full_message = self.message

            # Run the Agno agent with context
            response = practice_agent.run(full_message)

            print(f"[AGENT] Response received")
            # Emit text response
            content = response.content if response.content else ""
            print(f"[AGENT] Response content: {content}")
            self.response_ready.emit(str(content))
            print(f"[AGENT] Extracting tools results")

            # Extract tool results from the response
            photos = []
            tips = {}
            session_config = None

            if response.tools:
                print(f"[AGENT] Found {len(response.tools)} tool executions")
                for i, tool_exec in enumerate(response.tools):
                    tool_name = getattr(tool_exec, 'tool_name', None) or getattr(tool_exec, 'name', None)
                    result_str = getattr(tool_exec, 'result', None) or getattr(tool_exec, 'content', None)
                    print(f"[AGENT] Tool {i}: {tool_name}, has_result: {result_str is not None}")

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

                        # Check for any image curation tool (Pexels or Pinterest)
                        image_tools = (
                            "search_reference_photos",
                            "curate_reference_photos",
                            "curate_pinterest_images",
                            "curate_pinterest_diverse",
                        )
                        if tool_name in image_tools and isinstance(result, list):
                            # Normalize photo keys (curator uses pexels_id, others use id)
                            photos = []
                            for photo in result:
                                normalized = dict(photo)
                                if "pexels_id" in normalized and "id" not in normalized:
                                    normalized["id"] = normalized["pexels_id"]
                                photos.append(normalized)
                            print(f"[AGENT] Extracted {len(photos)} photos from {tool_name}")
                        elif tool_name == "get_practice_tips" and isinstance(result, dict):
                            tips = result
                        elif tool_name == "start_practice_session" and isinstance(result, dict):
                            # Agent wants to start the session
                            if result.get("success"):
                                session_config = result
                                print(f"[AGENT] Session start requested: {session_config}")

            # Emit tips if found from tool
            if tips:
                print(f"[AGENT] Extracted practice tips: {tips}")
                record_tips(tips)
                self.tips_ready.emit(tips)

            # Generate tips using subagent if we have photos but no tips
            if photos and not tips:
                try:
                    # Get theme from session config or infer from message
                    config = get_current_config()
                    theme = config.get("theme") or self.message[:50]
                    duration = config.get("duration_seconds", 60)

                    print(f"[AGENT] Generating tips for '{theme}' at {duration}s")
                    generated_tips = generate_practice_tips(theme, duration)
                    if generated_tips:
                        record_tips(generated_tips)
                        self.tips_ready.emit(generated_tips)
                except Exception as e:
                    print(f"[AGENT] Tips generation failed: {e}")

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
        self.current_theme = ""
        self.conversation_history: list[dict] = []  # Track conversation for context

        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header = QLabel("Timed Reference - Art Practice")
        header.setFont(QFont("Arial", 24, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # Main horizontal splitter: [Stacked Views | Tips Panel]
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        # Stacked widget for switching between chat and practice views
        self.view_stack = QStackedWidget()

        # Chat view (index 0)
        chat_view = self._create_chat_view()
        self.view_stack.addWidget(chat_view)

        # Practice view (index 1)
        self.practice_widget = EmbeddedPracticeWidget()
        self.practice_widget.session_completed.connect(self._on_session_completed)
        self.practice_widget.session_ended.connect(self._return_to_chat)
        self.view_stack.addWidget(self.practice_widget)

        splitter.addWidget(self.view_stack)

        # Tips panel (always visible on right side)
        right_panel = self._create_tips_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([600, 300])

    def _create_chat_view(self) -> QWidget:
        """Create the chat/setup view."""
        chat_view = QFrame()
        left_layout = QVBoxLayout(chat_view)

        chat_label = QLabel("Chat with your practice assistant:")
        left_layout.addWidget(chat_label)

        self.chat_display = MarkdownChatWidget()
        self.chat_display.add_system_message(
            "Tell me what you want to practice today! Examples: "
            "'I want to practice drawing hands', "
            "'Help me with gesture drawing', "
            "'I need vehicle references for sketching'"
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
        return chat_view

    def _create_tips_panel(self) -> QWidget:
        """Create the tips panel (always visible on right side)."""
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        tips_label = QLabel("Practice Tips:")
        tips_label.setFont(QFont("Arial", 14, QFont.Bold))
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

        return right_panel

    def _return_to_chat(self):
        """Return to chat view after session ends."""
        self.view_stack.setCurrentIndex(0)
        self.start_session_button.setEnabled(len(self.current_photos) > 0)
        self.status_label.setText("Ready for another session")

    def _send_message(self):
        message = self.message_input.text().strip()
        if not message:
            return

        self.chat_display.add_user_message(message)
        self.message_input.clear()

        # Track in conversation history
        self.conversation_history.append({'role': 'user', 'content': message})

        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)
        self.status_label.setText("Thinking...")

        # Use AgentWorker for AI-powered processing with conversation context
        self.worker = AgentWorker(message, self.conversation_history.copy())
        self.worker.response_ready.connect(self._on_response)
        self.worker.photos_ready.connect(self._on_photos)
        self.worker.tips_ready.connect(self._on_tips)
        self.worker.error.connect(self._on_error)
        self.worker.no_photos.connect(self._on_no_photos)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_response(self, response: str):
        # Track assistant response in history
        self.conversation_history.append({'role': 'assistant', 'content': response})
        # Filter out tips content from chat (tips go to the tips panel only)
        filtered_response = self._filter_tips_from_response(response)
        if filtered_response.strip():
            self.chat_display.add_assistant_message(filtered_response)

    def _filter_tips_from_response(self, response: str) -> str:
        """Remove tips-related content that should only appear in tips panel."""
        import re
        # Remove common tips headers/sections from chat
        patterns = [
            r'(?i)##?\s*practice\s+tips.*?(?=##|\n\n|\Z)',
            r'(?i)##?\s*focus\s+areas.*?(?=##|\n\n|\Z)',
            r'(?i)##?\s*tips\s+for.*?(?=##|\n\n|\Z)',
            r'(?i)\*\*practice\s+tips\*\*.*?(?=\*\*[^*]|\n\n|\Z)',
            r'(?i)\*\*focus\s+areas\*\*.*?(?=\*\*[^*]|\n\n|\Z)',
        ]
        filtered = response
        for pattern in patterns:
            filtered = re.sub(pattern, '', filtered, flags=re.DOTALL)
        return filtered.strip()

    def _on_photos(self, photos: list):
        self.current_photos = photos
        self.status_label.setText(f"Found {len(photos)} reference photos")

        # Show image previews in chat for HITL approval
        if photos:
            self.chat_display.add_image_preview(photos, f"Found {len(photos)} reference photos:")
        self.start_session_button.setEnabled(len(photos) > 0)

    def _on_tips(self, tips: dict):
        self.current_tips = tips
        # Extract theme from tips if available
        if tips.get("practice_focus"):
            self.current_theme = tips["practice_focus"]
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
        self.chat_display.add_error_message(error)
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

        dialog = SessionSetupDialog(
            self.current_photos,
            self.current_tips,
            theme=self.current_theme,
            parent=self
        )
        dialog.session_configured.connect(self._launch_practice_session)
        dialog.exec()

    def _launch_practice_session(self, photos: list, duration: int, play_sound: bool, tips: dict, theme: str = ""):
        """Switch to practice view and start the session."""
        # Start the practice session in the embedded widget
        self.practice_widget.start_session(
            photos=photos,
            duration_seconds=duration,
            play_sound=play_sound,
            tips=tips,
            theme=theme or self.current_theme,
        )
        # Switch to practice view
        self.view_stack.setCurrentIndex(1)
        self.start_session_button.setEnabled(False)
        self.status_label.setText("Session in progress...")

    def _on_session_completed(self, minutes: int, images: int):
        """Handle session completion."""
        self.chat_display.add_system_message(
            f"Great session! You practiced for {minutes} minutes with {images} images."
        )
