from datetime import date, datetime, timedelta

from helpers import create_invoice_for
from models import Appointment, Doctor, MedicalRecord, Prescription, User, db

DEMO_PASSWORD_PATIENT = "Patient@123"
DEMO_PASSWORD_DOCTOR = "Doctor@123"

SAMPLE_DOCTORS = [
    {
        "name": "Dr. Ananya Sharma",
        "email": "ananya.sharma@careconnect360.com",
        "specialization": "Cardiologist",
        "qualification": "MD (Cardiology), DM - AIIMS New Delhi",
        "experience_years": 12,
        "consultation_fee": 800,
        "rating": 4.9,
        "availability_days": "Mon,Tue,Wed,Thu,Fri",
        "bio": "Interventional cardiologist focused on heart failure management, hypertension and preventive cardiac care.",
        "photo_url": "https://images.pexels.com/photos/37272329/pexels-photo-37272329.png?auto=compress&cs=tinysrgb&h=650&w=940",
    },
    {
        "name": "Dr. Rahul Verma",
        "email": "rahul.verma@careconnect360.com",
        "specialization": "General Physician",
        "qualification": "MBBS, MD (General Medicine)",
        "experience_years": 8,
        "consultation_fee": 500,
        "rating": 4.7,
        "availability_days": "Mon,Tue,Wed,Thu,Fri,Sat",
        "bio": "Family physician managing fevers, infections, diabetes and routine preventive health checkups.",
        "photo_url": "https://images.pexels.com/photos/19601385/pexels-photo-19601385.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
    },
    {
        "name": "Dr. Priya Mehta",
        "email": "priya.mehta@careconnect360.com",
        "specialization": "Dermatologist",
        "qualification": "MBBS, MD (Dermatology), Cosmetology Fellowship",
        "experience_years": 9,
        "consultation_fee": 700,
        "rating": 4.8,
        "availability_days": "Tue,Wed,Thu,Sat",
        "bio": "Treats acne, eczema, pigmentation and hair concerns with evidence-based skin care plans.",
        "photo_url": "https://images.pexels.com/photos/30270934/pexels-photo-30270934.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
    },
    {
        "name": "Dr. Arjun Kapoor",
        "email": "arjun.kapoor@careconnect360.com",
        "specialization": "Neurologist",
        "qualification": "MBBS, DM (Neurology)",
        "experience_years": 15,
        "consultation_fee": 1000,
        "rating": 4.9,
        "availability_days": "Mon,Wed,Fri",
        "bio": "Specialist in migraine, epilepsy, stroke recovery and movement disorders.",
        "photo_url": "https://images.pexels.com/photos/33970123/pexels-photo-33970123.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
    },
    {
        "name": "Dr. Neha Gupta",
        "email": "neha.gupta@careconnect360.com",
        "specialization": "Pediatrician",
        "qualification": "MBBS, MD (Pediatrics)",
        "experience_years": 6,
        "consultation_fee": 600,
        "rating": 4.6,
        "availability_days": "Mon,Tue,Wed,Thu,Fri,Sat",
        "bio": "Caring for newborns, children and adolescents, including vaccinations and growth monitoring.",
        "photo_url": "https://images.pexels.com/photos/29995629/pexels-photo-29995629.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
    },
]

SAMPLE_PATIENTS = [
    {
        "full_name": "Aarav Patel",
        "email": "patient@careconnect360.com",
        "phone": "+91 98765 43210",
        "date_of_birth": date(1994, 5, 14),
    },
    {
        "full_name": "Meera Iyer",
        "email": "meera@careconnect360.com",
        "phone": "+91 91234 56789",
        "date_of_birth": date(1988, 11, 2),
    },
]


def seed_demo_data():
    if User.query.first() is not None:
        return

    doctors = []
    for item in SAMPLE_DOCTORS:
        user = User(role="doctor", full_name=item["name"], email=item["email"], phone="+91 22 4000 0000")
        user.set_password(DEMO_PASSWORD_DOCTOR)
        doctor = Doctor(
            user=user,
            specialization=item["specialization"],
            qualification=item["qualification"],
            experience_years=item["experience_years"],
            consultation_fee=item["consultation_fee"],
            rating=item["rating"],
            availability_days=item["availability_days"],
            bio=item["bio"],
            photo_url=item["photo_url"],
        )
        db.session.add(doctor)
        doctors.append(doctor)

    patients = []
    for item in SAMPLE_PATIENTS:
        patient = User(
            role="patient",
            full_name=item["full_name"],
            email=item["email"],
            phone=item["phone"],
            date_of_birth=item["date_of_birth"],
        )
        patient.set_password(DEMO_PASSWORD_PATIENT)
        db.session.add(patient)
        patients.append(patient)

    db.session.flush()

    aarav = patients[0]
    rahul, ananya, neha = doctors[1], doctors[0], doctors[4]
    today = date.today()

    completed = Appointment(
        patient=aarav,
        doctor=rahul,
        appointment_date=today - timedelta(days=7),
        time_slot="10:00",
        mode="video",
        symptoms="Fever for three days, body ache and sore throat.",
        status="completed",
        diagnosis="Viral fever with mild throat infection",
        doctor_notes="Rest for 3 days, plenty of fluids. Review if fever persists beyond 5 days.",
    )
    confirmed = Appointment(
        patient=aarav,
        doctor=ananya,
        appointment_date=today + timedelta(days=2),
        time_slot="11:00",
        mode="video",
        symptoms="Occasional chest tightness after climbing stairs. Want a routine heart checkup.",
        status="confirmed",
    )
    pending = Appointment(
        patient=aarav,
        doctor=neha,
        appointment_date=today + timedelta(days=5),
        time_slot="15:00",
        mode="audio",
        symptoms="Follow-up for vaccination schedule and growth concerns for my niece.",
        status="pending",
    )
    db.session.add_all([completed, confirmed, pending])
    db.session.flush()

    for appointment in (completed, confirmed, pending):
        create_invoice_for(appointment)

    paid = completed.invoice
    paid.status = "paid"
    paid.payment_method = "UPI"
    paid.transaction_ref = "TXN-DEMO-000101"
    paid.payment_date = datetime.utcnow() - timedelta(days=7)

    db.session.add(
        Prescription(
            appointment=completed,
            patient=aarav,
            doctor=rahul,
            diagnosis="Viral fever with mild throat infection",
            medicine_name="Paracetamol 650 mg",
            dosage="1 tablet",
            frequency="Three times a day after meals",
            duration_days=5,
            instructions="Drink warm fluids. Avoid cold beverages. Stop if rash or breathing difficulty occurs.",
            prescription_date=today - timedelta(days=7),
        )
    )
    db.session.add(
        Prescription(
            appointment=completed,
            patient=aarav,
            doctor=rahul,
            diagnosis="Viral fever with mild throat infection",
            medicine_name="Warm saline gargle",
            dosage="1 gargle",
            frequency="Twice a day",
            duration_days=5,
            instructions="Gargle with lukewarm salt water after breakfast and before sleep.",
            prescription_date=today - timedelta(days=2),
        )
    )
    db.session.add(
        MedicalRecord(
            patient=aarav,
            record_type="Lab report",
            title="Complete blood count",
            record_date=today - timedelta(days=30),
            symptoms="Routine annual screening",
            diagnosis="Within normal limits",
            notes="Hemoglobin 14.2 g/dL, WBC 6,800 /cumm. No action needed.",
        )
    )
    db.session.commit()
