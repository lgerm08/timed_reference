#!/usr/bin/env python3
"""
Timed Reference - Art Practice Assistant

A desktop application that helps artists practice with timed reference photos.
Uses Agno framework for AI-powered assistance and Pexels API for reference images.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.main_window import MainWindow
import config


def check_api_keys():
    """Check if required API keys are configured."""
    missing = []

    if not config.PEXELS_API_KEY:
        missing.append("PEXELS_API_KEY")

    provider = config.LLM_PROVIDER.lower()
    if provider == "groq" and not config.GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    elif provider == "openai" and not config.OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")

    if missing:
        print("Warning: Missing API keys:")
        for key in missing:
            print(f"  - {key}")
        print(f"\nCurrent LLM provider: {config.LLM_PROVIDER}")
        print("Please set them in your .env file or environment variables.")
        print("See .env.example for reference.")


def main():
    """Main entry point."""
    check_api_keys()

    # Note: HiDPI scaling is enabled by default in Qt6
    app = QApplication(sys.argv)
    app.setApplicationName("Timed Reference")
    app.setOrganizationName("ArtPractice")

    app.setStyleSheet(
        """
        QMainWindow, QDialog {
            background-color: #2b2b2b;
        }
        QWidget {
            color: #e0e0e0;
        }
        QTextEdit, QLineEdit {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 5px;
            padding: 8px;
            color: #e0e0e0;
        }
        QTextEdit:focus, QLineEdit:focus {
            border-color: #4CAF50;
        }
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QPushButton:disabled {
            background-color: #555;
            color: #888;
        }
        QLabel {
            color: #e0e0e0;
        }
        QComboBox, QSpinBox {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 5px;
            padding: 5px;
            color: #e0e0e0;
        }
        QComboBox::drop-down {
            border: none;
        }
        QScrollArea {
            border: none;
            background-color: #2b2b2b;
        }
        QFrame {
            background-color: #333;
            border-radius: 5px;
        }
        QCheckBox {
            color: #e0e0e0;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QSplitter::handle {
            background-color: #555;
        }
        """
    )

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
