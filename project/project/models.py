from datetime import date, datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from config import WEEKDAYS

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    date_of_birth = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    doctor = db.relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_doctor(self):
        return self.role == "doctor"

    @property
    def initials(self):
        parts = self.full_name.replace("Dr.", "").split()
        return "".join(part[0] for part in parts[:2]).upper()


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    specialization = db.Column(db.String(80), nullable=False, index=True)
    qualification = db.Column(db.String(160), nullable=False)
    experience_years = db.Column(db.Integer, nullable=False, default=0)
    consultation_fee = db.Column(db.Integer, nullable=False, default=500)
    rating = db.Column(db.Float, nullable=False, default=4.5)
    availability_days = db.Column(db.String(60), nullable=False, default="Mon,Tue,Wed,Thu,Fri")
    bio = db.Column(db.Text, nullable=False, default="")
    photo_url = db.Column(db.String(300), nullable=False, default="")

    user = db.relationship("User", back_populates="doctor")
    appointments = db.relationship("Appointment", back_populates="doctor")

    @property
    def name(self):
        return self.user.full_name

    @property
    def days_list(self):
        return [day.strip() for day in self.availability_days.split(",") if day.strip()]

    def works_on(self, day):
        return WEEKDAYS[day.weekday()] in self.days_list


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    time_slot = db.Column(db.String(5), nullable=False)
    mode = db.Column(db.String(10), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    diagnosis = db.Column(db.String(255), nullable=False, default="")
    doctor_notes = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    patient = db.relationship("User")
    doctor = db.relationship("Doctor", back_populates="appointments")
    prescriptions = db.relationship(
        "Prescription", back_populates="appointment", cascade="all, delete-orphan"
    )
    invoice = db.relationship(
        "Invoice", back_populates="appointment", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def code(self):
        return f"APT-{self.id:05d}"

    @property
    def is_upcoming(self):
        return self.appointment_date >= date.today() and self.status in ("pending", "confirmed")


class Prescription(db.Model):
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    diagnosis = db.Column(db.String(255), nullable=False)
    medicine_name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(60), nullable=False)
    frequency = db.Column(db.String(60), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    instructions = db.Column(db.Text, nullable=False, default="")
    prescription_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    appointment = db.relationship("Appointment", back_populates="prescriptions")
    patient = db.relationship("User")
    doctor = db.relationship("Doctor")

    @property
    def code(self):
        return f"RX-{self.id:05d}"

    @property
    def valid_until(self):
        return self.prescription_date + timedelta(days=self.duration_days)

    @property
    def is_active(self):
        return self.valid_until >= date.today()


class MedicalRecord(db.Model):
    __tablename__ = "medical_records"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    record_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    record_date = db.Column(db.Date, nullable=False, default=date.today)
    symptoms = db.Column(db.Text, nullable=False, default="")
    diagnosis = db.Column(db.String(255), nullable=False, default="")
    notes = db.Column(db.Text, nullable=False, default="")
    document_filename = db.Column(db.String(255))
    document_original_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    patient = db.relationship("User")


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    consultation_fee = db.Column(db.Integer, nullable=False)
    tax_amount = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="unpaid", index=True)
    payment_method = db.Column(db.String(30), nullable=False, default="")
    transaction_ref = db.Column(db.String(40), nullable=False, default="")
    payment_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    appointment = db.relationship("Appointment", back_populates="invoice")
    patient = db.relationship("User")
    doctor = db.relationship("Doctor")
