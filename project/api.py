from datetime import date, datetime

from flask import Blueprint, abort, jsonify, request

from config import SPECIALIZATIONS, WEEKDAYS
from helpers import appointment_visible_to, current_user, open_slots
from models import Appointment, Doctor, db

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _doctor_json(doctor):
    return {
        "id": doctor.id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "experience_years": doctor.experience_years,
        "consultation_fee": doctor.consultation_fee,
        "rating": doctor.rating,
        "availability_days": doctor.days_list,
        "photo_url": doctor.photo_url,
    }


def _appointment_json(appointment):
    return {
        "id": appointment.id,
        "code": appointment.code,
        "date": appointment.appointment_date.isoformat(),
        "time_slot": appointment.time_slot,
        "mode": appointment.mode,
        "status": appointment.status,
        "patient_name": appointment.patient.full_name,
        "doctor_name": appointment.doctor.name,
    }


@api_bp.errorhandler(400)
@api_bp.errorhandler(404)
def api_error(error):
    return jsonify({"error": error.description}), error.code


@api_bp.get("/doctors")
def list_doctors():
    specialization = request.args.get("specialization", "").strip()
    day = request.args.get("day", "").strip()
    query = Doctor.query.join(Doctor.user)
    if specialization in SPECIALIZATIONS:
        query = query.filter(Doctor.specialization == specialization)
    doctors = query.order_by(Doctor.rating.desc()).all()
    if day in WEEKDAYS:
        doctors = [doctor for doctor in doctors if day in doctor.days_list]
    return jsonify({"doctors": [_doctor_json(doctor) for doctor in doctors]})


@api_bp.get("/doctors/<int:doctor_id>/slots")
def doctor_slots(doctor_id):
    doctor = db.session.get(Doctor, doctor_id)
    if doctor is None:
        abort(404, description="Doctor not found.")
    raw_date = request.args.get("date", "")
    try:
        day = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        abort(400, description="Provide the date as YYYY-MM-DD.")
    if day < date.today():
        abort(400, description="Choose today or a future date.")
    if not doctor.works_on(day):
        return jsonify({"date": raw_date, "available": False, "slots": []})
    return jsonify({"date": raw_date, "available": True, "slots": open_slots(doctor, day)})


@api_bp.get("/appointments")
def list_appointments():
    user = current_user()
    if user is None:
        return jsonify({"error": "Authentication required."}), 401
    query = Appointment.query
    if user.is_doctor:
        query = query.filter_by(doctor_id=user.doctor.id)
    else:
        query = query.filter_by(patient_id=user.id)
    items = query.order_by(Appointment.appointment_date.desc(), Appointment.time_slot.desc()).all()
    return jsonify({"appointments": [_appointment_json(item) for item in items]})


@api_bp.get("/appointments/<int:appointment_id>")
def get_appointment(appointment_id):
    user = current_user()
    if user is None:
        return jsonify({"error": "Authentication required."}), 401
    appointment = db.session.get(Appointment, appointment_id)
    if appointment is None or not appointment_visible_to(appointment, user):
        abort(404, description="Appointment not found.")
    return jsonify(_appointment_json(appointment))
