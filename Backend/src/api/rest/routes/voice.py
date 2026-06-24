"""
Twilio Voice Integration — handles incoming phone calls via the iClinic AI agent.

Uses Twilio's <Gather> with speech recognition for STT, and <Say> for TTS.
Handles Twilio's 15-second webhook timeout by using <Redirect> polling pattern.

Flow:
  1. Patient calls → /voice/incoming returns greeting + <Gather>
  2. Patient speaks → Twilio STT → POSTs to /voice/respond
  3. /voice/respond kicks off agent in background, returns <Pause> + <Redirect> to /voice/result
  4. /voice/result checks if agent is done:
     - Done → returns <Say> with response + <Gather> for next turn
     - Not done → returns <Pause> + <Redirect> back to /voice/result (poll again)
"""

import asyncio
import html
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import Response

# Ensure Backend/src is on sys.path for control.* imports
_src_dir = str(Path(__file__).resolve().parents[3])  # Backend/src
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

# ─── In-memory stores ───────────────────────────────────────────────────────────

# call_sid → { graph, config, first_message, patient_entities, db }
_voice_sessions: dict[str, dict] = {}

# call_sid → { "status": "processing"|"done", "response": str }
_pending_responses: dict[str, dict] = {}

# phone_number → { patient_id, first_name, ... } — pre-loaded when outbound call is initiated
_outbound_identities: dict[str, dict] = {}

# call_sid → JWT token string — stored at /voice/initiate time
_outbound_tokens: dict[str, str] = {}

# call_sid → user_id — stored at /voice/initiate time
_outbound_user_ids: dict[str, str] = {}

# phone_number → session_id (thread_id) — when user triggers call from chat
_outbound_session_ids: dict[str, str] = {}


# ─── LLM + Graph setup ─────────────────────────────────────────────────────────

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from control.factories.llm_factory import LLMFactory

        _llm = LLMFactory.get_llm()
    return _llm


def _get_or_create_session(call_sid: str, caller_number: str) -> dict:
    """Get existing session or create a new one for this call."""
    if call_sid in _voice_sessions:
        return _voice_sessions[call_sid]

    from control.factories.tool_factory import ToolFactory
    from control.graphs.frontdesk_graph import FrontDeskGraph
    from src.config.database import SessionLocal

    db = SessionLocal()
    registry = ToolFactory.create_registry(db)
    llm = _get_llm()

    graph = FrontDeskGraph(llm=llm, tool_registry=registry).get_graph()

    # Resolve patient identity — use stored JWT token (same method as WebSocket)
    patient_entities = {}
    token = _outbound_tokens.pop(call_sid, None)
    if token:
        patient_entities = _resolve_patient_from_token(token, db)
        logger.info(
            f"[VOICE] Patient resolved from token: patient_id={patient_entities.get('patient_id')}, name={patient_entities.get('first_name')}"
        )

    # Fallback: try user_id dict
    if not patient_entities.get("patient_id"):
        user_id = _outbound_user_ids.pop(call_sid, None)
        if not user_id:
            user_id = _outbound_user_ids.pop(caller_number, None)
        if not user_id:
            caller_stripped = caller_number.lstrip("+")
            last10 = (
                caller_stripped[-10:] if len(caller_stripped) >= 10 else caller_stripped
            )
            for stored_key, stored_uid in list(_outbound_user_ids.items()):
                stored_stripped = stored_key.lstrip("+")
                stored_last10 = (
                    stored_stripped[-10:]
                    if len(stored_stripped) >= 10
                    else stored_stripped
                )
                if stored_last10 == last10:
                    user_id = stored_uid
                    _outbound_user_ids.pop(stored_key, None)
                    break
        if user_id:
            patient_entities = _resolve_patient_by_user_id(user_id, db)
            logger.info(
                f"[VOICE] Patient resolved by user_id: patient_id={patient_entities.get('patient_id')}"
            )

    # Fallback: try phone lookup
    if not patient_entities.get("patient_id"):
        patient_entities = _identify_patient_by_phone(caller_number, db)
        logger.info(
            f"[VOICE] Patient resolved by phone: patient_id={patient_entities.get('patient_id')}"
        )

    # Check if this call should continue an existing chat session
    # Look up by caller_number (normalized matching)
    existing_session_id = None
    for stored_phone, sid in list(_outbound_session_ids.items()):
        stored_stripped = stored_phone.lstrip("+")
        caller_stripped = caller_number.lstrip("+")
        if len(stored_stripped) > 10:
            stored_last10 = stored_stripped[-10:]
        else:
            stored_last10 = stored_stripped
        if len(caller_stripped) > 10:
            caller_last10 = caller_stripped[-10:]
        else:
            caller_last10 = caller_stripped

        if stored_last10 == caller_last10:
            existing_session_id = sid
            _outbound_session_ids.pop(stored_phone, None)
            break

    if existing_session_id:
        # Reuse the chat thread_id so LangGraph loads the same conversation history
        thread_id = existing_session_id
        first_message = (
            False  # Not the first message — conversation already has history
        )
        logger.info(f"[VOICE] Continuing chat session: {thread_id}")
    else:
        thread_id = f"voice-{call_sid}"
        first_message = True

    session = {
        "graph": graph,
        "config": {"configurable": {"thread_id": thread_id}},
        "first_message": first_message,
        "patient_entities": patient_entities,
        "db": db,
    }

    _voice_sessions[call_sid] = session
    logger.info(
        f"[VOICE] Session created: call={call_sid}, thread={thread_id}, "
        f"patient={patient_entities.get('first_name', 'unknown')}"
    )
    return session


def _close_session(call_sid: str):
    """Close DB session and cleanup."""
    session = _voice_sessions.pop(call_sid, None)
    _pending_responses.pop(call_sid, None)
    if session and session.get("db"):
        try:
            session["db"].commit()
            session["db"].close()
        except Exception:
            session["db"].rollback()
            session["db"].close()


def _resolve_patient_from_token(token: str, db) -> dict:
    """Decode JWT and resolve patient by user_id — same as WebSocket handler."""
    if not token:
        return {}

    from jose import JWTError, jwt
    from src.config.settings import settings
    from src.core.services.appointment_service import AppointmentService
    from src.core.services.patient_service import PatientService

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
    except JWTError as e:
        logger.warning(f"[VOICE] Token decode failed: {e}")
        return {}

    user_id = payload.get("sub")
    if not user_id:
        return {}

    patient_service = PatientService(db)
    patient = patient_service.get_patient_by_user_id(user_id)

    if not patient:
        return {"user_id": user_id, "email": payload.get("email", "")}

    entities = {
        "user_id": user_id,
        "patient_id": str(patient.patient_id),
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone": patient.phone,
        "email": patient.email or payload.get("email", ""),
    }

    appointment_service = AppointmentService(db)
    all_appointments = appointment_service.get_patient_appointments(patient.patient_id)
    recent_5 = all_appointments[:5]

    if recent_5:
        booking_history = []
        for apt in recent_5:
            doctor_name = apt.doctor.full_name if apt.doctor else "Unknown"
            booking_history.append(
                {
                    "doctor_name": doctor_name,
                    "doctor_id": str(apt.doctor_id),
                    "specialty": apt.doctor.specialization if apt.doctor else "",
                    "date": apt.start_datetime.strftime("%A, %B %d, %Y at %I:%M %p"),
                    "status": apt.status,
                }
            )
        entities["booking_history"] = booking_history

    return entities


def _resolve_patient_by_user_id(user_id: str, db) -> dict:
    """Resolve patient entities by user_id — same as WebSocket chat does."""
    from src.core.services.appointment_service import AppointmentService
    from src.core.services.patient_service import PatientService

    patient_service = PatientService(db)
    patient = patient_service.get_patient_by_user_id(user_id)

    if not patient:
        return {"user_id": user_id}

    entities = {
        "user_id": user_id,
        "patient_id": str(patient.patient_id),
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone": patient.phone,
        "email": patient.email or "",
    }

    appointment_service = AppointmentService(db)
    all_appointments = appointment_service.get_patient_appointments(patient.patient_id)
    recent_5 = all_appointments[:5]

    if recent_5:
        booking_history = []
        for apt in recent_5:
            doctor_name = apt.doctor.full_name if apt.doctor else "Unknown"
            booking_history.append(
                {
                    "doctor_name": doctor_name,
                    "doctor_id": str(apt.doctor_id),
                    "specialty": apt.doctor.specialization if apt.doctor else "",
                    "date": apt.start_datetime.strftime("%A, %B %d, %Y at %I:%M %p"),
                    "status": apt.status,
                }
            )
        entities["booking_history"] = booking_history

    return entities


def _identify_patient_by_phone(phone: str, db) -> dict:
    """Look up patient by caller phone number. Also checks pre-loaded outbound identities."""
    if not phone or phone == "unknown":
        return {}

    # Check if this phone was pre-identified via /voice/initiate (outbound call)
    preloaded = _outbound_identities.get(phone)
    if not preloaded:
        # Try normalized variants
        stripped = phone.lstrip("+")
        if len(stripped) > 10:
            last10 = stripped[-10:]
        else:
            last10 = stripped
        # Check all stored numbers for a match
        for stored_phone, identity in list(_outbound_identities.items()):
            stored_stripped = stored_phone.lstrip("+")
            if len(stored_stripped) > 10:
                stored_last10 = stored_stripped[-10:]
            else:
                stored_last10 = stored_stripped
            if stored_last10 == last10:
                preloaded = identity
                break

    if preloaded:
        logger.info(
            f"[VOICE] Patient pre-identified from outbound call: {preloaded.get('first_name')}"
        )
        # Remove from map (one-time use)
        _outbound_identities.pop(phone, None)
        return preloaded

    from src.core.services.appointment_service import AppointmentService
    from src.core.services.patient_service import PatientService

    patient_service = PatientService(db)

    # Try direct phone lookup with multiple formats
    patient = patient_service.get_patient_by_phone(phone)

    if not patient:
        stripped = phone.lstrip("+")
        if len(stripped) > 10:
            stripped = stripped[-10:]
        patient = patient_service.get_patient_by_phone(stripped)

    # Also try with country code variants
    if not patient:
        stripped = phone.lstrip("+")
        if len(stripped) == 10:
            patient = patient_service.get_patient_by_phone(f"+91{stripped}")

    # Last resort: match by last 10 digits using SQL LIKE
    if not patient:
        from src.data.models.postgres.patient import Patient

        stripped = phone.lstrip("+")
        last10 = stripped[-10:] if len(stripped) >= 10 else stripped
        patient = db.query(Patient).filter(Patient.phone.like(f"%{last10}")).first()

    if not patient:
        return {"caller_phone": phone}

    entities = {
        "caller_phone": phone,
        "patient_id": str(patient.patient_id),
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone": patient.phone,
        "email": patient.email or "",
    }

    appointment_service = AppointmentService(db)
    all_appointments = appointment_service.get_patient_appointments(patient.patient_id)
    recent_5 = all_appointments[:5]

    if recent_5:
        booking_history = []
        for apt in recent_5:
            doctor_name = apt.doctor.full_name if apt.doctor else "Unknown"
            booking_history.append(
                {
                    "doctor_name": doctor_name,
                    "doctor_id": str(apt.doctor_id),
                    "specialty": apt.doctor.specialization if apt.doctor else "",
                    "date": apt.start_datetime.strftime("%A, %B %d, %Y at %I:%M %p"),
                    "status": apt.status,
                }
            )
        entities["booking_history"] = booking_history

    return entities


# ─── Endpoints ──────────────────────────────────────────────────────────────────


@router.post("/incoming")
async def handle_incoming_call(request: Request):
    """
    Twilio webhook — called when the outbound call is answered.
    Returns greeting + <Gather> immediately.
    Also pre-creates the voice session with patient context from the JWT.
    """
    from control.voice.voice_config import voice_config

    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")

    # For outbound calls: To = user's phone, From = Twilio number
    # For inbound calls: From = user's phone, To = Twilio number
    to_number = form_data.get("To", "")
    from_number = form_data.get("From", "")
    direction = form_data.get("Direction", "")

    if direction == "outbound-api" or to_number != voice_config.twilio_phone_number:
        caller_number = to_number or from_number or "unknown"
    else:
        caller_number = from_number or to_number or "unknown"

    logger.info(
        f"[VOICE] Call answered: {caller_number} (CallSid: {call_sid}, Direction: {direction})"
    )

    # Extract JWT from URL query param (passed from /voice/initiate)
    jwt_token = request.query_params.get("jwt", "")
    if jwt_token:
        import urllib.parse

        jwt_token = urllib.parse.unquote(jwt_token)
        # Pre-create session NOW with patient context from JWT
        # This ensures /voice/respond finds an existing session with patient preloaded
        from control.factories.tool_factory import ToolFactory
        from control.graphs.frontdesk_graph import FrontDeskGraph
        from src.config.database import SessionLocal

        db = SessionLocal()
        registry = ToolFactory.create_registry(db)
        llm = _get_llm()
        graph = FrontDeskGraph(llm=llm, tool_registry=registry).get_graph()

        patient_entities = _resolve_patient_from_token(jwt_token, db)
        logger.info(
            f"[VOICE] Patient from JWT: patient_id={patient_entities.get('patient_id')}, name={patient_entities.get('first_name')}"
        )

        thread_id = f"voice-{call_sid}"
        session = {
            "graph": graph,
            "config": {"configurable": {"thread_id": thread_id}},
            "first_message": True,
            "patient_entities": patient_entities,
            "db": db,
        }
        _voice_sessions[call_sid] = session

    base_url = voice_config.server_base_url

    # Check if this call is continuing an existing chat session
    has_existing_session = False
    for stored_phone in list(_outbound_session_ids.keys()):
        stored_stripped = stored_phone.lstrip("+")
        caller_stripped = caller_number.lstrip("+")
        s10 = stored_stripped[-10:] if len(stored_stripped) > 10 else stored_stripped
        c10 = caller_stripped[-10:] if len(caller_stripped) > 10 else caller_stripped
        if s10 == c10:
            has_existing_session = True
            break

    # Check pre-loaded identity for patient name
    patient_name = None
    # First check the session we just created
    if call_sid in _voice_sessions:
        pe = _voice_sessions[call_sid].get("patient_entities", {})
        patient_name = pe.get("first_name")
    # Fallback: check _outbound_identities
    if not patient_name:
        for stored_phone, identity in list(_outbound_identities.items()):
            stored_stripped = stored_phone.lstrip("+")
            caller_stripped = caller_number.lstrip("+")
            s10 = (
                stored_stripped[-10:] if len(stored_stripped) > 10 else stored_stripped
            )
            c10 = (
                caller_stripped[-10:] if len(caller_stripped) > 10 else caller_stripped
            )
            if s10 == c10:
                patient_name = identity.get("first_name")
                break

    if has_existing_session and patient_name:
        greeting = (
            f"Hi {patient_name}, this is Maya from iClinic. "
            "I have our chat conversation right here. Let's continue where we left off. "
            "Go ahead, I'm listening."
        )
    elif has_existing_session:
        greeting = (
            "Hi there, this is Maya from iClinic. "
            "I have our chat right here, so let's pick up where we left off. "
            "What would you like to do?"
        )
    elif patient_name:
        greeting = (
            f"Hi {patient_name}, this is Maya from iClinic. How can I help you today?"
        )
    else:
        greeting = "Hi there, this is Maya from iClinic. How can I help you today?"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{greeting}</Say>
    <Gather input="speech" action="{base_url}/voice/respond" method="POST" speechTimeout="2" language="en-US">
    </Gather>
    <Say voice="Polly.Joanna">I didn't catch that. Goodbye.</Say>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


@router.post("/initiate")
async def initiate_outbound_call(request: Request):
    """
    Frontend calls this to trigger an outbound call to the user.

    Expects JSON body: { "phone_number": "+1XXXXXXXXXX" }
    Optionally: { "phone_number": "+1XXXXXXXXXX", "patient_id": "uuid" }

    Requires a valid JWT (Bearer token or cookie).
    Twilio will call the user's phone and when they pick up,
    connect them to the AI agent via /voice/incoming webhook.
    """
    from control.voice.voice_config import voice_config
    from jose import JWTError, jwt
    from src.config.settings import settings
    from twilio.rest import Client

    # Authenticate: extract token from Authorization header or cookie
    token = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        return Response(
            content='{"error": "Authentication required"}',
            status_code=401,
            media_type="application/json",
        )

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return Response(
            content='{"error": "Invalid or expired token"}',
            status_code=401,
            media_type="application/json",
        )

    body = await request.json()
    phone_number = body.get("phone_number", "").strip()

    # If no phone number provided, look it up from the patient profile
    if not phone_number:
        try:
            from src.config.database import SessionLocal
            from src.core.services.patient_service import PatientService

            user_id = payload.get("sub") or payload.get("user_id")
            if user_id:
                db = SessionLocal()
                patient_service = PatientService(db)
                patient = patient_service.get_patient_by_user_id(user_id)
                if patient and patient.phone:
                    phone_number = patient.phone
                db.close()
        except Exception as e:
            logger.warning(f"[VOICE] Could not auto-fetch phone: {e}")

    if not phone_number:
        return Response(
            content='{"error": "phone_number is required and could not be determined from your profile"}',
            status_code=400,
            media_type="application/json",
        )

    # Validate E.164 format (basic check)
    if not phone_number.startswith("+"):
        phone_number = f"+{phone_number}"

    # Pre-identify patient from JWT so /voice/incoming knows who they are
    user_id = payload.get("sub") or payload.get("user_id")
    if user_id:
        try:
            from src.config.database import SessionLocal
            from src.core.services.appointment_service import AppointmentService
            from src.core.services.patient_service import PatientService

            db = SessionLocal()
            patient_service = PatientService(db)
            patient = patient_service.get_patient_by_user_id(user_id)

            if patient:
                entities = {
                    "caller_phone": phone_number,
                    "patient_id": str(patient.patient_id),
                    "first_name": patient.first_name,
                    "last_name": patient.last_name,
                    "phone": patient.phone,
                    "email": patient.email or "",
                }

                # Load booking history
                appointment_service = AppointmentService(db)
                all_appointments = appointment_service.get_patient_appointments(
                    patient.patient_id
                )
                recent_5 = all_appointments[:5]
                if recent_5:
                    booking_history = []
                    for apt in recent_5:
                        doctor_name = apt.doctor.full_name if apt.doctor else "Unknown"
                        booking_history.append(
                            {
                                "doctor_name": doctor_name,
                                "doctor_id": str(apt.doctor_id),
                                "specialty": apt.doctor.specialization
                                if apt.doctor
                                else "",
                                "date": apt.start_datetime.strftime(
                                    "%A, %B %d, %Y at %I:%M %p"
                                ),
                                "status": apt.status,
                            }
                        )
                    entities["booking_history"] = booking_history

                # Store so /voice/incoming can pick it up
                _outbound_identities[phone_number] = entities
                logger.info(
                    f"[VOICE] Pre-identified patient: {patient.first_name} {patient.last_name}"
                )

            db.close()
        except Exception as e:
            logger.warning(f"[VOICE] Could not pre-identify patient: {e}")

    # Store chat session_id so voice call continues the same conversation
    chat_session_id = body.get("session_id", "")
    if chat_session_id:
        _outbound_session_ids[phone_number] = chat_session_id
        logger.info(f"[VOICE] Will continue chat session: {chat_session_id}")

    logger.info(f"[VOICE] Initiating outbound call to {phone_number}")

    try:
        client = Client(voice_config.twilio_account_sid, voice_config.twilio_auth_token)

        # Make the outbound call — when answered, Twilio fetches /voice/incoming
        # Pass the JWT token in the URL so /voice/incoming can resolve the patient
        # This avoids any in-memory state issues between requests
        import urllib.parse

        encoded_token = urllib.parse.quote(token, safe="")
        call = client.calls.create(
            to=phone_number,
            from_=voice_config.twilio_phone_number,
            url=f"{voice_config.server_base_url}/voice/incoming?jwt={encoded_token}",
            method="POST",
            status_callback=f"{voice_config.server_base_url}/voice/status",
            status_callback_method="POST",
            status_callback_event=["completed", "failed", "busy", "no-answer"],
        )

        logger.info(f"[VOICE] Call initiated: SID={call.sid}, to={phone_number}")

        # Store user_id → call_sid mapping so session creation resolves patient by user_id
        if user_id:
            _outbound_user_ids[call.sid] = user_id
            # Also store by phone for fallback (call_sid might not match in some callbacks)
            _outbound_user_ids[phone_number] = user_id
        # Store the JWT token itself for the most reliable patient resolution
        if token:
            _outbound_tokens[call.sid] = token

        return Response(
            content=f'{{"success": true, "call_sid": "{call.sid}", "to": "{phone_number}"}}',
            status_code=200,
            media_type="application/json",
        )

    except Exception as e:
        logger.error(f"[VOICE] Failed to initiate call: {e}", exc_info=True)
        return Response(
            content=f'{{"error": "{str(e)}"}}',
            status_code=500,
            media_type="application/json",
        )


@router.post("/respond")
async def handle_speech_response(request: Request):
    """
    Receives transcribed speech. Kicks off agent processing in background.
    Returns a short <Say> "hold" message + <Redirect> to /voice/result
    so we don't hit Twilio's 15s timeout.
    """
    from control.voice.voice_config import voice_config

    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    speech_result = form_data.get("SpeechResult", "")

    # Determine the patient's phone number (direction-aware)
    from_number = form_data.get("From", "unknown")
    to_number = form_data.get("To", "unknown")
    direction = form_data.get("Direction", "")

    if direction == "outbound-api" or from_number == voice_config.twilio_phone_number:
        # Outbound call — patient is the "To" number
        caller_number = to_number
    else:
        # Inbound call — patient is the "From" number
        caller_number = from_number

    logger.info(f"[VOICE] Speech: '{speech_result}' (call={call_sid})")

    if not speech_result:
        base_url = voice_config.server_base_url
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Sorry, I didn't catch that. Could you say that again?</Say>
    <Gather input="speech" action="{base_url}/voice/respond" method="POST" speechTimeout="2" language="en-US">
    </Gather>
    <Say voice="Polly.Joanna">Goodbye.</Say>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Mark as processing
    _pending_responses[call_sid] = {"status": "processing", "response": ""}

    # Kick off agent in background
    asyncio.create_task(
        _process_speech_background(call_sid, caller_number, speech_result)
    )

    # Return immediately with a brief pause + redirect to poll for result
    base_url = voice_config.server_base_url
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Pause length="2"/>
    <Redirect method="POST">{base_url}/voice/result?CallSid={call_sid}&amp;From={html.escape(caller_number)}</Redirect>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


@router.post("/result")
async def handle_result_poll(request: Request):
    """
    Polling endpoint. Twilio redirects here after /voice/respond.
    If the agent is done, return the response. If not, pause + redirect again.
    """
    from control.voice.voice_config import voice_config

    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    caller_number = form_data.get("From", "unknown")

    # Also check query params (from the redirect URL)
    if call_sid == "unknown":
        call_sid = request.query_params.get("CallSid", "unknown")
    if caller_number == "unknown":
        caller_number = request.query_params.get("From", "unknown")

    base_url = voice_config.server_base_url
    pending = _pending_responses.get(call_sid)

    if not pending or pending["status"] == "processing":
        # Not done yet — wait a bit more
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Pause length="2"/>
    <Redirect method="POST">{base_url}/voice/result?CallSid={call_sid}&amp;From={html.escape(caller_number)}</Redirect>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Agent is done — deliver the response
    response_text = pending["response"]
    _pending_responses.pop(call_sid, None)

    safe_response = html.escape(response_text)

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{safe_response}</Say>
    <Gather input="speech" action="{base_url}/voice/respond" method="POST" speechTimeout="2" language="en-US">
    </Gather>
    <Say voice="Polly.Joanna">I didn't hear anything. Call back anytime. Goodbye.</Say>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def handle_call_status(request: Request):
    """Twilio status callback — cleanup when call ends."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    call_status = form_data.get("CallStatus", "unknown")

    logger.info(f"[VOICE] Call status: {call_status} (call={call_sid})")

    if call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
        _close_session(call_sid)

    return Response(content="OK", status_code=200)


# ─── Background Processing ──────────────────────────────────────────────────────


async def _process_speech_background(call_sid: str, caller_number: str, text: str):
    """
    Background task: creates session (if needed), invokes agent, stores result.
    Runs in the background so /voice/respond can return immediately.
    """
    try:
        session = _get_or_create_session(call_sid, caller_number)
        response_text = await _invoke_agent(session, text)
        logger.info(f"[VOICE] Agent done: {response_text[:80]}")
    except Exception as e:
        logger.error(f"[VOICE] Background error: {e}", exc_info=True)
        response_text = "I'm sorry, I had trouble processing that. Could you try again?"

    # Store result for /voice/result to pick up
    _pending_responses[call_sid] = {"status": "done", "response": response_text}


async def _invoke_agent(session: dict, user_text: str) -> str:
    """Feed user text to the LangGraph agent and return response."""
    from langchain_core.messages import HumanMessage

    graph = session["graph"]
    config = session["config"]
    patient_entities = session["patient_entities"]

    invoke_input = {
        "session_id": config["configurable"]["thread_id"],
        "messages": [HumanMessage(content=user_text)],
    }

    if session["first_message"]:
        invoke_input.update(
            {
                "active_intents": [],
                "entities": patient_entities,
                "current_intent": None,
                "response": None,
                "patient_preloaded": bool(patient_entities.get("patient_id")),
                # Explicit state fields
                "patient_id": patient_entities.get("patient_id"),
                "patient_name": (
                    f"{patient_entities['first_name']} {patient_entities['last_name']}"
                    if patient_entities.get("first_name")
                    else None
                ),
                "patient_phone": patient_entities.get(
                    "phone", patient_entities.get("caller_phone")
                ),
                "patient_email": patient_entities.get("email"),
                "selected_doctor_id": None,
                "selected_doctor_name": None,
                "selected_specialty": None,
                "selected_slot": None,
                "selected_appointment_type_id": None,
                "selected_appointment_type": None,
                "selected_appointment_id": None,
                "pending_action": None,
                "available_slots": None,
                "available_doctors": None,
                "active_bookings": None,
                "booking_history": patient_entities.get("booking_history"),
            }
        )
        session["first_message"] = False

    try:
        result = await graph.ainvoke(invoke_input, config=config)
        return result.get("response", "I'm sorry, could you say that again?")
    except Exception as e:
        logger.error(f"[VOICE] Agent error: {e}", exc_info=True)
        return "I'm sorry, I had trouble with that. Could you try again?"
