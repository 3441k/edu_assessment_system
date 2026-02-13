"""Initialize the database with schema and default data."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.models import Base, User, Topic
from shared.constants import ROLE_LECTURER, ROLE_STUDENT
import bcrypt
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "database/assessment.db")


def init_database():
    """Initialize the database with schema."""
    # Create database directory if it doesn't exist
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Create engine and tables
    engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if database is already initialized
        existing_user = session.query(User).first()
        if existing_user:
            print("Database already initialized.")
            return
        
        # Create default lecturer account (password: admin)
        password_hash = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        lecturer = User(
            username="admin",
            password_hash=password_hash,
            role=ROLE_LECTURER
        )
        session.add(lecturer)
        
        # Create a default topic
        default_topic = Topic(
            name="General",
            description="General questions and topics"
        )
        session.add(default_topic)
        
        session.commit()
        print(f"Database initialized successfully at {DATABASE_PATH}")
        print("Default lecturer account created:")
        print("  Username: admin")
        print("  Password: admin")
        print("  (Please change the password after first login)")
        
    except Exception as e:
        session.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    init_database()

