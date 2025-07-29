from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

storage_dir = os.path.dirname(settings.DATABASE_URL.split("///")[1])
os.makedirs(storage_dir, exist_ok=True)
