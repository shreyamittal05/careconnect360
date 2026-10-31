import re
from datetime import date, datetime, timedelta

from config import BOOKING_WINDOW_DAYS, MEDICAL_RECORD_TYPES, SPECIALIZATIONS, TIME_SLOTS, WEEKDAYS

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9 ()-]{7,20}$")


def _text(form, key, label, max_length, required=True):
    value = (form.get(key) or "").strip()
    if not value:
        return value, f"{label} is required." if required else None
    if len(value) > max_length:
        return value, f"{label} must be {max_length} characters or fewer."
    return value, None


def _whole_number(form, key, label, low, high):
    raw = (form.get(key) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return None, f"{label} must be a whole number."
    if not low <= value <= high:
        return None, f"{label} must be between {low} and {high}."
    return value, None


def _date(form, key, label):
    raw = (form.get(key) or "").strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date(), None
    except ValueError:
        return None, f"Enter a valid {label.lower()}."


def validate_registration(form):
    errors = []
    role = form.get("role", "patient")
    if role not in ("patient", "doctor"):
        errors.append("Choose a valid account type.")

    email = (form.get("email") or "").strip().lower()
    if not EMAIL_PATTERN.match(email) or len(email) > 120:
        errors.append("Enter a valid email address.")

    phone = (form.get("phone") or "").strip()
    if not PHONE_PATTERN.match(phone):
        errors.append("Enter a valid phone number.")

    password = form.get("password") or ""
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != (form.get("confirm_password") or ""):
        errors.append("Passwords do not match.")

    full_name, error = _text(form, "full_name", "Full name", 120)
    if error:
        errors.append(error)

    data = {"role": role, "full_name": full_name, "email": email, "phone": phone, "password": password}

    if role == "patient":
        dob_raw = (form.get("date_of_birth") or "").strip()
        data["date_of_birth"] = None
        if dob_raw:
            dob, error = _date(form, "date_of_birth", "date of birth")
            if error or dob > date.today():
                errors.append("Enter a valid date of birth in the past.")
            data["date_of_birth"] = dob
        return data, errors

    data.update(_doctor_fields(form, errors))
    return data, errors


def _doctor_fields(form, errors):
    specialization = (form.get("specialization") or "").strip()
    if specialization not in SPECIALIZATIONS:
        errors.append("Choose a valid specialization.")
    qualification, error = _text(form, "qualification", "Qualification", 160)
    if error:
        errors.append(error)
    experience, error = _whole_number(form, "experience_years", "Experience", 0, 60)
    if error:
        errors.append(error)
    fee, error = _whole_number(form, "consultation_fee", "Consultation fee", 100, 10000)
    if error:
        errors.append(error)
    days = _availability_days(form, errors)
    bio, error = _text(form, "bio", "Bio", 600, required=False)
    if error:
        errors.append(error)
    return {
        "specialization": specialization,
        "qualification": qualification,
        "experience_years": experience,
        "consultation_fee": fee,
        "availability_days": days,
        "bio": bio,
    }


def _availability_days(form, errors):
    selected = [day for day in form.getlist("availability_days") if day in WEEKDAYS]
    if not selected:
        errors.append("Select at least one day you are available.")
    return ",".join(day for day in WEEKDAYS if day in selected)


def validate_login(form):
    errors = []
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    if not email or not password:
        errors.append("Enter your email and password.")
    return {"email": email, "password": password}, errors


def validate_profile(form, is_doctor):
    errors = []
    full_name, error = _text(form, "full_name", "Full name", 120)
    if error:
        errors.append(error)
    phone = (form.get("phone") or "").strip()
    if not PHONE_PATTERN.match(phone):
        errors.append("Enter a valid phone number.")
    data = {"full_name": full_name, "phone": phone}
    if is_doctor:
        data.update(_doctor_fields(form, errors))
    return data, errors


def validate_booking(form):
    errors = []
    doctor_id, error = _whole_number(form, "doctor_id", "Doctor", 1, 10**9)
    if error:
        errors.append("Select a doctor.")

    day, error = _date(form, "appointment_date", "appointment date")
    today = date.today()
    if error:
        errors.append(error)
    elif day < today or day > today + timedelta(days=BOOKING_WINDOW_DAYS):
        errors.append(f"Choose a date within the next {BOOKING_WINDOW_DAYS} days.")

    slot = (form.get("time_slot") or "").strip()
    if slot not in TIME_SLOTS:
        errors.append("Choose an available time slot.")

    mode = (form.get("mode") or "").strip()
    if mode not in ("video", "audio"):
        errors.append("Choose video or audio consultation.")

    symptoms, error = _text(form, "symptoms", "Symptoms or reason for consultation", 500)
    if not error and len(symptoms) < 10:
        error = "Describe your symptoms in at least 10 characters."
    if error:
        errors.append(error)

    data = {
        "doctor_id": doctor_id,
        "appointment_date": day,
        "time_slot": slot,
        "mode": mode,
        "symptoms": symptoms,
    }
    return data, errors


def validate_prescription(form):
    errors = []
    appointment_id, error = _whole_number(form, "appointment_id", "Appointment", 1, 10**9)
    if error:
        errors.append("Select an appointment for this prescription.")
    diagnosis, error = _text(form, "diagnosis", "Diagnosis", 255)
    if error:
        errors.append(error)
    medicine_name, error = _text(form, "medicine_name", "Medicine name", 120)
    if error:
        errors.append(error)
    dosage, error = _text(form, "dosage", "Dosage", 60)
    if error:
        errors.append(error)
    frequency, error = _text(form, "frequency", "Frequency", 60)
    if error:
        errors.append(error)
    duration, error = _whole_number(form, "duration_days", "Duration", 1, 365)
    if error:
        errors.append(error)
    instructions, error = _text(form, "instructions", "Instructions", 1000, required=False)
    if error:
        errors.append(error)
    prescription_date, error = _date(form, "prescription_date", "prescription date")
    if error:
        errors.append(error)
    data = {
        "appointment_id": appointment_id,
        "diagnosis": diagnosis,
        "medicine_name": medicine_name,
        "dosage": dosage,
        "frequency": frequency,
        "duration_days": duration,
        "instructions": instructions,
        "prescription_date": prescription_date,
    }
    return data, errors


def validate_medical_record(form):
    errors = []
    record_type = (form.get("record_type") or "").strip()
    if record_type not in MEDICAL_RECORD_TYPES:
        errors.append("Choose a valid record type.")
    title, error = _text(form, "title", "Title", 120)
    if error:
        errors.append(error)
    record_date, error = _date(form, "record_date", "record date")
    if error:
        errors.append(error)
    elif record_date > date.today():
        errors.append("Record date cannot be in the future.")
    symptoms, error = _text(form, "symptoms", "Symptoms", 1000, required=False)
    if error:
        errors.append(error)
    diagnosis, error = _text(form, "diagnosis", "Diagnosis", 255, required=False)
    if error:
        errors.append(error)
    notes, error = _text(form, "notes", "Notes", 1000, required=False)
    if error:
        errors.append(error)
    data = {
        "record_type": record_type,
        "title": title,
        "record_date": record_date,
        "symptoms": symptoms,
        "diagnosis": diagnosis,
        "notes": notes,
    }
    return data, errors


def validate_consultation_notes(form):
    errors = []
    diagnosis, error = _text(form, "diagnosis", "Diagnosis", 255)
    if error:
        errors.append(error)
    notes, error = _text(form, "doctor_notes", "Consultation notes", 2000, required=False)
    if error:
        errors.append(error)
    return {"diagnosis": diagnosis, "doctor_notes": notes}, errors


def validate_upload(file, allowed_extensions):
    if file is None or not file.filename:
        return None
    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in allowed_extensions:
        return "Upload a PDF, PNG or JPG document."
    return None
