"""Report generation service for PDF and CSV exports."""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import csv
import io
from datetime import datetime
from typing import List, Dict


def generate_pdf_report(data: Dict, output_path: str):
    """
    Generate a PDF report.
    
    Args:
        data: Dictionary with report data
        output_path: Path to save PDF
    """
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    title = Paragraph(data.get('title', 'Assessment Report'), title_style)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # Date
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    date_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(date_text, date_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Content sections
    if 'sections' in data:
        for section in data['sections']:
            # Section title
            section_title = Paragraph(section.get('title', ''), styles['Heading2'])
            story.append(section_title)
            story.append(Spacer(1, 0.1*inch))
            
            # Section content
            if 'table' in section:
                table_data = section['table']
                if table_data:
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 0.2*inch))
            
            if 'text' in section:
                text = Paragraph(section['text'], styles['Normal'])
                story.append(text)
                story.append(Spacer(1, 0.1*inch))
            
            story.append(Spacer(1, 0.2*inch))
    
    doc.build(story)


def generate_csv_grades(grades: List[Dict], output_path: str):
    """
    Generate CSV file with grades.
    
    Args:
        grades: List of grade dictionaries
        output_path: Path to save CSV
    """
    if not grades:
        return
    
    fieldnames = ['student_id', 'username', 'test_name', 'total_score', 'max_score', 'percentage', 'graded_at']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for grade in grades:
            writer.writerow({
                'student_id': grade.get('student_id', ''),
                'username': grade.get('username', ''),
                'test_name': grade.get('test_name', ''),
                'total_score': grade.get('total_score', 0),
                'max_score': grade.get('max_score', 0),
                'percentage': f"{grade.get('percentage', 0):.2f}%",
                'graded_at': grade.get('graded_at', '')
            })

