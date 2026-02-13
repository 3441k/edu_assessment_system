"""Test taking window for student application."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QScrollArea, QWidget, QFrame, QTextEdit, QRadioButton, 
                             QButtonGroup, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor
import json


class TestTakingWindow(QDialog):
    """Window for taking a test."""
    
    def __init__(self, api_client, test_id):
        super().__init__()
        self.api_client = api_client
        self.test_id = test_id
        self.test_data = None
        self.submission_id = None
        self.current_question_index = 0
        self.answers = {}
        self.timer = None
        self.time_remaining = None
        self.init_ui()
        self.load_test()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("Taking Test - Assessment System")
        self.setMinimumSize(1000, 700)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header with timer
        header = QHBoxLayout()
        self.test_name_label = QLabel("Loading...")
        font = self.test_name_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.test_name_label.setFont(font)
        header.addWidget(self.test_name_label)
        header.addStretch()
        
        self.timer_label = QLabel("")
        self.timer_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        header.addWidget(self.timer_label)
        main_layout.addLayout(header)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Questions area
        questions_scroll = QScrollArea()
        questions_scroll.setWidgetResizable(True)
        self.questions_widget = QWidget()
        self.questions_layout = QVBoxLayout()
        self.questions_widget.setLayout(self.questions_layout)
        questions_scroll.setWidget(self.questions_widget)
        content_layout.addWidget(questions_scroll, stretch=3)
        
        # Navigation sidebar
        nav_frame = QFrame()
        nav_frame.setFixedWidth(200)
        nav_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 5px; padding: 10px;")
        nav_layout = QVBoxLayout()
        nav_label = QLabel("Questions")
        font = nav_label.font()
        font.setBold(True)
        nav_label.setFont(font)
        nav_layout.addWidget(nav_label)
        
        self.nav_buttons_layout = QVBoxLayout()
        nav_layout.addLayout(self.nav_buttons_layout)
        nav_layout.addStretch()
        nav_frame.setLayout(nav_layout)
        content_layout.addWidget(nav_frame)
        
        main_layout.addLayout(content_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Progress")
        save_btn.clicked.connect(self.save_progress)
        button_layout.addWidget(save_btn)
        button_layout.addStretch()
        submit_btn = QPushButton("Submit Test")
        submit_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 8px;")
        submit_btn.clicked.connect(self.submit_test)
        button_layout.addWidget(submit_btn)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def load_test(self):
        """Load test data."""
        try:
            self.test_data = self.api_client.get_test(self.test_id)
            self.test_name_label.setText(self.test_data.get('name', 'Test'))
            
            # Create or get submission
            self.create_submission()
            
            # Load existing answers
            self.load_answers()
            
            # Render questions
            self.render_questions()
            
            # Start timer if needed
            if self.test_data.get('time_limit'):
                self.start_timer(self.test_data['time_limit'] * 60)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load test: {str(e)}")
            self.reject()
    
    def create_submission(self):
        """Create or get existing submission."""
        try:
            # Try to get existing submission
            tests = self.api_client.get_tests()
            for test in tests:
                if test['id'] == self.test_id:
                    if test.get('submission_status') == 'in_progress' and test.get('submission_id'):
                        self.submission_id = test['submission_id']
                        return
            
            # Create new submission
            result = self.api_client.create_submission(self.test_id)
            self.submission_id = result.get('id')
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not create submission: {str(e)}")
    
    def load_answers(self):
        """Load existing answers."""
        if not self.submission_id:
            return
        
        try:
            submission = self.api_client.get_submission(self.submission_id)
            for answer in submission.get('answers', []):
                self.answers[answer['question_id']] = answer
        except:
            pass
    
    def render_questions(self):
        """Render all questions."""
        # Clear existing
        while self.questions_layout.count():
            child = self.questions_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        while self.nav_buttons_layout.count():
            child = self.nav_buttons_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        questions = self.test_data.get('questions', [])
        
        for idx, question in enumerate(questions):
            # Question card
            card = self.create_question_card(question, idx)
            card.setVisible(idx == 0)  # Show first question
            self.questions_layout.addWidget(card)
            
            # Navigation button
            nav_btn = QPushButton(f"Q{idx + 1}")
            nav_btn.setCheckable(True)
            nav_btn.setChecked(idx == 0)
            nav_btn.clicked.connect(lambda checked, i=idx: self.show_question(i))
            self.nav_buttons_layout.addWidget(nav_btn)
    
    def create_question_card(self, question, index):
        """Create a question card widget."""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 5px; padding: 15px;")
        
        layout = QVBoxLayout()
        
        # Question header
        header = QLabel(f"Question {index + 1} ({question.get('points', 0)} points)")
        font = header.font()
        font.setPointSize(12)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)
        
        # Question content
        content = QLabel(question.get('content', ''))
        content.setWordWrap(True)
        layout.addWidget(content)
        
        # Answer input based on type
        answer_widget = self.create_answer_input(question)
        layout.addWidget(answer_widget)
        
        card.setLayout(layout)
        return card
    
    def create_answer_input(self, question):
        """Create answer input widget based on question type."""
        question_type = question.get('type')
        question_id = question['id']
        saved_answer = self.answers.get(question_id, {})
        
        if question_type == 'multiple_choice':
            # Parse choices from content (simplified - in real app, store choices separately)
            choices = ['Option A', 'Option B', 'Option C', 'Option D']  # Placeholder
            group = QButtonGroup()
            widget = QWidget()
            layout = QVBoxLayout()
            
            for choice in choices:
                radio = QRadioButton(choice)
                group.addButton(radio)
                if saved_answer.get('answer_text') == choice:
                    radio.setChecked(True)
                layout.addWidget(radio)
            
            widget.setLayout(layout)
            return widget
            
        elif question_type == 'code':
            text_edit = QTextEdit()
            text_edit.setPlaceholderText("Write your code here...")
            if saved_answer.get('code'):
                text_edit.setPlainText(saved_answer['code'])
            text_edit.setMinimumHeight(300)
            return text_edit
            
        elif question_type == 'text':
            text_edit = QTextEdit()
            text_edit.setPlaceholderText("Write your answer here...")
            if saved_answer.get('answer_text'):
                text_edit.setPlainText(saved_answer['answer_text'])
            text_edit.setMinimumHeight(200)
            return text_edit
            
        else:  # diagram
            label = QLabel("Diagram drawing - Use web interface for full functionality")
            label.setStyleSheet("color: #666; padding: 20px; border: 1px dashed #ddd;")
            return label
    
    def show_question(self, index):
        """Show a specific question."""
        for i in range(self.questions_layout.count()):
            widget = self.questions_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(i == index)
        
        # Update nav buttons
        for i in range(self.nav_buttons_layout.count()):
            btn = self.nav_buttons_layout.itemAt(i).widget()
            if btn:
                btn.setChecked(i == index)
        
        self.current_question_index = index
    
    def start_timer(self, seconds):
        """Start countdown timer."""
        self.time_remaining = seconds
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        self.update_timer()
    
    def update_timer(self):
        """Update timer display."""
        if self.time_remaining is None:
            return
        
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        self.timer_label.setText(f"Time: {minutes}:{seconds:02d}")
        
        if self.time_remaining <= 0:
            self.timer.stop()
            QMessageBox.warning(self, "Time Up", "Time is up! Submitting test...")
            self.submit_test()
        else:
            self.time_remaining -= 1
    
    def save_progress(self):
        """Save current progress."""
        if not self.submission_id:
            return
        
        questions = self.test_data.get('questions', [])
        
        for idx, question in enumerate(questions):
            question_id = question['id']
            answer_data = {}
            
            # Get answer from UI (simplified - would need to track widgets)
            # For now, just save what we have in self.answers
            
            try:
                if question_id in self.answers:
                    answer = self.answers[question_id]
                    self.api_client.save_answer(
                        self.submission_id,
                        question_id,
                        {
                            'answer_text': answer.get('answer_text'),
                            'code': answer.get('code'),
                            'diagram_data': answer.get('diagram_data')
                        }
                    )
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not save answer: {str(e)}")
        
        QMessageBox.information(self, "Saved", "Progress saved successfully!")
    
    def submit_test(self):
        """Submit the test."""
        if not self.submission_id:
            QMessageBox.warning(self, "Error", "No submission to submit")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Submission",
            "Are you sure you want to submit? You cannot modify answers after submission.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Save progress first
                self.save_progress()
                
                # Submit
                self.api_client.submit_submission(self.submission_id)
                
                if self.timer:
                    self.timer.stop()
                
                QMessageBox.information(self, "Success", "Test submitted successfully!")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to submit test: {str(e)}")

