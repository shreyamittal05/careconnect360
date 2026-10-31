import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

TIME_SLOTS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ACTIVE_STATUSES = ("pending", "confirmed")
BOOKING_WINDOW_DAYS = 30
GST_RATE = 0.18
SPECIALIZATIONS = [
    "Cardiologist",
    "General Physician",
    "Dermatologist",
    "Neurologist",
    "Pediatrician",
]
MEDICAL_RECORD_TYPES = [
    "Consultation summary",
    "Lab report",
    "Scan or X-ray",
    "Vaccination",
    "Discharge summary",
    "Other",
]
PAYMENT_METHODS = ["UPI", "Credit / Debit Card", "Net Banking", "Wallet"]


class Config:
    SECRET_KEY = os.environ.get("CARECONNECT_SECRET_KEY", "careconnect360-dev-key-change-me")
    oracle_dsn = os.environ.get("ORACLE_DSN")
    oracle_user = os.environ.get("ORACLE_USER")
    oracle_password = os.environ.get("ORACLE_PASSWORD")
    if oracle_dsn and oracle_user and oracle_password:
        SQLALCHEMY_DATABASE_URI = (
            f"oracle+oracledb://{oracle_user}:{oracle_password}@{oracle_dsn}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'careconnect360.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
