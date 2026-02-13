"""Test creation and editing window."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QDialog, QLineEdit, 
                             QTextEdit, QSpinBox, QMessageBox,
                             QListWidget, QListWidgetItem, QGroupBox, QHeaderView)
from PyQt5.QtCore import Qt


class TestEditorWindow(QWidget):
    """Test editor window."""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.tests = []
        self.questions = []
        self.init_ui()
        self.load_tests()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Test Management")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        add_btn = QPushButton("Create Test")
        add_btn.clicked.connect(self.create_test)
        header.addWidget(add_btn)
        layout.addLayout(header)
        
        # Tests table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Questions", "Time Limit", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self.edit_test)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def load_tests(self):
        """Load tests."""
        try:
            self.tests = self.api_client.get_tests()
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load tests: {str(e)}")
    
    def populate_table(self):
        """Populate table with tests."""
        self.table.setRowCount(len(self.tests))
        
        for row, test in enumerate(self.tests):
            self.table.setItem(row, 0, QTableWidgetItem(str(test['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(test['name']))
            self.table.setItem(row, 2, QTableWidgetItem(str(test.get('question_count', 0))))
            time_limit = str(test['time_limit']) + " min" if test.get('time_limit') else "No limit"
            self.table.setItem(row, 3, QTableWidgetItem(time_limit))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, t=test: self.edit_test_dialog(t))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("background-color: #dc3545; color: white;")
            delete_btn.clicked.connect(lambda checked, t=test: self.delete_test(t))
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.table.setCellWidget(row, 4, actions_widget)
    
    def create_test(self):
        """Create a new test."""
        dialog = TestDialog(self, self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.load_tests()
    
    def edit_test(self, row, col):
        """Edit test (double-click)."""
        test_id = int(self.table.item(row, 0).text())
        test = next((t for t in self.tests if t['id'] == test_id), None)
        if test:
            self.edit_test_dialog(test)
    
    def edit_test_dialog(self, test):
        """Open edit test dialog."""
        dialog = TestDialog(self, self.api_client, test)
        if dialog.exec_() == QDialog.Accepted:
            self.load_tests()
    
    def delete_test(self, test):
        """Delete a test."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete test '{test['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.api_client.delete_test(test['id'])
                QMessageBox.information(self, "Success", "Test deleted successfully")
                self.load_tests()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete test: {str(e)}")


class TestDialog(QDialog):
    """Dialog for creating/editing tests."""
    
    def __init__(self, parent, api_client, test=None):
        super().__init__(parent)
        self.api_client = api_client
        self.test = test
        self.questions = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Edit Test" if self.test else "Create Test")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Basic info
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Test Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # Settings
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Time Limit (minutes, 0 = no limit):"))
        self.time_limit_spin = QSpinBox()
        self.time_limit_spin.setMinimum(0)
        self.time_limit_spin.setMaximum(300)
        self.time_limit_spin.setValue(0)
        settings_layout.addWidget(self.time_limit_spin)
        
        settings_layout.addWidget(QLabel("Attempts Allowed:"))
        self.attempts_spin = QSpinBox()
        self.attempts_spin.setMinimum(1)
        self.attempts_spin.setMaximum(10)
        self.attempts_spin.setValue(1)
        settings_layout.addWidget(self.attempts_spin)
        layout.addLayout(settings_layout)
        
        # Questions selection
        layout.addWidget(QLabel("Select Questions:"))
        
        questions_layout = QHBoxLayout()
        
        # Available questions
        available_group = QGroupBox("Available Questions")
        available_layout = QVBoxLayout()
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.MultiSelection)
        available_layout.addWidget(self.available_list)
        available_group.setLayout(available_layout)
        questions_layout.addWidget(available_group)
        
        # Buttons
        buttons_layout = QVBoxLayout()
        add_btn = QPushButton(">")
        add_btn.clicked.connect(self.add_question)
        buttons_layout.addWidget(add_btn)
        remove_btn = QPushButton("<")
        remove_btn.clicked.connect(self.remove_question)
        buttons_layout.addWidget(remove_btn)
        buttons_layout.addStretch()
        questions_layout.addLayout(buttons_layout)
        
        # Selected questions
        selected_group = QGroupBox("Selected Questions (in order)")
        selected_layout = QVBoxLayout()
        self.selected_list = QListWidget()
        selected_layout.addWidget(self.selected_list)
        selected_group.setLayout(selected_layout)
        questions_layout.addWidget(selected_group)
        
        layout.addLayout(questions_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_test)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.load_questions()
        
        if self.test:
            self.load_test_data()
    
    def load_questions(self):
        """Load available questions."""
        try:
            self.questions = self.api_client.get_questions()
            topics = self.api_client.get_topics()
            topic_dict = {t['id']: t['name'] for t in topics}
            
            self.available_list.clear()
            for question in self.questions:
                topic_name = topic_dict.get(question['topic_id'], 'Unknown')
                item_text = f"[{topic_name}] {question['content'][:50]}..."
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, question)
                self.available_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load questions: {str(e)}")
    
    def load_test_data(self):
        """Load test data into form."""
        self.name_edit.setText(self.test.get('name', ''))
        self.desc_edit.setPlainText(self.test.get('description', ''))
        self.time_limit_spin.setValue(self.test.get('time_limit', 0) or 0)
        self.attempts_spin.setValue(self.test.get('attempts_allowed', 1))
        
        # Load test questions
        try:
            test_data = self.api_client.get_test(self.test['id'])
            for question in test_data.get('questions', []):
                item_text = f"Q{question.get('order', 0)}: {question.get('content', '')[:50]}..."
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, question)
                self.selected_list.addItem(item)
        except:
            pass
    
    def add_question(self):
        """Add selected question to test."""
        selected = self.available_list.selectedItems()
        for item in selected:
            question = item.data(Qt.UserRole)
            item_text = f"{question['content'][:50]}..."
            new_item = QListWidgetItem(item_text)
            new_item.setData(Qt.UserRole, question)
            self.selected_list.addItem(new_item)
            self.available_list.takeItem(self.available_list.row(item))
    
    def remove_question(self):
        """Remove question from test."""
        selected = self.selected_list.selectedItems()
        for item in selected:
            question = item.data(Qt.UserRole)
            topic_dict = {t['id']: t['name'] for t in self.api_client.get_topics()}
            topic_name = topic_dict.get(question['topic_id'], 'Unknown')
            item_text = f"[{topic_name}] {question['content'][:50]}..."
            new_item = QListWidgetItem(item_text)
            new_item.setData(Qt.UserRole, question)
            self.available_list.addItem(new_item)
            self.selected_list.takeItem(self.selected_list.row(item))
    
    def save_test(self):
        """Save test."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a test name")
            return
        
        # Get selected questions
        question_ids = []
        for i in range(self.selected_list.count()):
            item = self.selected_list.item(i)
            question = item.data(Qt.UserRole)
            question_ids.append({
                'question_id': question['id'],
                'order': i + 1
            })
        
        test_data = {
            'name': name,
            'description': self.desc_edit.toPlainText(),
            'time_limit': self.time_limit_spin.value() or None,
            'attempts_allowed': self.attempts_spin.value(),
            'question_ids': question_ids
        }
        
        try:
            if self.test:
                self.api_client.update_test(self.test['id'], test_data)
                QMessageBox.information(self, "Success", "Test updated successfully")
            else:
                self.api_client.create_test(test_data)
                QMessageBox.information(self, "Success", "Test created successfully")
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save test: {str(e)}")

