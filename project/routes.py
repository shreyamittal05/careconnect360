import secrets
from datetime import date, datetime, timedelta

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from config import (
    BOOKING_WINDOW_DAYS,
    MEDICAL_RECORD_TYPES,
    PAYMENT_METHODS,
    SPECIALIZATIONS,
    TIME_SLOTS,
    WEEKDAYS,
)
from helpers import (
    age_from_dob,
    appointment_visible_to,
    create_invoice_for,
    csrf_token,
    current_user,
    dashboard_endpoint_for,
    fail_if_not_found,
    format_inr,
    login_required,
    open_slots,
    save_upload,
    slot_is_free,
)
from models import Appointment, Doctor, Invoice, MedicalRecord, Prescription, User, db
from seed import DEMO_PASSWORD_DOCTOR, DEMO_PASSWORD_PATIENT, SAMPLE_DOCTORS, SAMPLE_PATIENTS
from validators import (
    validate_booking,
    validate_consultation_notes,
    validate_login,
    validate_medical_record,
    validate_prescription,
    validate_profile,
    validate_registration,
    validate_upload,
)

main_bp = Blueprint("main", __name__)

DOCTOR_STATUS_ACTIONS = {
    "accept": ("pending", "confirmed"),
    "reject": ("pending", "rejected"),
    "complete": ("confirmed", "completed"),
}
APPOINTMENT_FILTERS = ("all", "upcoming", "completed", "cancelled")


@main_bp.app_context_processor
def inject_globals():
    return {
        "csrf_token": csrf_token,
        "current_user": current_user(),
        "format_inr": format_inr,
        "today": date.today(),
    }


@main_bp.route("/")
def index():
    featured = Doctor.query.order_by(Doctor.rating.desc()).limit(3).all()
    return render_template("index.html", featured=featured, specializations=SPECIALIZATIONS)


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for(dashboard_endpoint_for(current_user())))

    form = {"role": request.args.get("role", "patient")}
    if request.method == "POST":
        form = request.form
        data, errors = validate_registration(form)
        if not errors and User.query.filter_by(email=data["email"]).first():
            errors.append("An account with this email already exists.")
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            user = User(
                role=data["role"],
                full_name=data["full_name"],
                email=data["email"],
                phone=data["phone"],
                date_of_birth=data.get("date_of_birth"),
            )
            user.set_password(data["password"])
            if user.is_doctor:
                user.doctor = Doctor(
                    specialization=data["specialization"],
                    qualification=data["qualification"],
                    experience_years=data["experience_years"],
                    consultation_fee=data["consultation_fee"],
                    availability_days=data["availability_days"],
                    bio=data["bio"],
                    rating=4.5,
                    photo_url="",
                )
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            flash(f"Welcome to CareConnect360, {user.full_name}! Your account is ready.", "success")
            return redirect(url_for(dashboard_endpoint_for(user)))

    return render_template(
        "register.html", form=form, specializations=SPECIALIZATIONS, weekdays=WEEKDAYS
    )


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for(dashboard_endpoint_for(current_user())))

    if request.method == "POST":
        data, errors = validate_login(request.form)
        user = User.query.filter_by(email=data["email"]).first() if not errors else None
        if user and user.check_password(data["password"]):
            session.clear()
            session["user_id"] = user.id
            flash(f"Welcome back, {user.full_name}.", "success")
            return redirect(url_for(dashboard_endpoint_for(user)))
        for error in errors or ["Invalid email or password."]:
            flash(error, "danger")

    demo_accounts = [
        {"label": "Patient", "email": SAMPLE_PATIENTS[0]["email"], "password": DEMO_PASSWORD_PATIENT},
        {"label": "Doctor", "email": SAMPLE_DOCTORS[0]["email"], "password": DEMO_PASSWORD_DOCTOR},
    ]
    return render_template("login.html", demo_accounts=demo_accounts)


@main_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("main.index"))


@main_bp.route("/dashboard")
@login_required("patient")
def dashboard():
    user = current_user()
    appointments = Appointment.query.filter_by(patient_id=user.id).all()
    upcoming = sorted(
        (a for a in appointments if a.is_upcoming),
        key=lambda a: (a.appointment_date, a.time_slot),
    )
    prescriptions = Prescription.query.filter_by(patient_id=user.id).all()
    recent = sorted(appointments, key=lambda a: a.created_at, reverse=True)[:5]
    return render_template(
        "dashboard.html",
        total_count=len(appointments),
        upcoming=upcoming[:5],
        upcoming_count=len(upcoming),
        completed_count=sum(1 for a in appointments if a.status == "completed"),
        active_prescriptions=sum(1 for p in prescriptions if p.is_active),
        recent=recent,
    )


@main_bp.route("/doctor-dashboard")
@login_required("doctor")
def doctor_dashboard():
    doctor = current_user().doctor
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
    today = date.today()
    todays = sorted(
        (
            a
            for a in appointments
            if a.appointment_date == today and a.status not in ("cancelled", "rejected")
        ),
        key=lambda a: a.time_slot,
    )
    pending = sorted(
        (a for a in appointments if a.status == "pending"),
        key=lambda a: (a.appointment_date, a.time_slot),
    )
    return render_template(
        "doctor_dashboard.html",
        total_patients=len({a.patient_id for a in appointments}),
        todays=todays,
        pending=pending,
        pending_count=len(pending),
        completed_count=sum(1 for a in appointments if a.status == "completed"),
    )


@main_bp.route("/doctors")
@login_required()
def doctors():
    specialization = request.args.get("specialization", "").strip()
    day = request.args.get("day", "").strip()
    search = request.args.get("q", "").strip()[:80]

    query = Doctor.query.join(Doctor.user)
    if specialization in SPECIALIZATIONS:
        query = query.filter(Doctor.specialization == specialization)
    if search:
        query = query.filter(User.full_name.ilike(f"%{search}%"))
    results = query.order_by(Doctor.rating.desc()).all()
    if day in WEEKDAYS:
        results = [doctor for doctor in results if day in doctor.days_list]

    return render_template(
        "doctors.html",
        doctors=results,
        specializations=SPECIALIZATIONS,
        weekdays=WEEKDAYS,
        filters={"specialization": specialization, "day": day, "q": search},
    )


@main_bp.route("/doctors/<int:doctor_id>")
@login_required()
def doctor_profile(doctor_id):
    doctor = fail_if_not_found(db.session.get(Doctor, doctor_id))
    next_days = []
    day = date.today()
    while len(next_days) < 5 and (day - date.today()).days < 14:
        if doctor.works_on(day):
            next_days.append({"date": day, "open_slots": len(open_slots(doctor, day))})
        day += timedelta(days=1)
    return render_template("doctor_profile.html", doctor=doctor, next_days=next_days)


@main_bp.route("/book-appointment", methods=["GET", "POST"])
@login_required("patient")
def book_appointment():
    doctors_list = Doctor.query.join(Doctor.user).order_by(User.full_name).all()
    form = {"doctor_id": request.args.get("doctor_id", type=int)}

    if request.method == "POST":
        form = request.form
        data, errors = validate_booking(request.form)
        doctor = db.session.get(Doctor, data["doctor_id"]) if data["doctor_id"] else None
        if doctor is None and not errors:
            errors.append("The selected doctor could not be found.")
        if doctor and not errors:
            if not doctor.works_on(data["appointment_date"]):
                errors.append(f"{doctor.name} is not available on that day.")
            elif not slot_is_free(doctor, data["appointment_date"], data["time_slot"]):
                errors.append("That time slot was just booked. Please choose another slot.")

        if not errors:
            appointment = Appointment(
                patient_id=current_user().id,
                doctor=doctor,
                appointment_date=data["appointment_date"],
                time_slot=data["time_slot"],
                mode=data["mode"],
                symptoms=data["symptoms"],
                status="pending",
            )
            db.session.add(appointment)
            db.session.flush()
            create_invoice_for(appointment)
            db.session.commit()
            flash(
                f"Appointment {appointment.code} requested with {doctor.name}. "
                "You will be notified once the doctor confirms it.",
                "success",
            )
            return redirect(url_for("main.appointments"))

        for error in errors:
            flash(error, "danger")

    return render_template(
        "booking.html",
        doctors=doctors_list,
        form=form,
        time_slots=TIME_SLOTS,
        min_date=date.today().isoformat(),
        max_date=(date.today() + timedelta(days=BOOKING_WINDOW_DAYS)).isoformat(),
    )


def _accessible_appointment(appointment_id):
    appointment = db.session.get(Appointment, appointment_id)
    if appointment is None or not appointment_visible_to(appointment, current_user()):
        abort(404)
    return appointment


def _settle_invoice_after_end(appointment):
    invoice = appointment.invoice
    if invoice is None:
        return
    if invoice.status == "unpaid":
        invoice.status = "cancelled"
    elif invoice.status == "paid":
        invoice.status = "refunded"


@main_bp.route("/appointments")
@login_required()
def appointments():
    user = current_user()
    query = Appointment.query
    if user.is_doctor:
        query = query.filter_by(doctor_id=user.doctor.id)
    else:
        query = query.filter_by(patient_id=user.id)
    items = query.order_by(Appointment.appointment_date.desc(), Appointment.time_slot.desc()).all()

    status_filter = request.args.get("status", "all")
    if status_filter not in APPOINTMENT_FILTERS:
        status_filter = "all"
    if status_filter == "upcoming":
        items = [a for a in items if a.is_upcoming]
    elif status_filter == "completed":
        items = [a for a in items if a.status == "completed"]
    elif status_filter == "cancelled":
        items = [a for a in items if a.status in ("cancelled", "rejected")]

    return render_template("appointments.html", appointments=items, status_filter=status_filter)


@main_bp.route("/appointments/<int:appointment_id>")
@login_required()
def appointment_detail(appointment_id):
    appointment = _accessible_appointment(appointment_id)
    patient_visits = Appointment.query.filter(
        Appointment.patient_id == appointment.patient_id,
        Appointment.status == "completed",
        Appointment.id != appointment.id,
    ).count()
    return render_template(
        "appointment_detail.html",
        appointment=appointment,
        patient_age=age_from_dob(appointment.patient.date_of_birth),
        patient_visits=patient_visits,
    )


@main_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@login_required("patient")
def cancel_appointment(appointment_id):
    appointment = _accessible_appointment(appointment_id)
    if appointment.status not in ("pending", "confirmed"):
        flash("Only pending or confirmed appointments can be cancelled.", "warning")
    else:
        appointment.status = "cancelled"
        _settle_invoice_after_end(appointment)
        db.session.commit()
        flash(f"Appointment {appointment.code} has been cancelled.", "success")
    return redirect(url_for("main.appointments"))


@main_bp.route("/appointments/<int:appointment_id>/status", methods=["POST"])
@login_required("doctor")
def update_appointment_status(appointment_id):
    appointment = _accessible_appointment(appointment_id)
    action = request.form.get("action", "")
    transition = DOCTOR_STATUS_ACTIONS.get(action)
    if transition is None or appointment.status != transition[0]:
        flash("That status change is not allowed for this appointment.", "warning")
    else:
        appointment.status = transition[1]
        if action == "reject":
            _settle_invoice_after_end(appointment)
        db.session.commit()
        messages = {
            "accept": "Appointment confirmed. The patient can now join the consultation.",
            "reject": "Appointment rejected.",
            "complete": "Consultation marked as completed.",
        }
        flash(messages[action], "success")
    return redirect(url_for("main.appointment_detail", appointment_id=appointment.id))


@main_bp.route("/appointments/<int:appointment_id>/notes", methods=["POST"])
@login_required("doctor")
def save_consultation_notes(appointment_id):
    appointment = _accessible_appointment(appointment_id)
    data, errors = validate_consultation_notes(request.form)
    if errors:
        for error in errors:
            flash(error, "danger")
    else:
        appointment.diagnosis = data["diagnosis"]
        appointment.doctor_notes = data["doctor_notes"]
        db.session.commit()
        flash("Diagnosis and consultation notes saved.", "success")
    return redirect(url_for("main.appointment_detail", appointment_id=appointment.id))


@main_bp.route("/consultation")
@login_required()
def consultation():
    user = current_user()
    query = Appointment.query.filter(Appointment.status == "confirmed")
    if user.is_doctor:
        query = query.filter_by(doctor_id=user.doctor.id)
    else:
        query = query.filter_by(patient_id=user.id)
    live = sorted(
        (a for a in query.all() if a.appointment_date >= date.today()),
        key=lambda a: (a.appointment_date, a.time_slot),
    )
    selected_id = request.args.get("appointment", type=int)
    selected = next((a for a in live if a.id == selected_id), live[0] if live else None)
    return render_template("consultation.html", appointments=live, selected=selected)


def _can_view_prescription(prescription, user):
    if user.is_doctor:
        return prescription.doctor_id == user.doctor.id
    return prescription.patient_id == user.id


@main_bp.route("/prescriptions", methods=["GET", "POST"])
@login_required()
def prescriptions():
    user = current_user()
    form = {"appointment_id": request.args.get("appointment", type=int), "duration_days": 5}
    if request.method == "POST":
        if not user.is_doctor:
            abort(403)
        form = request.form
        data, errors = validate_prescription(request.form)
        appointment = None
        if not errors:
            appointment = db.session.get(Appointment, data["appointment_id"])
            if (
                appointment is None
                or appointment.doctor_id != user.doctor.id
                or appointment.status not in ("confirmed", "completed")
            ):
                errors.append("Select one of your confirmed or completed appointments.")
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            prescription = Prescription(
                appointment=appointment,
                patient_id=appointment.patient_id,
                doctor_id=user.doctor.id,
                diagnosis=data["diagnosis"],
                medicine_name=data["medicine_name"],
                dosage=data["dosage"],
                frequency=data["frequency"],
                duration_days=data["duration_days"],
                instructions=data["instructions"],
                prescription_date=data["prescription_date"],
            )
            db.session.add(prescription)
            db.session.commit()
            flash(f"Prescription {prescription.code} created for {appointment.patient.full_name}.", "success")
            return redirect(url_for("main.prescriptions"))

    if user.is_doctor:
        items = (
            Prescription.query.filter_by(doctor_id=user.doctor.id)
            .order_by(Prescription.created_at.desc())
            .all()
        )
        eligible = (
            Appointment.query.filter(
                Appointment.doctor_id == user.doctor.id,
                Appointment.status.in_(("confirmed", "completed")),
            )
            .order_by(Appointment.appointment_date.desc())
            .all()
        )
    else:
        items = (
            Prescription.query.filter_by(patient_id=user.id)
            .order_by(Prescription.created_at.desc())
            .all()
        )
        eligible = []

    return render_template("prescriptions.html", prescriptions=items, eligible=eligible, form=form)


@main_bp.route("/prescriptions/<int:prescription_id>/print")
@login_required()
def print_prescription(prescription_id):
    prescription = fail_if_not_found(db.session.get(Prescription, prescription_id))
    if not _can_view_prescription(prescription, current_user()):
        abort(404)
    return render_template("print_prescription.html", prescription=prescription)


@main_bp.route("/medical-records", methods=["GET", "POST"])
@login_required("patient")
def medical_records():
    user = current_user()
    form = request.form if request.method == "POST" else {}
    if request.method == "POST":
        data, errors = validate_medical_record(request.form)
        upload = request.files.get("document")
        upload_error = validate_upload(upload, current_app.config["ALLOWED_UPLOAD_EXTENSIONS"])
        if upload_error:
            errors.append(upload_error)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            stored_name, original_name = (None, None)
            if upload and upload.filename:
                stored_name, original_name = save_upload(upload)
            record = MedicalRecord(
                patient_id=user.id,
                document_filename=stored_name,
                document_original_name=original_name,
                **data,
            )
            db.session.add(record)
            db.session.commit()
            flash("Medical record added to your history.", "success")
            return redirect(url_for("main.medical_records"))

    records = (
        MedicalRecord.query.filter_by(patient_id=user.id)
        .order_by(MedicalRecord.record_date.desc())
        .all()
    )
    consultations = (
        Appointment.query.filter_by(patient_id=user.id, status="completed")
        .order_by(Appointment.appointment_date.desc())
        .all()
    )
    prescription_history = (
        Prescription.query.filter_by(patient_id=user.id)
        .order_by(Prescription.created_at.desc())
        .all()
    )
    return render_template(
        "medical_records.html",
        records=records,
        consultations=consultations,
        prescription_history=prescription_history,
        record_types=MEDICAL_RECORD_TYPES,
        form=form,
    )


@main_bp.route("/medical-records/<int:record_id>/document")
@login_required("patient")
def view_record_document(record_id):
    record = db.session.get(MedicalRecord, record_id)
    if record is None or record.patient_id != current_user().id or not record.document_filename:
        abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        record.document_filename,
        download_name=record.document_original_name,
    )


@main_bp.route("/billing")
@login_required()
def billing():
    user = current_user()
    query = Invoice.query
    if user.is_doctor:
        query = query.filter_by(doctor_id=user.doctor.id)
    else:
        query = query.filter_by(patient_id=user.id)
    invoices = query.order_by(Invoice.created_at.desc()).all()
    return render_template(
        "billing.html",
        invoices=invoices,
        paid_total=sum(i.total_amount for i in invoices if i.status == "paid"),
        outstanding_total=sum(i.total_amount for i in invoices if i.status == "unpaid"),
        payment_methods=PAYMENT_METHODS,
    )


@main_bp.route("/billing/<int:invoice_id>/pay", methods=["POST"])
@login_required("patient")
def pay_invoice(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None or invoice.patient_id != current_user().id:
        abort(404)
    method = request.form.get("payment_method", "")
    if invoice.status != "unpaid":
        flash("This invoice has already been settled or cancelled.", "warning")
    elif method not in PAYMENT_METHODS:
        flash("Select a valid payment method to continue.", "danger")
    else:
        invoice.status = "paid"
        invoice.payment_method = method
        invoice.transaction_ref = f"TXN{secrets.token_hex(5).upper()}"
        invoice.payment_date = datetime.utcnow()
        db.session.commit()
        flash(
            f"Payment of {format_inr(invoice.total_amount)} confirmed via {method}. "
            f"Reference {invoice.transaction_ref}. This is a simulated payment.",
            "success",
        )
    return redirect(url_for("main.billing"))


@main_bp.route("/billing/<int:invoice_id>/print")
@login_required()
def print_invoice(invoice_id):
    invoice = fail_if_not_found(db.session.get(Invoice, invoice_id))
    user = current_user()
    allowed = invoice.patient_id == user.id or (user.is_doctor and invoice.doctor_id == user.doctor.id)
    if not allowed:
        abort(404)
    return render_template("print_invoice.html", invoice=invoice)


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required()
def profile():
    user = current_user()
    if request.method == "POST":
        data, errors = validate_profile(request.form, user.is_doctor)
        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            user.full_name = data["full_name"]
            user.phone = data["phone"]
            if user.is_doctor:
                doctor = user.doctor
                doctor.specialization = data["specialization"]
                doctor.qualification = data["qualification"]
                doctor.experience_years = data["experience_years"]
                doctor.consultation_fee = data["consultation_fee"]
                doctor.availability_days = data["availability_days"]
                doctor.bio = data["bio"]
            db.session.commit()
            flash("Your profile has been updated.", "success")
            return redirect(url_for("main.profile"))

    return render_template("profile.html", specializations=SPECIALIZATIONS, weekdays=WEEKDAYS)
