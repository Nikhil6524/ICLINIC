# iClinic — AI-Powered Hospital Booking System

An intelligent clinic management platform with an AI front desk agent that handles appointment booking, rescheduling, and cancellations via real-time chat and voice calls.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│    Frontend      │     │   Auth-Backend   │     │     Backend      │
│  React + Vite   │────▶│  FastAPI :8001   │     │  FastAPI :8000   │
│    Port 5173    │     │  JWT + RBAC      │     │  AI Agent + API  │
└────────┬────────┘     └──────────────────┘     └────────┬─────────┘
         │                                                 │
         │◀───── WebSocket (real-time chat) ──────────────▶│
         │◀───── REST API (appointments, profile) ────────▶│
         │                                                 │
         │                                      ┌──────────┴──────────┐
         │                                      │    LangGraph Agent   │
         │                                      │  Intent Router → Tools│
         │                                      └──────────┬──────────┘
         │                                                 │
         │                              ┌──────────────────┼──────────────────┐
         │                              │                  │                  │
         │                        ┌─────┴─────┐    ┌──────┴──────┐   ┌──────┴──────┐
         │                        │ PostgreSQL │    │    Redis    │   │   Twilio    │
         │                        │  Database  │    │ Slot Locks  │   │ Voice + SMS │
         │                        └───────────┘    └─────────────┘   └─────────────┘
```

## Features

### Patient Dashboard
- Real-time AI chat (WebSocket) for booking, rescheduling, cancelling appointments
- Voice call via Twilio — AI receptionist calls the patient's phone
- Profile management with inline editing
- Appointment history (upcoming + past)

### Admin Dashboard (Front Desk)
- Gantt chart view of all doctors' daily schedules
- Color-coded: green (available), red (booked), gray (blocked)
- Book appointments on behalf of patients (name + phone)
- Block doctor time slots (meetings, surgery, breaks)
- Add new doctors with working hours
- Cancel appointments directly from the chart
- SMS confirmations sent automatically

### AI Agent
- LangGraph state machine with intent routing
- 6 intents: book, check availability, reschedule, cancel, escalate, general
- 8 tools: doctor lookup, availability, patient management, booking, rescheduling, cancellation, escalation, active bookings
- LLM-based intent classification (fast router model)
- Conversation memory with checkpointing
- Patient pre-identification from JWT (no need to ask for name/phone)

### Voice Integration
- Outbound calls via Twilio (patient-initiated from the app)
- Speech-to-text via Twilio Gather
- Text-to-speech via Polly.Joanna
- Redirect-polling pattern to handle Twilio's 15s timeout
- Escalation with call forwarding to staff

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite 8, react-router-dom v7 |
| Auth Service | FastAPI, JWT (access + refresh), bcrypt, RBAC |
| Backend API | FastAPI, SQLAlchemy, Pydantic |
| AI Agent | LangGraph, LangChain, OpenRouter/Groq LLMs |
| Database | PostgreSQL (via SQLAlchemy ORM) |
| Cache | Redis (slot locking, session state) |
| Voice/SMS | Twilio (calls, SMS confirmations) |
| Infra | Docker, docker-compose, Alembic migrations |

## Project Structure

```
ICLINIC/
├── Frontend/              # React SPA
│   ├── src/
│   │   ├── features/     # auth, chat, dashboard, admin, profile
│   │   ├── hooks/        # useWebSocketChat
│   │   ├── lib/          # axios clients (auth + backend)
│   │   └── styles/       # global CSS
│   └── package.json
│
├── Backend/               # Main API + AI Agent
│   ├── src/
│   │   ├── api/          # REST routes + middleware
│   │   ├── control/      # LangGraph agent (graphs, tools, routing, prompts)
│   │   ├── core/         # Business logic services
│   │   ├── data/         # Models, repositories, DB clients
│   │   └── config/       # Settings
│   ├── alembic/          # Database migrations
│   ├── docs/             # Architecture documentation
│   └── dockerfile
│
├── Auth-Backend/          # Authentication microservice
│   ├── src/
│   │   ├── api/          # Auth routes (register, login, refresh, logout)
│   │   ├── core/         # Auth service, JWT service, password service
│   │   ├── data/         # User, Role, RefreshToken models + repos
│   │   └── config/       # Settings, security
│   └── dockerfile
│
└── docker-compose.yml     # PostgreSQL + Redis + services
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### 1. Database Setup

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run migrations
cd Backend
alembic upgrade head
```

### 2. Auth-Backend (Port 8001)

```bash
cd Auth-Backend
pip install -e .
cp .env.example .env  # Configure your secrets
uvicorn src.main:app --port 8001
```

### 3. Backend (Port 8000)

```bash
cd Backend
pip install -e .
cp .env.example .env  # Configure DB, Redis, Twilio, LLM keys
uvicorn src.main:app --port 8000
```

### 4. Frontend (Port 5173)

```bash
cd Frontend
npm install
npm run dev
```

### 5. Access the app

- Patient: http://localhost:5173 → Register → Complete profile → Chat
- Admin: http://localhost:5173 → Login with ADMIN role → Gantt chart dashboard

## Environment Variables

### Backend (.env)
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=iclinic_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

REDIS_HOST=localhost
REDIS_PORT=6379

JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# LLM (choose one)
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-...

# Twilio
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Ngrok (for Twilio webhooks in dev)
SERVER_BASE_URL=https://your-ngrok-url.ngrok-free.dev
```

## API Endpoints

### Auth-Backend (:8001)
| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/register | Register (email, password, role) |
| POST | /auth/login | Login → access_token + cookie |
| POST | /auth/refresh | Refresh access token |
| POST | /auth/logout | Clear refresh token |
| GET | /users/me | Current user info |

### Backend (:8000)
| Method | Path | Description |
|--------|------|-------------|
| WS | /ws/chat | Real-time AI chat |
| GET | /appointments/me | Patient's appointments |
| GET | /appointments/admin/schedule | Admin Gantt chart data |
| POST | /appointments/frontdesk-book | Admin books for patient |
| POST | /voice/initiate | Trigger outbound call |
| GET | /patients/me | Current patient profile |
| PUT | /patients/me | Update profile |
| GET | /doctors | List all doctors |
| POST | /doctors | Add doctor (admin) |
| POST | /doctor-unavailability | Block time (admin) |

## Roles (RBAC)

| Role | Access |
|------|--------|
| PATIENT | Chat, voice call, own appointments, profile |
| ADMIN | All of above + Gantt chart, book/cancel for patients, add doctors, block time |
| FRONT_DESK | Same as ADMIN |
| DOCTOR | View own schedule, unavailability |

## License

Private — all rights reserved.
