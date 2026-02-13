"""Login window for lecturer application."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from lecturer_app.api_client import LecturerAPIClient
from lecturer_app.windows.main_window import MainWindow


class LecturerLoginWindow(QWidget):
    """Login window for lecturer."""
    
    def __init__(self):
        super().__init__()
        self.api_client = LecturerAPIClient()
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Lecturer Login - Assessment System")
        self.setFixedSize(480, 500)
        
        # Main layout with background styling
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container frame with styling
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 10px;
            }
        """)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)
        
        # Title section
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        
        title = QLabel("Welcome Back")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: white;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("Lecturer Portal")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        title_layout.addWidget(subtitle)
        
        container_layout.addLayout(title_layout)
        container_layout.addSpacing(20)
        
        # Form container with white background
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(0)  # We'll use explicit spacing instead
        
        # Username field
        username_layout = QVBoxLayout()
        username_layout.setSpacing(12)
        username_label = QLabel("Username")
        username_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-weight: 600;
                font-size: 13px;
            }
        """)
        username_layout.addWidget(username_label)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setMinimumHeight(40)
        self.username_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: #fafafa;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
                background-color: white;
            }
        """)
        username_layout.addWidget(self.username_input)
        form_layout.addLayout(username_layout)
        
        # Add spacing between username and password fields
        form_layout.addSpacing(20)
        
        # Password field
        password_layout = QVBoxLayout()
        password_layout.setSpacing(12)
        password_label = QLabel("Password")
        password_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-weight: 600;
                font-size: 13px;
            }
        """)
        password_layout.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setMinimumHeight(40)
        self.password_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: #fafafa;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
                background-color: white;
            }
        """)
        password_layout.addWidget(self.password_input)
        form_layout.addLayout(password_layout)
        
        form_layout.addSpacing(55)
        
        # Login button
        login_btn = QPushButton("Login")
        login_btn.setMinimumHeight(45)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 15px;
                padding: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5568d3, stop:1 #6a3d8f);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a5bc2, stop:1 #5d2d7d);
            }
        """)
        login_btn.clicked.connect(self.login)
        form_layout.addWidget(login_btn)
        
        # Add stretch at the end to push everything up and create space
        form_layout.addStretch()
        
        form_frame.setLayout(form_layout)
        container_layout.addWidget(form_frame)
        
        container.setLayout(container_layout)
        main_layout.addWidget(container)
        
        self.setLayout(main_layout)
        
        # Set window background
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
        """)
        
        # Enter key on password field also triggers login
        self.password_input.returnPressed.connect(self.login)
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
        
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
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        try:
            result = self.api_client.login(username, password)
            
            if result:
                # Open main window with the authenticated API client
                self.main_window = MainWindow(self.api_client)
                self.main_window.show()
                self.close()
            else:
                QMessageBox.warning(self, "Error", "Login failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login failed: {str(e)}\n\nPlease ensure the Flask server is running.")

