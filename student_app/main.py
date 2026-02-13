"""Main entry point for student desktop application."""

import sys
from PyQt5.QtWidgets import QApplication
from student_app.windows.login_window import LoginWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Assessment System - Student")
    
    window = LoginWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

