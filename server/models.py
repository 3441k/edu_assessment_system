"""Database models for the assessment system."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from shared.constants import (
    ROLE_LECTURER, ROLE_STUDENT,
    QUESTION_TYPE_MULTIPLE_CHOICE, QUESTION_TYPE_CODE, QUESTION_TYPE_DIAGRAM, QUESTION_TYPE_TEXT,
    SUBMISSION_STATUS_NOT_STARTED, SUBMISSION_STATUS_SUBMITTED, SUBMISSION_STATUS_GRADED
)

Base = declarative_base()


class User(Base):
    """User model for students and lecturers."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'lecturer' or 'student'
    student_id = Column(String(50), unique=True, nullable=True)  # Only for students
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submissions = relationship("Submission", back_populates="user")


class Topic(Base):
    """Topic model for organizing questions."""
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = relationship("Question", back_populates="topic")


class Question(Base):
    """Question model for the question bank."""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    type = Column(String(50), nullable=False)  # multiple_choice, code, diagram, text
    content = Column(Text, nullable=False)  # Question text/content
    correct_answer = Column(Text, nullable=True)  # JSON for multiple choice, expected output for code
    test_cases = Column(JSON, nullable=True)  # For code questions: [{"input": "...", "output": "..."}]
    points = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    topic = relationship("Topic", back_populates="questions")
    test_questions = relationship("TestQuestion", back_populates="question")
    answers = relationship("Answer", back_populates="question")


class Test(Base):
    """Test model for test definitions."""
    __tablename__ = "tests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    time_limit = Column(Integer, nullable=True)  # Time limit in minutes, None = no limit
    attempts_allowed = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)
    
    # Relationships
    test_questions = relationship("TestQuestion", back_populates="test", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="test")


class TestQuestion(Base):
    """Many-to-many relationship between tests and questions."""
    __tablename__ = "test_questions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    order = Column(Integer, nullable=False)  # Order of question in test
    points = Column(Float, nullable=True)  # Override question points if specified
    
    # Relationships
    test = relationship("Test", back_populates="test_questions")
    question = relationship("Question", back_populates="test_questions")


class Submission(Base):
    """Submission model for student test submissions."""
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    status = Column(String(50), default=SUBMISSION_STATUS_NOT_STARTED, nullable=False)
    
    # Relationships
    test = relationship("Test", back_populates="submissions")
    user = relationship("User", back_populates="submissions")
    answers = relationship("Answer", back_populates="submission", cascade="all, delete-orphan")
    grade = relationship("Grade", back_populates="submission", uselist=False)


class Answer(Base):
    """Answer model for individual question answers."""
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text, nullable=True)  # For multiple choice and text questions
    code = Column(Text, nullable=True)  # For code questions
    diagram_data = Column(Text, nullable=True)  # Base64 or JSON for diagram questions
    score = Column(Float, nullable=True)  # Points awarded
    feedback = Column(Text, nullable=True)  # Feedback from lecturer
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    submission = relationship("Submission", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class Grade(Base):
    """Grade model for final test grades."""
    __tablename__ = "grades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), unique=True, nullable=False)
    total_score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    graded_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Lecturer who graded
    graded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("Submission", back_populates="grade")

