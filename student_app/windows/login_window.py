"""Login window for student application."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from student_app.api_client import APIClient
from student_app.windows.dashboard import DashboardWindow


class LoginWindow(QWidget):
    """Login window."""
    
    def __init__(self):
        super().__init__()
        self.api_client = APIClient()
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Student Login - Assessment System")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("Student Login")
        title.setAlignment(Qt.AlignCenter)
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        # Username
        username_label = QLabel("Username:")
        layout.addWidget(username_label)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        layout.addWidget(self.username_input)
        
        # Student ID
        student_id_label = QLabel("Student ID:")
        layout.addWidget(student_id_label)
        self.student_id_input = QLineEdit()
        self.student_id_input.setPlaceholderText("Enter your student ID (optional)")
        layout.addWidget(self.student_id_input)
        
        # Password
        password_label = QLabel("Password:")
        layout.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        layout.addWidget(self.password_input)
        
        # Login button
        login_btn = QPushButton("Login")
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #764ba2;
            }
        """)
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)
        
        # Enter key on password field also triggers login
        self.password_input.returnPressed.connect(self.login)
        
        self.setLayout(layout)
        self.center_window()
    
    def center_window(self):
        """Center window on screen."""
        from PyQt5.QtWidgets import QDesktopWidget
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
    
    def login(self):
        """Handle login."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        student_id = self.student_id_input.text().strip() or None
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        try:
            result = self.api_client.login(username, password, student_id)
            
            if result:
                # Open dashboard
                self.dashboard = DashboardWindow(self.api_client)
                self.dashboard.show()
                self.close()
            else:
                QMessageBox.warning(self, "Error", "Login failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login failed: {str(e)}")

