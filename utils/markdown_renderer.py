"""
Markdown Renderer for Chat Display.

Converts markdown text to HTML with styling suitable for dark theme.
"""

import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.nl2br import Nl2BrExtension
from markdown.extensions.sane_lists import SaneListExtension


class MarkdownRenderer:
    """Renders markdown to HTML with dark theme styling."""

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                FencedCodeExtension(),
                TableExtension(),
                Nl2BrExtension(),
                SaneListExtension(),
            ]
        )

    def render(self, text: str) -> str:
        """
        Convert markdown text to HTML.

        Args:
            text: Markdown formatted text

        Returns:
            HTML string
        """
        # Reset markdown instance state for fresh conversion
        self.md.reset()
        return self.md.convert(text)

    def get_stylesheet(self) -> str:
        """
        Return CSS stylesheet for rendered HTML.

        Designed for dark theme with good readability.
        """
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: #e0e0e0;
            margin: 0;
            padding: 8px;
        }

        h1, h2, h3, h4, h5, h6 {
            color: #4CAF50;
            margin-top: 16px;
            margin-bottom: 8px;
            font-weight: 600;
        }

        h1 { font-size: 1.7em; }
        h2 { font-size: 1.5em; }
        h3 { font-size: 1.3em; }

        p {
            margin: 8px 0;
        }

        ul, ol {
            margin: 8px 0;
            padding-left: 24px;
        }

        li {
            margin: 4px 0;
        }

        code {
            background: #1a1a1a;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #ff9800;
        }

        pre {
            background: #1a1a1a;
            padding: 12px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 8px 0;
        }

        pre code {
            padding: 0;
            background: none;
            color: #e0e0e0;
        }

        strong, b {
            color: #4CAF50;
            font-weight: 600;
        }

        em, i {
            color: #90CAF9;
        }

        blockquote {
            border-left: 3px solid #4CAF50;
            margin: 8px 0;
            padding-left: 12px;
            color: #b0b0b0;
        }

        table {
            border-collapse: collapse;
            margin: 8px 0;
            width: 100%;
        }

        th, td {
            border: 1px solid #555;
            padding: 8px;
            text-align: left;
        }

        th {
            background: #333;
            color: #4CAF50;
        }

        a {
            color: #64B5F6;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        hr {
            border: none;
            border-top: 1px solid #555;
            margin: 16px 0;
        }

        .user-message {
            background: #2d3a2d;
            border-radius: 8px;
            padding: 8px 12px;
            margin: 8px 0;
        }

        .assistant-message {
            background: #3c3c3c;
            border-radius: 8px;
            padding: 8px 12px;
            margin: 8px 0;
        }

        .error-message {
            background: #4a2d2d;
            border-radius: 8px;
            padding: 8px 12px;
            margin: 8px 0;
            color: #ff6b6b;
        }

        .message-header {
            font-weight: 600;
            margin-bottom: 4px;
        }

        .user-header {
            color: #81C784;
        }

        .assistant-header {
            color: #64B5F6;
        }
        """

    def wrap_with_style(self, html: str) -> str:
        """Wrap HTML content with stylesheet."""
        return f"<style>{self.get_stylesheet()}</style>{html}"
