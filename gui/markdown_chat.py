"""
Markdown Chat Widget for Art Practice Assistant.

Provides a QTextBrowser-based chat display with markdown rendering.
Supports image previews for HITL (Human-in-the-Loop) approval.
"""

import sys
import base64
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PySide6.QtCore import QUrl, QThread, Signal
from PySide6.QtGui import QImage

from utils.markdown_renderer import MarkdownRenderer
from services.image_cache import image_cache


class ThumbnailLoader(QThread):
    """Background thread for loading thumbnail images."""

    thumbnail_loaded = Signal(int, str)  # index, base64_data
    finished_all = Signal()

    def __init__(self, urls: list[str]):
        super().__init__()
        self.urls = urls

    def run(self):
        for i, url in enumerate(self.urls):
            try:
                path = image_cache.download(url)
                if path and path.exists():
                    # Load and convert to base64
                    image = QImage(str(path))
                    if not image.isNull():
                        # Scale down for thumbnail
                        scaled = image.scaled(150, 150)
                        # Save to bytes and encode
                        from PySide6.QtCore import QByteArray, QBuffer, QIODevice
                        byte_array = QByteArray()
                        buffer = QBuffer(byte_array)
                        buffer.open(QIODevice.WriteOnly)
                        scaled.save(buffer, "PNG")
                        b64 = base64.b64encode(byte_array.data()).decode('utf-8')
                        self.thumbnail_loaded.emit(i, b64)
            except Exception as e:
                print(f"[THUMBNAIL] Error loading {url}: {e}")
        self.finished_all.emit()


class MarkdownChatWidget(QWidget):
    """Chat display widget with markdown rendering support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = MarkdownRenderer()
        self.messages: list[tuple[str, str, Optional[dict]]] = []  # (role, content, extra_data)
        self.pending_thumbnails: dict[int, str] = {}  # index -> base64 data
        self.thumbnail_loader: Optional[ThumbnailLoader] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setReadOnly(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #2b2b2b;
                border: none;
                padding: 8px;
            }
        """)

        layout.addWidget(self.browser)

    def add_user_message(self, text: str):
        """
        Add a user message to the chat.

        User messages are displayed as plain text (not markdown).
        """
        self.messages.append(('user', text, None))
        self._render_all()

    def add_assistant_message(self, text: str):
        """
        Add an assistant message to the chat.

        Assistant messages are rendered as markdown.
        """
        self.messages.append(('assistant', text, None))
        self._render_all()

    def add_error_message(self, text: str):
        """Add an error message to the chat."""
        self.messages.append(('error', text, None))
        self._render_all()

    def add_system_message(self, text: str):
        """Add a system/info message to the chat."""
        self.messages.append(('system', text, None))
        self._render_all()

    def add_image_preview(self, photos: list[dict], message: str = ""):
        """
        Add image preview thumbnails for HITL approval.

        Args:
            photos: List of photo dicts with 'thumbnail' and 'alt' keys
            message: Optional message to display with previews
        """
        preview_data = {
            'type': 'image_preview',
            'photos': photos,
            'thumbnails': {},  # Will be populated as images load
        }
        self.messages.append(('preview', message or f"Found {len(photos)} reference photos:", preview_data))
        self._render_all()

        # Start loading thumbnails in background
        # Use thumbnail if available, fallback to main url (for Pinterest local paths)
        urls = [p.get('thumbnail') or p.get('url') for p in photos if p.get('thumbnail') or p.get('url')]
        if urls:
            self._load_thumbnails(urls, len(self.messages) - 1)

    def _load_thumbnails(self, urls: list[str], message_index: int):
        """Load thumbnails in background thread."""
        # Store the message index for updating later
        self._preview_message_index = message_index

        # Stop any previous loader
        if self.thumbnail_loader and self.thumbnail_loader.isRunning():
            self.thumbnail_loader.wait()

        self.thumbnail_loader = ThumbnailLoader(urls)
        self.thumbnail_loader.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        self.thumbnail_loader.finished_all.connect(self._on_thumbnails_complete)
        self.thumbnail_loader.start()

    def _on_thumbnail_loaded(self, index: int, b64_data: str):
        """Handle a loaded thumbnail."""
        if hasattr(self, '_preview_message_index'):
            msg_idx = self._preview_message_index
            if msg_idx < len(self.messages):
                role, content, data = self.messages[msg_idx]
                if data and 'thumbnails' in data:
                    data['thumbnails'][index] = b64_data
                    # Update display
                    self._render_all()

    def _on_thumbnails_complete(self):
        """Handle completion of all thumbnail loading."""
        print("[CHAT] All thumbnails loaded")

    def _render_all(self):
        """Re-render all messages to HTML."""
        html_parts = [f"<style>{self.renderer.get_stylesheet()}</style>"]

        for msg in self.messages:
            role = msg[0]
            content = msg[1]
            data = msg[2] if len(msg) > 2 else None

            if role == 'user':
                # User messages: plain text, escaped
                escaped = self._escape_html(content)
                html_parts.append(
                    f'<div class="user-message">'
                    f'<div class="message-header user-header">You:</div>'
                    f'{escaped}</div>'
                )
            elif role == 'assistant':
                # Assistant messages: rendered as markdown
                rendered = self.renderer.render(content)
                html_parts.append(
                    f'<div class="assistant-message">'
                    f'<div class="message-header assistant-header">Assistant:</div>'
                    f'{rendered}</div>'
                )
            elif role == 'error':
                escaped = self._escape_html(content)
                html_parts.append(
                    f'<div class="error-message">'
                    f'<div class="message-header">Error:</div>'
                    f'{escaped}</div>'
                )
            elif role == 'system':
                escaped = self._escape_html(content)
                html_parts.append(
                    f'<div style="color: #888; font-style: italic; '
                    f'padding: 4px 0; font-size: 0.9em;">{escaped}</div>'
                )
            elif role == 'preview' and data:
                # Image preview with thumbnails
                html_parts.append(self._render_preview(content, data))

        self.browser.setHtml(''.join(html_parts))

        # Scroll to bottom
        scrollbar = self.browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _render_preview(self, message: str, data: dict) -> str:
        """Render image preview section with thumbnails."""
        photos = data.get('photos', [])
        thumbnails = data.get('thumbnails', {})

        html = f'''
        <div style="background-color: #333; border-radius: 8px; padding: 12px; margin: 8px 0;">
            <div style="color: #4CAF50; font-weight: bold; margin-bottom: 8px;">
                📷 {self._escape_html(message)}
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
        '''

        for i, photo in enumerate(photos):
            alt = self._escape_html(photo.get('alt', 'Reference photo')[:50])
            photographer = self._escape_html(photo.get('photographer', 'Unknown'))

            if i in thumbnails:
                # Show loaded thumbnail
                b64 = thumbnails[i]
                img_html = f'<img src="data:image/png;base64,{b64}" style="width: 100px; height: 100px; object-fit: cover; border-radius: 4px;">'
            else:
                # Placeholder while loading
                img_html = f'''
                <div style="width: 100px; height: 100px; background-color: #444;
                     border-radius: 4px; display: flex; align-items: center;
                     justify-content: center; color: #888; font-size: 12px;">
                    Loading...
                </div>
                '''

            html += f'''
            <div style="text-align: center; width: 110px;">
                {img_html}
                <div style="color: #aaa; font-size: 10px; margin-top: 4px;
                     overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {photographer}
                </div>
            </div>
            '''

        html += '''
            </div>
            <div style="color: #888; font-size: 12px; margin-top: 8px;">
                Type "start" to begin, or ask for different images.
            </div>
        </div>
        '''

        return html

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('\n', '<br>')
        )

    def clear(self):
        """Clear all messages."""
        self.messages = []
        self.browser.clear()

    def get_message_count(self) -> int:
        """Get the number of messages in the chat."""
        return len(self.messages)

    def export_conversation(self) -> str:
        """Export the conversation as plain text."""
        lines = []
        for role, content in self.messages:
            prefix = {
                'user': 'You',
                'assistant': 'Assistant',
                'error': 'Error',
                'system': 'System'
            }.get(role, role.capitalize())
            lines.append(f"{prefix}: {content}")
            lines.append("")
        return '\n'.join(lines)
