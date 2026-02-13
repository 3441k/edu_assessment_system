"""Main window for lecturer application."""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTabWidget, QMessageBox)
from PyQt5.QtCore import Qt
from lecturer_app.api_client import LecturerAPIClient
from lecturer_app.windows.question_bank import QuestionBankWindow
from lecturer_app.windows.test_editor import TestEditorWindow
from lecturer_app.windows.grading_window import GradingWindow
from lecturer_app.windows.statistics import StatisticsWindow
from lecturer_app.windows.student_management import StudentManagementWindow


class MainWindow(QMainWindow):
    """Main window for lecturer application."""
    
    def __init__(self, api_client=None):
        super().__init__()
        # Use provided API client (with session cookies) or create new one
        self.api_client = api_client if api_client else LecturerAPIClient()
        self.init_ui()
        self.check_connection()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Assessment System - Lecturer")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Assessment System - Lecturer Dashboard")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)
        header.addWidget(logout_btn)
        layout.addLayout(header)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Question Bank tab
        self.question_bank = QuestionBankWindow(self.api_client)
        self.tabs.addTab(self.question_bank, "Question Bank")
        
        # Test Editor tab
        self.test_editor = TestEditorWindow(self.api_client)
        self.tabs.addTab(self.test_editor, "Tests")
        
        # Grading tab
        self.grading = GradingWindow(self.api_client)
        self.tabs.addTab(self.grading, "Grading")
        
        # Statistics tab
        self.statistics = StatisticsWindow(self.api_client)
        self.tabs.addTab(self.statistics, "Statistics")
        
        # Student Management tab
        self.student_management = StudentManagementWindow(self.api_client)
        self.tabs.addTab(self.student_management, "Students")
        
        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        
        self.center_window()
    
    def center_window(self):
        """Center window on screen."""
        from PyQt5.QtWidgets import QDesktopWidget
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
    
    def check_connection(self):
        """Check connection to server."""
        try:
            self.api_client.get_current_user()
        except Exception as e:
            QMessageBox.warning(
                self, "Connection Error",
                f"Could not connect to server.\n\n"
                f"Please ensure the Flask server is running.\n"
                f"Error: {str(e)}\n\n"
                f"You can still use the application, but some features may not work."
            )
    
    def logout(self):
        """Logout."""
        try:
            self.api_client.logout()
        except:
            pass
        self.close()

