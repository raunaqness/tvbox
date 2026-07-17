from sqlalchemy import create_engine, Column, String, DateTime, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./jobs.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True) # task_id
    gid = Column(String, index=True)
    title = Column(String)
    status = Column(String) # downloading, uploading, completed, failed
    progress_string = Column(String, default="0%")
    download_speed = Column(String, default="0 B/s")
    fallback_magnets = Column(String, default="[]")
    media_type = Column(String, default="movie") # "movie" or "tv"
    poster_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def ensure_job_schema():
    """Add columns introduced after the initial SQLite database was created."""
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("jobs")}
    if "poster_path" not in existing_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN poster_path VARCHAR"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
