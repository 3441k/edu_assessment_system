#!/usr/bin/env python
"""Run the lecturer desktop application."""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import and run the app
from lecturer_app.windows.login_window import LecturerLoginWindow
from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Assessment System - Lecturer")
    
    window = LecturerLoginWindow()
    window.show()
    
    sys.exit(app.exec_())

