from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


BACKEND_BASE_URL = "127.0.0.1"
BACKEND_PORT = 8001

BACKEND_URL = f"http://{BACKEND_BASE_URL}:{BACKEND_PORT}"


SQLALCHEMY_DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

BACKGROUND_COLOR = "#f8f9fa"
BORDER_COLOR = "#e9ecef"
PRIMARY_COLOR = "#5e5ce6"
SECONDARY_COLOR = "#ff8c00"
NEGATIVE_COLOR = "#ff453a"
POSITIVE_COLOR = "#32d74b"
BACKGROUND_COLOR = "#f2f2f7"
CARD_BACKGROUND_COLOR = "#d4d4e4"
TEXT_PRIMARY_COLOR = "#1c1c1e"
TEXT_SECONDARY_COLOR = "#6e6e73"
BORDER_COLOR = "#e5e5ea"
