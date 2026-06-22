from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api.rest.dependencies import CurrentUser, DBSession, require_role
from src.core.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["Appointments"])


class BookAppointmentRequest(BaseModel):
    patient_id: UUID
    doctor_id: UUID
    appointment_type_id: UUID
    start_datetime: datetime
    booking_source: str  # AI_CHAT, AI_CALL, FRONT_DESK


class RescheduleRequest(BaseModel):
    new_start_datetime: datetime


class AvailabilityRequest(BaseModel):
    doctor_id: UUID
    date: datetime
    appointment_type_id: UUID


def _appointment_response(a):
    return {
        "appointment_id": str(a.appointment_id),
        "patient_id": str(a.patient_id),
        "doctor_id": str(a.doctor_id),
        "appointment_type_id": str(a.appointment_type_id),
        "start_datetime": a.start_datetime.isoformat(),
        "end_datetime": a.end_datetime.isoformat(),
        "status": a.status,
        "booking_source": a.booking_source,
        "created_by_actor_type": a.created_by_actor_type,
        "created_by_actor_id": str(a.created_by_actor_id),
        "created_at": a.created_at.isoformat(),
    }


@router.post("", status_code=201)
def book_appointment(
    request: BookAppointmentRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Book an appointment. Accessible by all authenticated users."""
    service = AppointmentService(db)
    appointment = service.book_appointment(
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        appointment_type_id=request.appointment_type_id,
        start_datetime=request.start_datetime,
        booking_source=request.booking_source,
        created_by_actor_type=current_user.get("role"),
        created_by_actor_id=UUID(current_user.get("sub")),
    )
    return _appointment_response(appointment)


@router.get("/{appointment_id}")
def get_appointment(
    appointment_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    service = AppointmentService(db)
    a = service.get_appointment(appointment_id)
    return _appointment_response(a)


@router.get("/patient/{patient_id}")
def get_patient_appointments(
    patient_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    service = AppointmentService(db)
    appointments = service.get_patient_appointments(patient_id)
    return [_appointment_response(a) for a in appointments]


@router.get("/doctor/{doctor_id}")
def get_doctor_appointments(
    doctor_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    service = AppointmentService(db)
    appointments = service.get_doctor_appointments(doctor_id)
    return [_appointment_response(a) for a in appointments]


@router.post("/availability")
def get_available_slots(
    request: AvailabilityRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get available time slots for a doctor on a given date."""
    service = AppointmentService(db)
    slots = service.get_available_slots(
        doctor_id=request.doctor_id,
        date=request.date,
        appointment_type_id=request.appointment_type_id,
    )
    return [
        {"start": s["start"].isoformat(), "end": s["end"].isoformat()} for s in slots
    ]


@router.put("/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: UUID,
    request: RescheduleRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    service = AppointmentService(db)
    a = service.reschedule_appointment(appointment_id, request.new_start_datetime)
    return _appointment_response(a)


@router.put("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    service = AppointmentService(db)
    a = service.cancel_appointment(appointment_id)
    return _appointment_response(a)


@router.put("/{appointment_id}/complete")
def complete_appointment(
    appointment_id: UUID,
    db: DBSession,
    current_user: dict = Depends(require_role("ADMIN", "FRONT_DESK", "DOCTOR")),
):
    """Mark appointment as completed. Staff/Doctor only."""
    service = AppointmentService(db)
    a = service.complete_appointment(appointment_id)
    return _appointment_response(a)


@router.put("/{appointment_id}/no-show")
def mark_no_show(
    appointment_id: UUID,
    db: DBSession,
    current_user: dict = Depends(require_role("ADMIN", "FRONT_DESK", "DOCTOR")),
):
    """Mark appointment as no-show. Staff/Doctor only."""
    service = AppointmentService(db)
    a = service.mark_no_show(appointment_id)
    return _appointment_response(a)
