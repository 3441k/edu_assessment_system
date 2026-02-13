"""Grading window for lecturer."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QDialog, QTextEdit, 
                             QDoubleSpinBox, QMessageBox, QHeaderView, QSplitter)
from PyQt5.QtCore import Qt
from server.services.grader import auto_grade_code_answer
from server.app import db_session
from server.models import Answer


class GradingWindow(QWidget):
    """Grading window."""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.submissions = []
        self.current_submission = None
        self.init_ui()
        self.load_submissions()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Grading")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_submissions)
        header.addWidget(refresh_btn)
        layout.addLayout(header)
        
        # Submissions table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Test", "Student", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.grade_submission)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def load_submissions(self):
        """Load submissions."""
        try:
            self.submissions = self.api_client.get_submissions()
            # Filter to only submitted/graded
            self.submissions = [s for s in self.submissions if s.get('status') in ['submitted', 'graded']]
            self.populate_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load submissions: {str(e)}")
    
    def populate_table(self):
        """Populate table with submissions."""
        self.table.setRowCount(len(self.submissions))
        
        for row, submission in enumerate(self.submissions):
            self.table.setItem(row, 0, QTableWidgetItem(str(submission['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(submission.get('test_name', 'Unknown')))
            self.table.setItem(row, 2, QTableWidgetItem(submission.get('username', 'Unknown')))
            self.table.setItem(row, 3, QTableWidgetItem(submission.get('status', 'Unknown')))
            
            # Actions
            grade_btn = QPushButton("Grade")
            grade_btn.clicked.connect(lambda checked, s=submission: self.grade_submission_dialog(s))
            self.table.setCellWidget(row, 4, grade_btn)
    
    def grade_submission(self, row, col):
        """Grade submission (double-click)."""
        submission_id = int(self.table.item(row, 0).text())
        submission = next((s for s in self.submissions if s['id'] == submission_id), None)
        if submission:
            self.grade_submission_dialog(submission)
    
    def grade_submission_dialog(self, submission):
        """Open grading dialog."""
        dialog = GradingDialog(self, self.api_client, submission)
        dialog.exec_()
        self.load_submissions()


class GradingDialog(QDialog):
    """Dialog for grading a submission."""
    
    def __init__(self, parent, api_client, submission):
        super().__init__(parent)
        self.api_client = api_client
        self.submission = submission
        self.submission_data = None
        self.init_ui()
        self.load_submission_data()
    
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle(f"Grading - Submission {self.submission['id']}")
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel(f"Test: {self.submission.get('test_name', 'Unknown')}"))
        header.addWidget(QLabel(f"Student: {self.submission.get('username', 'Unknown')}"))
        header.addStretch()
        
        auto_grade_btn = QPushButton("Auto-Grade Code Questions")
        auto_grade_btn.clicked.connect(self.auto_grade_code)
        header.addWidget(auto_grade_btn)
        
        finalize_btn = QPushButton("Finalize Grading")
        finalize_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        finalize_btn.clicked.connect(self.finalize_grading)
        header.addWidget(finalize_btn)
        layout.addLayout(header)
        
        # Questions scroll area
        from PyQt5.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.questions_widget = QWidget()
        self.questions_layout = QVBoxLayout()
        self.questions_widget.setLayout(self.questions_layout)
        scroll.setWidget(self.questions_widget)
        layout.addWidget(scroll)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def load_submission_data(self):
        """Load submission data for grading."""
        try:
            self.submission_data = self.api_client.get_submission_for_grading(self.submission['id'])
            self.render_questions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load submission: {str(e)}")
    
    def render_questions(self):
        """Render questions with answers."""
        if not self.submission_data:
            return
        
        # Clear existing
        while self.questions_layout.count():
            child = self.questions_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        questions = self.submission_data.get('questions', [])
        
        for idx, q_data in enumerate(questions):
            card = self.create_question_card(q_data, idx)
            self.questions_layout.addWidget(card)
    
    def create_question_card(self, q_data, index):
        """Create a question card for grading."""
        from PyQt5.QtWidgets import QFrame, QGroupBox
        
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin: 5px;")
        
        layout = QVBoxLayout()
        
        # Question header
        header = QLabel(f"Question {q_data.get('order', index + 1)} ({q_data.get('points', 0)} points) - {q_data.get('type', 'unknown')}")
        font = header.font()
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)
        
        # Question content
        content = QLabel(q_data.get('content', ''))
        content.setWordWrap(True)
        layout.addWidget(content)
        
        # Answer
        answer = q_data.get('answer')
        if answer:
            answer_label = QLabel("Student Answer:")
            answer_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addWidget(answer_label)
            
            if q_data.get('type') == 'code':
                answer_text = QTextEdit()
                answer_text.setPlainText(answer.get('code', ''))
                answer_text.setReadOnly(True)
                answer_text.setMaximumHeight(200)
                layout.addWidget(answer_text)
            elif q_data.get('type') == 'diagram':
                if answer.get('diagram_data'):
                    diagram_label = QLabel("Diagram submitted")
                    layout.addWidget(diagram_label)
            else:
                answer_text = QTextEdit()
                answer_text.setPlainText(answer.get('answer_text', ''))
                answer_text.setReadOnly(True)
                layout.addWidget(answer_text)
        
        # Grading
        grading_layout = QHBoxLayout()
        grading_layout.addWidget(QLabel("Score:"))
        score_spin = QDoubleSpinBox()
        score_spin.setMinimum(0)
        score_spin.setMaximum(q_data.get('points', 100))
        score_spin.setValue(answer.get('score', 0) if answer else 0)
        score_spin.setSuffix(f" / {q_data.get('points', 0)}")
        grading_layout.addWidget(score_spin)
        grading_layout.addStretch()
        
        # Store reference for later
        q_data['_score_widget'] = score_spin
        
        layout.addLayout(grading_layout)
        
        # Feedback
        feedback_label = QLabel("Feedback:")
        layout.addWidget(feedback_label)
        feedback_edit = QTextEdit()
        feedback_edit.setPlainText(answer.get('feedback', '') if answer else '')
        feedback_edit.setMaximumHeight(100)
        layout.addWidget(feedback_edit)
        q_data['_feedback_widget'] = feedback_edit
        
        # Save button
        save_btn = QPushButton("Save Grade")
        save_btn.clicked.connect(lambda checked, q=q_data: self.save_grade(q))
        layout.addWidget(save_btn)
        
        card.setLayout(layout)
        return card
    
    def save_grade(self, q_data):
        """Save grade for a question."""
        answer = q_data.get('answer')
        if not answer or not answer.get('id'):
            return
        
        score = q_data['_score_widget'].value()
        feedback = q_data['_feedback_widget'].toPlainText()
        
        try:
            self.api_client.grade_answer(answer['id'], score, feedback)
            QMessageBox.information(self, "Success", "Grade saved")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save grade: {str(e)}")
    
    def auto_grade_code(self):
        """Auto-grade all code questions."""
        if not self.submission_data:
            return
        
        graded = 0
        for q_data in self.submission_data.get('questions', []):
            if q_data.get('type') == 'code':
                answer = q_data.get('answer')
                if answer and answer.get('code'):
                    # Auto-grade using the service
                    try:
                        from server.services.code_executor import grade_code_submission
                        test_cases = q_data.get('test_cases', [])
                        points = q_data.get('points', 0)
                        
                        result = grade_code_submission(answer['code'], test_cases, points)
                        
                        # Update UI
                        q_data['_score_widget'].setValue(result['score'])
                        q_data['_feedback_widget'].setPlainText(result['feedback'])
                        
                        # Save to database
                        self.api_client.grade_answer(answer['id'], result['score'], result['feedback'])
                        graded += 1
                    except Exception as e:
                        QMessageBox.warning(self, "Warning", f"Could not auto-grade question: {str(e)}")
        
        QMessageBox.information(self, "Auto-Grading Complete", f"Auto-graded {graded} code questions")
    
    def finalize_grading(self):
        """Finalize grading for the submission."""
        reply = QMessageBox.question(
            self, "Confirm Finalize",
            "Are you sure you want to finalize grading? This will calculate the final grade.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Save all grades first
                for q_data in self.submission_data.get('questions', []):
                    self.save_grade(q_data)
                
                # Finalize
                result = self.api_client.finalize_grading(self.submission['id'])
                QMessageBox.information(
                    self, "Success",
                    f"Grading finalized!\n\n"
                    f"Score: {result['total_score']} / {result['max_score']}\n"
                    f"Percentage: {result['percentage']:.1f}%"
                )
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to finalize grading: {str(e)}")

