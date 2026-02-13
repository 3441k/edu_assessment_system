"""Question bank management window."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QDialog, QLineEdit, 
                             QTextEdit, QComboBox, QDoubleSpinBox, QMessageBox,
                             QHeaderView, QGroupBox, QListWidget)
from PyQt5.QtCore import Qt
from shared.constants import QUESTION_TYPES, QUESTION_TYPE_MULTIPLE_CHOICE, QUESTION_TYPE_CODE


class QuestionBankWindow(QWidget):
    """Question bank management window."""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.topics = []
        self.questions = []
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Question Bank")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        add_btn = QPushButton("Add Question")
        add_btn.clicked.connect(self.add_question)
        header.addWidget(add_btn)
        layout.addLayout(header)
        
        # Topics filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Topic:"))
        self.topic_filter = QComboBox()
        self.topic_filter.addItem("All Topics")
        self.topic_filter.currentIndexChanged.connect(self.filter_questions)
        filter_layout.addWidget(self.topic_filter)
        
        # Topic management buttons
        manage_topics_btn = QPushButton("Manage Topics")
        manage_topics_btn.clicked.connect(self.manage_topics)
        filter_layout.addWidget(manage_topics_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Questions table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Topic", "Type", "Content", "Points", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.edit_question)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def load_data(self):
        """Load topics and questions."""
        try:
            self.topics = self.api_client.get_topics()
            self.topic_filter.clear()
            self.topic_filter.addItem("All Topics")
            for topic in self.topics:
                self.topic_filter.addItem(topic['name'], topic['id'])
            
            self.load_questions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
    
    def load_questions(self, topic_id=None):
        """Load questions."""
        try:
            self.questions = self.api_client.get_questions(topic_id)
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load questions: {str(e)}")
    
    def populate_table(self):
        """Populate table with questions."""
        self.table.setRowCount(len(self.questions))
        
        topic_dict = {t['id']: t['name'] for t in self.topics}
        
        for row, question in enumerate(self.questions):
            self.table.setItem(row, 0, QTableWidgetItem(str(question['id'])))
            topic_name = topic_dict.get(question['topic_id'], 'Unknown')
            self.table.setItem(row, 1, QTableWidgetItem(topic_name))
            self.table.setItem(row, 2, QTableWidgetItem(question['type']))
            content = question['content'][:100] + "..." if len(question['content']) > 100 else question['content']
            self.table.setItem(row, 3, QTableWidgetItem(content))
            self.table.setItem(row, 4, QTableWidgetItem(str(question['points'])))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, q=question: self.edit_question_dialog(q))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("background-color: #dc3545; color: white;")
            delete_btn.clicked.connect(lambda checked, q=question: self.delete_question(q))
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.table.setCellWidget(row, 5, actions_widget)
    
    def filter_questions(self):
        """Filter questions by topic."""
        topic_id = self.topic_filter.currentData()
        self.load_questions(topic_id)
    
    def add_question(self):
        """Add a new question."""
        dialog = QuestionDialog(self, self.api_client, self.topics)
        if dialog.exec_() == QDialog.Accepted:
            self.load_questions()
    
    def edit_question(self, row, col):
        """Edit question (double-click)."""
        question_id = int(self.table.item(row, 0).text())
        question = next((q for q in self.questions if q['id'] == question_id), None)
        if question:
            self.edit_question_dialog(question)
    
    def edit_question_dialog(self, question):
        """Open edit question dialog."""
        dialog = QuestionDialog(self, self.api_client, self.topics, question)
        if dialog.exec_() == QDialog.Accepted:
            self.load_questions()
    
    def delete_question(self, question):
        """Delete a question."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete question {question['id']}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.api_client.delete_question(question['id'])
                QMessageBox.information(self, "Success", "Question deleted successfully")
                self.load_questions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete question: {str(e)}")
    
    def manage_topics(self):
        """Open topic management dialog."""
        dialog = TopicManagementDialog(self, self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            # Reload topics and questions after topic management
            self.load_data()


class QuestionDialog(QDialog):
    """Dialog for creating/editing questions."""
    
    def __init__(self, parent, api_client, topics, question=None):
        super().__init__(parent)
        self.api_client = api_client
        self.topics = topics
        self.question = question
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Edit Question" if self.question else "Add Question")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        
        # Topic
        topic_layout = QHBoxLayout()
        topic_layout.addWidget(QLabel("Topic:"))
        self.topic_combo = QComboBox()
        for topic in self.topics:
            self.topic_combo.addItem(topic['name'], topic['id'])
        topic_layout.addWidget(self.topic_combo)
        layout.addLayout(topic_layout)
        
        # Type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(QUESTION_TYPES)
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Content
        layout.addWidget(QLabel("Content:"))
        self.content_edit = QTextEdit()
        layout.addWidget(self.content_edit)
        
        # Type-specific fields
        self.type_widget = QWidget()
        self.type_layout = QVBoxLayout()
        self.type_widget.setLayout(self.type_layout)
        layout.addWidget(self.type_widget)
        
        # Points
        points_layout = QHBoxLayout()
        points_layout.addWidget(QLabel("Points:"))
        self.points_spin = QDoubleSpinBox()
        self.points_spin.setMinimum(0.1)
        self.points_spin.setMaximum(100)
        self.points_spin.setValue(1.0)
        points_layout.addWidget(self.points_spin)
        layout.addLayout(points_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_question)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Load question data if editing
        if self.question:
            self.load_question_data()
        
        self.on_type_changed()
    
    def load_question_data(self):
        """Load question data into form."""
        # Find topic index
        for i in range(self.topic_combo.count()):
            if self.topic_combo.itemData(i) == self.question['topic_id']:
                self.topic_combo.setCurrentIndex(i)
                break
        
        # Set type
        type_index = self.type_combo.findText(self.question['type'])
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)
        
        self.content_edit.setPlainText(self.question['content'])
        self.points_spin.setValue(self.question['points'])
    
    def on_type_changed(self):
        """Handle type change."""
        # Clear type-specific widgets
        while self.type_layout.count():
            child = self.type_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        question_type = self.type_combo.currentText()
        
        if question_type == QUESTION_TYPE_MULTIPLE_CHOICE:
            self.type_layout.addWidget(QLabel("Choices (one per line):"))
            self.choices_edit = QTextEdit()
            self.choices_edit.setPlaceholderText("Option A\nOption B\nOption C\nOption D")
            self.choices_edit.setMaximumHeight(100)
            self.type_layout.addWidget(self.choices_edit)
            
            self.type_layout.addWidget(QLabel("Correct Answer:"))
            self.correct_answer_edit = QLineEdit()
            self.type_layout.addWidget(self.correct_answer_edit)
            
            # Load choices and correct answer if editing
            if self.question and self.question.get('correct_answer'):
                try:
                    import json
                    correct_answer_data = json.loads(self.question['correct_answer'])
                    if isinstance(correct_answer_data, dict):
                        # Load choices
                        choices = correct_answer_data.get('choices', [])
                        self.choices_edit.setPlainText('\n'.join(choices))
                        # Load correct answer
                        self.correct_answer_edit.setText(correct_answer_data.get('correct', ''))
                    else:
                        # Legacy format: just the correct answer string
                        self.correct_answer_edit.setText(self.question['correct_answer'])
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, treat as legacy format
                    self.correct_answer_edit.setText(self.question.get('correct_answer', ''))
        
        elif question_type == QUESTION_TYPE_CODE:
            self.type_layout.addWidget(QLabel("Test Cases (JSON format):"))
            self.test_cases_edit = QTextEdit()
            self.test_cases_edit.setPlaceholderText(
                '[{"input": "5", "output": "25"}, {"input": "10", "output": "100"}]'
            )
            self.test_cases_edit.setMaximumHeight(150)
            self.type_layout.addWidget(self.test_cases_edit)
            
            if self.question and self.question.get('test_cases'):
                import json
                self.test_cases_edit.setPlainText(json.dumps(self.question['test_cases'], indent=2))
    
    def save_question(self):
        """Save question."""
        topic_id = self.topic_combo.currentData()
        question_type = self.type_combo.currentText()
        content = self.content_edit.toPlainText()
        points = self.points_spin.value()
        
        if not topic_id or not content:
            QMessageBox.warning(self, "Error", "Please fill in all required fields")
            return
        
        question_data = {
            'topic_id': topic_id,
            'type': question_type,
            'content': content,
            'points': points
        }
        
        # Type-specific data
        if question_type == QUESTION_TYPE_MULTIPLE_CHOICE:
            if hasattr(self, 'choices_edit') and hasattr(self, 'correct_answer_edit'):
                # Get choices from text edit (one per line)
                choices_text = self.choices_edit.toPlainText().strip()
                if not choices_text:
                    QMessageBox.warning(self, "Error", "Please provide at least one choice")
                    return
                
                choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
                if not choices:
                    QMessageBox.warning(self, "Error", "Please provide at least one choice")
                    return
                
                correct_answer = self.correct_answer_edit.text().strip()
                if not correct_answer:
                    QMessageBox.warning(self, "Error", "Please specify the correct answer")
                    return
                
                if correct_answer not in choices:
                    QMessageBox.warning(self, "Error", "Correct answer must be one of the choices")
                    return
                
                # Store as JSON: {"choices": [...], "correct": "..."}
                import json
                question_data['correct_answer'] = json.dumps({
                    'choices': choices,
                    'correct': correct_answer
                })
        
        elif question_type == QUESTION_TYPE_CODE:
            if hasattr(self, 'test_cases_edit'):
                try:
                    import json
                    test_cases = json.loads(self.test_cases_edit.toPlainText())
                    question_data['test_cases'] = test_cases
                except:
                    QMessageBox.warning(self, "Error", "Invalid JSON format for test cases")
                    return
        
        try:
            if self.question:
                self.api_client.update_question(self.question['id'], question_data)
                QMessageBox.information(self, "Success", "Question updated successfully")
            else:
                self.api_client.create_question(question_data)
                QMessageBox.information(self, "Success", "Question created successfully")
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save question: {str(e)}")


class TopicManagementDialog(QDialog):
    """Dialog for managing topics."""
    
    def __init__(self, parent, api_client):
        super().__init__(parent)
        self.api_client = api_client
        self.topics = []
        self.init_ui()
        self.load_topics()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Manage Topics")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Topics")
        font = title.font()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        add_btn = QPushButton("Add Topic")
        add_btn.clicked.connect(self.add_topic)
        header.addWidget(add_btn)
        layout.addLayout(header)
        
        # Topics table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_topics(self):
        """Load topics."""
        try:
            self.topics = self.api_client.get_topics()
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load topics: {str(e)}")
    
    def populate_table(self):
        """Populate table with topics."""
        self.table.setRowCount(len(self.topics))
        
        for row, topic in enumerate(self.topics):
            self.table.setItem(row, 0, QTableWidgetItem(str(topic['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(topic['name']))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, t=topic: self.edit_topic(t))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("background-color: #dc3545; color: white;")
            delete_btn.clicked.connect(lambda checked, t=topic: self.delete_topic(t))
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.table.setCellWidget(row, 2, actions_widget)
    
    def add_topic(self):
        """Add a new topic."""
        dialog = TopicDialog(self, self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.load_topics()
    
    def edit_topic(self, topic):
        """Edit a topic."""
        dialog = TopicDialog(self, self.api_client, topic)
        if dialog.exec_() == QDialog.Accepted:
            self.load_topics()
    
    def delete_topic(self, topic):
        """Delete a topic."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete topic '{topic['name']}'?\n\n"
            f"This will fail if the topic has questions assigned to it.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.api_client.delete_topic(topic['id'])
                QMessageBox.information(self, "Success", "Topic deleted successfully")
                self.load_topics()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete topic: {str(e)}")


class TopicDialog(QDialog):
    """Dialog for creating/editing topics."""
    
    def __init__(self, parent, api_client, topic=None):
        super().__init__(parent)
        self.api_client = api_client
        self.topic = topic
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Edit Topic" if self.topic else "Add Topic")
        self.setMinimumSize(400, 200)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Topic Name:"))
        self.name_edit = QLineEdit()
        if self.topic:
            self.name_edit.setText(self.topic.get('name', ''))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Description
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        if self.topic:
            self.desc_edit.setPlainText(self.topic.get('description', ''))
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_topic)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_topic(self):
        """Save topic."""
        name = self.name_edit.text().strip()
        description = self.desc_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Topic name is required")
            return
        
        try:
            if self.topic:
                self.api_client.update_topic(self.topic['id'], name, description)
                QMessageBox.information(self, "Success", "Topic updated successfully")
            else:
                self.api_client.create_topic(name, description)
                QMessageBox.information(self, "Success", "Topic created successfully")
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save topic: {str(e)}")


class TopicManagementDialog(QDialog):
    """Dialog for managing topics."""
    
    def __init__(self, parent, api_client):
        super().__init__(parent)
        self.api_client = api_client
        self.topics = []
        self.init_ui()
        self.load_topics()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Manage Topics")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Topics")
        font = title.font()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        add_btn = QPushButton("Add Topic")
        add_btn.clicked.connect(self.add_topic)
        header.addWidget(add_btn)
        layout.addLayout(header)
        
        # Topics table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_topics(self):
        """Load topics."""
        try:
            self.topics = self.api_client.get_topics()
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load topics: {str(e)}")
    
    def populate_table(self):
        """Populate table with topics."""
        self.table.setRowCount(len(self.topics))
        
        for row, topic in enumerate(self.topics):
            self.table.setItem(row, 0, QTableWidgetItem(str(topic['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(topic['name']))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, t=topic: self.edit_topic(t))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setStyleSheet("background-color: #dc3545; color: white;")
            delete_btn.clicked.connect(lambda checked, t=topic: self.delete_topic(t))
            actions_layout.addWidget(delete_btn)
            
            actions_widget.setLayout(actions_layout)
            self.table.setCellWidget(row, 2, actions_widget)
    
    def add_topic(self):
        """Add a new topic."""
        dialog = TopicDialog(self, self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.load_topics()
    
    def edit_topic(self, topic):
        """Edit a topic."""
        dialog = TopicDialog(self, self.api_client, topic)
        if dialog.exec_() == QDialog.Accepted:
            self.load_topics()
    
    def delete_topic(self, topic):
        """Delete a topic."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete topic '{topic['name']}'?\n\n"
            f"This will fail if the topic has questions assigned to it.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.api_client.delete_topic(topic['id'])
                QMessageBox.information(self, "Success", "Topic deleted successfully")
                self.load_topics()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete topic: {str(e)}")


class TopicDialog(QDialog):
    """Dialog for creating/editing topics."""
    
    def __init__(self, parent, api_client, topic=None):
        super().__init__(parent)
        self.api_client = api_client
        self.topic = topic
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Edit Topic" if self.topic else "Add Topic")
        self.setMinimumSize(400, 200)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Topic Name:"))
        self.name_edit = QLineEdit()
        if self.topic:
            self.name_edit.setText(self.topic.get('name', ''))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Description
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        if self.topic:
            self.desc_edit.setPlainText(self.topic.get('description', ''))
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_topic)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_topic(self):
        """Save topic."""
        name = self.name_edit.text().strip()
        description = self.desc_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Topic name is required")
            return
        
        try:
            if self.topic:
                self.api_client.update_topic(self.topic['id'], name, description)
                QMessageBox.information(self, "Success", "Topic updated successfully")
            else:
                self.api_client.create_topic(name, description)
                QMessageBox.information(self, "Success", "Topic created successfully")
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save topic: {str(e)}")

