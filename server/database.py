"""Database configuration and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/assessment.db")

# Database setup
engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)
db_session = scoped_session(sessionmaker(bind=engine))

