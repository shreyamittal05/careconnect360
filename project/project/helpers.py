import secrets
import uuid
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import abort, current_app, flash, g, redirect, request, session, url_for
from werkzeug.utils import secure_filename

from config import ACTIVE_STATUSES, GST_RATE, TIME_SLOTS
from models import Appointment, Invoice, User, db


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    if "current_user" not in g:
        g.current_user = db.session.get(User, user_id)
    return g.current_user


def dashboard_endpoint_for(user):
    return "main.doctor_dashboard" if user.is_doctor else "main.dashboard"


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                session.clear()
                flash("Please log in to continue.", "warning")
                return redirect(url_for("main.login"))
            if role and user.role != role:
                flash("That page is not available for your account type.", "danger")
                return redirect(url_for(dashboard_endpoint_for(user)))
            return view(*args, **kwargs)

        return wrapper

    return decorator


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def csrf_is_valid():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    return bool(submitted) and bool(expected) and secrets.compare_digest(submitted, expected)


def booked_slots(doctor_id, day):
    rows = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == day,
        Appointment.status.in_(ACTIVE_STATUSES),
    ).all()
    return {row.time_slot for row in rows}


def open_slots(doctor, day):
    taken = booked_slots(doctor.id, day)
    return [slot for slot in TIME_SLOTS if slot not in taken]


def slot_is_free(doctor, day, slot):
    return slot in open_slots(doctor, day)


def create_invoice_for(appointment):
    fee = appointment.doctor.consultation_fee
    tax = round(fee * GST_RATE)
    invoice = Invoice(
        invoice_number=f"INV-{datetime.utcnow():%Y}-{appointment.id:05d}",
        appointment_id=appointment.id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        consultation_fee=fee,
        tax_amount=tax,
        total_amount=fee + tax,
    )
    db.session.add(invoice)
    return invoice


def save_upload(file):
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    original_name = secure_filename(file.filename) or "document"
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "bin"
    stored_name = f"{uuid.uuid4().hex}.{extension}"
    file.save(folder / stored_name)
    return stored_name, original_name


def format_inr(amount):
    return f"\u20b9{amount:,.0f}"


def age_from_dob(dob):
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def appointment_visible_to(appointment, user):
    if user.is_doctor:
        return appointment.doctor_id == user.doctor.id
    return appointment.patient_id == user.id


def fail_if_not_found(obj):
    if obj is None:
        abort(404)
    return obj
