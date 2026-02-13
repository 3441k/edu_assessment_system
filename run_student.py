#!/usr/bin/env python
"""Run the student desktop application."""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import and run the app
from student_app.windows.login_window import LoginWindow
from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Assessment System - Student")
    
    window = LoginWindow()
    window.show()
    
    sys.exit(app.exec_())

