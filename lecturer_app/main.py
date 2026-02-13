"""Main entry point for lecturer desktop application."""

import sys
from PyQt5.QtWidgets import QApplication
from lecturer_app.windows.login_window import LecturerLoginWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Assessment System - Lecturer")
    
    window = LecturerLoginWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

