"""Student management window."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QDialog, QLineEdit, 
                             QMessageBox, QHeaderView, QFileDialog)
from PyQt5.QtCore import Qt


class StudentManagementWindow(QWidget):
    """Student management window."""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.students = []
        self.init_ui()
        self.load_students()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Student Management")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        add_btn = QPushButton("Add Student")
        add_btn.clicked.connect(self.add_student)
        header.addWidget(add_btn)
        
        import_btn = QPushButton("Import CSV")
        import_btn.clicked.connect(self.import_csv)
        header.addWidget(import_btn)
        layout.addLayout(header)
        
        # Students table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Student ID", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def load_students(self):
        """Load students."""
        try:
            self.students = self.api_client.get_students()
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load students: {str(e)}")
    
    def populate_table(self):
        """Populate table with students."""
        self.table.setRowCount(len(self.students))
        
        for row, student in enumerate(self.students):
            self.table.setItem(row, 0, QTableWidgetItem(str(student['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(student.get('username', '')))
            self.table.setItem(row, 2, QTableWidgetItem(student.get('student_id', '')))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("background-color: #dc3545; color: white;")
            delete_btn.clicked.connect(lambda checked, s=student: self.delete_student(s))
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.table.setCellWidget(row, 3, actions_widget)
    
    def add_student(self):
        """Add a new student."""
        dialog = StudentDialog(self, self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.load_students()
    
    def import_csv(self):
        """Import students from CSV."""
        filename, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        
        if filename:
            try:
                result = self.api_client.import_students_csv(filename)
                QMessageBox.information(
                    self, "Import Complete",
                    f"Imported {result.get('imported', 0)} students.\n"
                    f"Errors: {result.get('errors', 0)}"
                )
                self.load_students()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import CSV: {str(e)}")
    
    def delete_student(self, student):
        """Delete a student."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete student '{student.get('username')}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Delete via API
                self.api_client._make_request('DELETE', f"/api/v1/students/{student['id']}")
                QMessageBox.information(self, "Success", "Student deleted successfully")
                self.load_students()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete student: {str(e)}")


class StudentDialog(QDialog):
    """Dialog for adding/editing students."""
    
    def __init__(self, parent, api_client, student=None):
        super().__init__(parent)
        self.api_client = api_client
        self.student = student
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Edit Student" if self.student else "Add Student")
        self.setMinimumSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        self.username_edit = QLineEdit()
        username_layout.addWidget(self.username_edit)
        layout.addLayout(username_layout)
        
        # Student ID
        student_id_layout = QHBoxLayout()
        student_id_layout.addWidget(QLabel("Student ID:"))
        self.student_id_edit = QLineEdit()
        student_id_layout.addWidget(self.student_id_edit)
        layout.addLayout(student_id_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.password_edit)
        layout.addLayout(password_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_student)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        if self.student:
            self.username_edit.setText(self.student.get('username', ''))
            self.student_id_edit.setText(self.student.get('student_id', ''))
    
    def save_student(self):
        """Save student."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        student_id = self.student_id_edit.text().strip() or None
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Username and password are required")
            return
        
        try:
            self.api_client.create_student(username, password, student_id)
            QMessageBox.information(self, "Success", "Student created successfully")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save student: {str(e)}")

