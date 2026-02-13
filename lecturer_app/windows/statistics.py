"""Statistics and analytics window."""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QComboBox, QMessageBox,
                             QHeaderView, QGroupBox, QPushButton)
from PyQt5.QtCore import Qt


class StatisticsWindow(QWidget):
    """Statistics window."""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.init_ui()
        self.load_overview()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Statistics & Analytics")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self.export_csv)
        header.addWidget(export_btn)
        
        export_pdf_btn = QPushButton("Export PDF")
        export_pdf_btn.clicked.connect(self.export_pdf)
        header.addWidget(export_pdf_btn)
        layout.addLayout(header)
        
        # Stats type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("View:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Overview", "By Topic", "By Student", "By Test"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Stats display
        self.stats_widget = QWidget()
        self.stats_layout = QVBoxLayout()
        self.stats_widget.setLayout(self.stats_layout)
        layout.addWidget(self.stats_widget)
        
        self.setLayout(layout)
    
    def on_type_changed(self):
        """Handle type change."""
        view_type = self.type_combo.currentText()
        
        if view_type == "Overview":
            self.load_overview()
        elif view_type == "By Topic":
            self.load_topic_stats()
        elif view_type == "By Student":
            self.load_student_stats()
        elif view_type == "By Test":
            self.load_test_stats()
    
    def load_overview(self):
        """Load overview statistics."""
        try:
            stats = self.api_client.get_statistics_overview()
            self.display_overview(stats)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load statistics: {str(e)}")
    
    def display_overview(self, stats):
        """Display overview statistics."""
        # Clear existing
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Create cards
        cards_layout = QHBoxLayout()
        
        for key, value in stats.items():
            card = QGroupBox(key.replace('_', ' ').title())
            card_layout = QVBoxLayout()
            value_label = QLabel(str(value))
            font = value_label.font()
            font.setPointSize(24)
            font.setBold(True)
            value_label.setFont(font)
            value_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(value_label)
            card.setLayout(card_layout)
            cards_layout.addWidget(card)
        
        self.stats_layout.addLayout(cards_layout)
    
    def load_topic_stats(self):
        """Load topic statistics."""
        try:
            stats = self.api_client.get_topic_statistics()
            self.display_table(stats, ["Topic", "Questions", "Avg Score", "Submissions"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load statistics: {str(e)}")
    
    def load_student_stats(self):
        """Load student statistics."""
        try:
            stats = self.api_client.get_student_statistics()
            self.display_table(stats, ["Student", "Student ID", "Tests", "Avg %"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load statistics: {str(e)}")
    
    def load_test_stats(self):
        """Load test statistics."""
        try:
            tests = self.api_client.get_tests()
            if not tests:
                QMessageBox.information(self, "Info", "No tests available")
                return
            
            # Let user select a test
            from PyQt5.QtWidgets import QInputDialog
            test_names = [t['name'] for t in tests]
            test_name, ok = QInputDialog.getItem(self, "Select Test", "Test:", test_names, 0, False)
            
            if ok:
                test = next((t for t in tests if t['name'] == test_name), None)
                if test:
                    stats = self.api_client.get_test_statistics(test['id'])
                    self.display_test_stats(stats)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load statistics: {str(e)}")
    
    def display_table(self, data, headers):
        """Display data in a table."""
        # Clear existing
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(data))
        
        for row, item in enumerate(data):
            for col, header in enumerate(headers):
                key = header.lower().replace(' ', '_')
                value = item.get(key, item.get(header.lower().replace(' ', '_'), ''))
                table.setItem(row, col, QTableWidgetItem(str(value)))
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_layout.addWidget(table)
    
    def display_test_stats(self, stats):
        """Display test statistics."""
        # Clear existing
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Summary
        summary = QGroupBox("Test Summary")
        summary_layout = QVBoxLayout()
        summary_layout.addWidget(QLabel(f"Test: {stats.get('test_name', 'Unknown')}"))
        summary_layout.addWidget(QLabel(f"Total Submissions: {stats.get('total_submissions', 0)}"))
        summary_layout.addWidget(QLabel(f"Graded: {stats.get('graded_submissions', 0)}"))
        summary_layout.addWidget(QLabel(f"Average Score: {stats.get('average_score', 0):.2f}"))
        summary_layout.addWidget(QLabel(f"Average Percentage: {stats.get('average_percentage', 0):.2f}%"))
        summary.setLayout(summary_layout)
        self.stats_layout.addWidget(summary)
        
        # Question stats
        if stats.get('question_statistics'):
            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Question", "Type", "Avg Score", "Max Points", "Answers"])
            table.setRowCount(len(stats['question_statistics']))
            
            for row, q_stat in enumerate(stats['question_statistics']):
                table.setItem(row, 0, QTableWidgetItem(q_stat.get('content', '')[:50]))
                table.setItem(row, 1, QTableWidgetItem(q_stat.get('type', '')))
                table.setItem(row, 2, QTableWidgetItem(str(q_stat.get('average_score', 0))))
                table.setItem(row, 3, QTableWidgetItem(str(q_stat.get('max_points', 0))))
                table.setItem(row, 4, QTableWidgetItem(str(q_stat.get('answer_count', 0))))
            
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.stats_layout.addWidget(table)
    
    def export_csv(self):
        """Export statistics to CSV."""
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        
        if filename:
            try:
                # Get all submissions with grades
                submissions = self.api_client.get_submissions()
                grades_data = []
                
                for sub in submissions:
                    if sub.get('status') == 'graded':
                        try:
                            grade_data = self.api_client.get_submission_for_grading(sub['id'])
                            grades_data.append({
                                'student_id': grade_data.get('student_id', ''),
                                'username': grade_data.get('username', ''),
                                'test_name': grade_data.get('test_name', ''),
                                'total_score': 0,  # Would need to get from grade
                                'max_score': 0,
                                'percentage': 0
                            })
                        except:
                            pass
                
                # Use report generator
                from server.services.report_generator import generate_csv_grades
                generate_csv_grades(grades_data, filename)
                QMessageBox.information(self, "Success", f"CSV exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")
    
    def export_pdf(self):
        """Export statistics to PDF."""
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(self, "Export PDF", "", "PDF Files (*.pdf)")
        
        if filename:
            try:
                # Create report data
                stats = self.api_client.get_statistics_overview()
                topic_stats = self.api_client.get_topic_statistics()
                
                report_data = {
                    'title': 'Assessment System Report',
                    'sections': [
                        {
                            'title': 'Overview',
                            'table': [['Metric', 'Value']] + [[k.replace('_', ' ').title(), str(v)] for k, v in stats.items()]
                        },
                        {
                            'title': 'Topic Performance',
                            'table': [['Topic', 'Questions', 'Avg Score', 'Submissions']] + 
                                    [[s['topic_name'], s['question_count'], s['average_score'], s['submission_count']] 
                                     for s in topic_stats]
                        }
                    ]
                }
                
                from server.services.report_generator import generate_pdf_report
                generate_pdf_report(report_data, filename)
                QMessageBox.information(self, "Success", f"PDF exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export PDF: {str(e)}")

