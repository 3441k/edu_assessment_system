"""Dashboard window for student application."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QTimer
from student_app.windows.test_taking import TestTakingWindow


class DashboardWindow(QWidget):
    """Dashboard window showing available tests."""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.init_ui()
        self.load_tests()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("My Tests - Assessment System")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("My Tests")
        font = title.font()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.logout)
        header.addWidget(logout_btn)
        layout.addLayout(header)
        
        # Scroll area for tests
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.tests_container = QWidget()
        self.tests_layout = QVBoxLayout()
        self.tests_layout.setSpacing(10)
        self.tests_container.setLayout(self.tests_layout)
        
        scroll.setWidget(self.tests_container)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        self.center_window()
    
    def center_window(self):
        """Center window on screen."""
        from PyQt5.QtWidgets import QDesktopWidget
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
    
    def load_tests(self):
        """Load and display tests."""
        try:
            tests = self.api_client.get_tests()
            
            # Clear existing tests
            while self.tests_layout.count():
                child = self.tests_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            if not tests:
                no_tests_label = QLabel("No tests available.")
                no_tests_label.setAlignment(Qt.AlignCenter)
                self.tests_layout.addWidget(no_tests_label)
                return
            
            for test in tests:
                self.add_test_card(test)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load tests: {str(e)}")
    
    def add_test_card(self, test):
        """Add a test card to the dashboard."""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Test name
        name_label = QLabel(test.get('name', 'Untitled Test'))
        font = name_label.font()
        font.setPointSize(14)
        font.setBold(True)
        name_label.setFont(font)
        layout.addWidget(name_label)
        
        # Description
        if test.get('description'):
            desc_label = QLabel(test.get('description'))
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666;")
            layout.addWidget(desc_label)
        
        # Status and action
        action_layout = QHBoxLayout()
        
        status = test.get('submission_status', 'not_started')
        status_text = {
            'not_started': 'Not Started',
            'in_progress': 'In Progress',
            'submitted': 'Submitted',
            'graded': 'Graded'
        }.get(status, 'Unknown')
        
        status_label = QLabel(f"Status: {status_text}")
        status_label.setStyleSheet("color: #666;")
        action_layout.addWidget(status_label)
        action_layout.addStretch()
        
        # Action button
        if status in ['not_started', 'in_progress']:
            action_btn = QPushButton("Start Test" if status == 'not_started' else "Continue Test")
            action_btn.clicked.connect(lambda checked, t=test: self.start_test(t))
            action_layout.addWidget(action_btn)
        elif status == 'graded':
            action_btn = QPushButton("View Results")
            action_btn.clicked.connect(lambda checked, t=test: self.view_results(t))
            action_layout.addWidget(action_btn)
        
        layout.addLayout(action_layout)
        
        card.setLayout(layout)
        self.tests_layout.addWidget(card)
    
    def start_test(self, test):
        """Start or continue a test."""
        test_window = TestTakingWindow(self.api_client, test['id'])
        test_window.show()
        test_window.exec_()
        # Refresh tests after test window closes
        QTimer.singleShot(500, self.load_tests)
    
    def view_results(self, test):
        """View test results."""
        QMessageBox.information(self, "Results", 
                              f"Results for {test.get('name')} are available.\n"
                              "This feature will be implemented in the grading interface.")
    
    def logout(self):
        """Logout and close dashboard."""
        try:
            self.api_client.logout()
        except:
            pass
        self.close()

