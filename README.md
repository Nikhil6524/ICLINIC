# iClinic Project Documentation

## 1. What this project is

iClinic is a full-stack clinic operations platform with three main parts:

1. `Frontend/` is the React application used by patients and front-desk staff.
2. `Auth-Backend/` is a dedicated FastAPI authentication service that handles login, registration, JWTs, refresh tokens, and role-based access.
3. `Backend/` is the main FastAPI application that manages clinic data, appointments, AI chat, voice calls, and admin scheduling operations.

The system is designed so that authentication is isolated into its own service, while all domain logic such as patient profiles, appointments, doctors, conversations, and voice/chat AI lives in the main backend.

## 2. How the whole project works

### 2.1 High-level flow

1. A user opens the React frontend.
2. The frontend talks to `Auth-Backend` for registration, login, refresh, logout, and current-user identity.
3. After login, the frontend stores the access token locally and also relies on HTTP-only cookies set by the auth service.
4. The frontend talks to `Backend` for patient profile data, appointments, doctor schedules, admin operations, voice initiation, and real-time AI chat.
5. `Backend` validates the JWT, loads patient/admin context, and performs business logic through services and repositories.
6. For AI chat and voice, `Backend` runs a LangGraph workflow that routes each user request into an intent-specific workflow and tool set.
7. PostgreSQL stores the long-lived relational data, while Redis is used for session-like state and slot-locking support.

### 2.2 Main architectural decision

The project uses a layered backend structure:

- API layer: request parsing, route registration, auth dependencies, protocol handling
- Service layer: business rules and validations
- Repository layer: database queries
- Model layer: SQLAlchemy schema definitions
- Control/agent layer: AI orchestration, prompt routing, tool execution, voice/chat workflows

That separation makes it easier to change UI behavior, AI logic, or persistence logic without rewriting the entire system.

### 2.3 Two backend services

This repo intentionally splits auth from domain behavior:

- `Auth-Backend` owns identity and token lifecycle.
- `Backend` trusts the JWT and focuses on clinic workflows.

This is why the frontend has two HTTP clients:

- one client for auth routes
- one client for main business routes

## 3. Runtime architecture

### 3.1 Frontend responsibilities

The frontend provides:

- landing page
- login and registration
- protected patient dashboard
- protected admin/front-desk dashboard
- profile completion flow
- live WebSocket chat with the AI assistant
- voice-call trigger button

### 3.2 Auth service responsibilities

The auth service provides:

- user registration
- login
- token refresh
- logout
- current user lookup
- RBAC metadata through the user role in the token

### 3.3 Main backend responsibilities

The main backend provides:

- departments, staff, doctors, patients, appointment types
- appointment creation, cancellation, rescheduling, listing
- doctor unavailability management
- notification and conversation endpoints
- real-time WebSocket chat
- Twilio voice workflow
- LangGraph-based AI front desk agent

### 3.4 Database and Redis

- PostgreSQL stores users, roles, patients, doctors, appointments, conversations, and audit data.
- Redis supports session-like state and temporary coordination for AI/voice flows.

## 4. Important request flows

### 4.1 Login flow

1. User submits login in the frontend.
2. `Frontend/src/features/auth/services/authService.ts` calls `Auth-Backend`.
3. `Auth-Backend/src/api/rest/routes/auth.py` delegates to `AuthService`.
4. `AuthService` validates credentials, generates access and refresh tokens, stores hashed refresh token records, and returns auth state.
5. Cookies are set by the auth backend, and the frontend also stores the access token for cross-service calls to `Backend`.

### 4.2 Protected page flow

1. `AuthContext` loads current user via `/users/me`.
2. `ProtectedLayout` checks authentication, role, and profile completion.
3. Patients with incomplete profiles are forced into the profile completion screen.
4. Admin/front-desk users are redirected to the admin dashboard instead of the patient dashboard.

### 4.3 Chat flow

1. `useWebSocketChat` opens a WebSocket to `/ws/chat?token=...`.
2. `Backend/src/api/rest/routes/websockets.py` accepts the connection.
3. The backend decodes the token and preloads patient identity into the conversation state.
4. A LangGraph graph is built for that session with tools and routing logic.
5. Each message is classified into an intent and run through the correct workflow node.
6. Tool calls can fetch doctors, find slots, create appointments, reschedule, cancel, escalate, or inspect existing bookings.
7. Responses are streamed back to the frontend in chunks for a typing effect.

### 4.4 Voice flow

1. The patient starts a voice call from the frontend.
2. The backend’s voice route and `voice_service.py` create or resume a call session.
3. Twilio sends speech input to the backend.
4. The same LangGraph agent processes the speech text.
5. The backend stores a pending response and Twilio polls until the response is ready.
6. If escalation is triggered, the call can be forwarded to a human number.

### 4.5 Admin scheduling flow

1. `AdminDashboard.tsx` requests a day schedule from the backend.
2. The backend assembles doctor working windows, booked appointments, and blocked periods.
3. The frontend renders those into a Gantt-like schedule board.
4. Staff can add doctors, block time, book appointments for patients, or cancel booked slots.

## 5. Root-level files

- `README.md`: broad project summary, architecture sketch, setup steps, feature list, and example endpoints.
- `pyproject.toml`: shared Python dependency definition and Ruff configuration for the workspace.
- `uv.lock`: exact Python dependency lock file for reproducible installs.
- `main.py`: tiny root entry script; not the actual app bootstrap used in deployment.
- `docker-compose.yml`: orchestrates Postgres, Redis, auth backend, main backend, and frontend containers.
- `alembic.ini`: root Alembic config for migrations at the repository root.
- `.dockerignore`: excludes unnecessary files from Docker build context.
- `.gitignore`: standard Git ignore rules for local artifacts.
- `.pre-commit-config.yaml`: pre-commit hook config.
- `.python-version`: local Python version hint for toolchains.

## 6. Root Alembic files

- `alembic/env.py`: root migration environment for SQLAlchemy/Alembic.
- `alembic/script.py.mako`: migration template used when generating new revision files.
- `alembic/README`: standard Alembic notes.
- `alembic/versions/4a21082b72cb_initial_schema_with_rbac.py`: initial migration for the top-level Alembic setup.

## 7. Frontend overview

The frontend is a Vite + React + TypeScript SPA. It is organized by feature so each area owns its components and service calls.

### 7.1 Frontend build/config files

- `Frontend/package.json`: frontend package metadata, scripts, and JS dependencies.
- `Frontend/package-lock.json`: exact npm dependency lock file.
- `Frontend/vite.config.ts`: Vite build/dev configuration.
- `Frontend/tsconfig.json`: top-level TypeScript project references.
- `Frontend/tsconfig.app.json`: app TypeScript compiler settings.
- `Frontend/tsconfig.node.json`: Node-side TypeScript settings for tooling files.
- `Frontend/eslint.config.js`: ESLint rules for the frontend codebase.
- `Frontend/index.html`: root HTML shell that hosts the React app.
- `Frontend/Dockerfile`: builds the frontend and serves it through Nginx.
- `Frontend/nginx.conf`: Nginx configuration for serving the built SPA.
- `Frontend/README.md`: frontend-specific notes.
- `Frontend/public/favicon.svg`: browser tab icon.
- `Frontend/public/icons.svg`: shared SVG asset sheet.

### 7.2 Frontend application entry files

- `Frontend/src/main.tsx`: React root mount; renders `<App />`.
- `Frontend/src/App.tsx`: top-level app component that delegates routing to `AppRouter`.
- `Frontend/src/App.css`: app-scoped styles used by `App.tsx`.
- `Frontend/src/index.css`: base stylesheet imported into the app.
- `Frontend/src/styles/global.css`: global design system and app-wide style rules.

### 7.3 Frontend routing and layout

- `Frontend/src/app/routes/AppRouter.tsx`: defines public and protected routes and wraps everything in `AuthProvider`.
- `Frontend/src/components/layout/AuthLayout.tsx`: layout wrapper for public auth pages.
- `Frontend/src/components/layout/ProtectedLayout.tsx`: guards private pages, handles role redirects, and enforces profile completion.

### 7.4 Frontend config and transport

- `Frontend/src/config/env.ts`: centralizes environment-driven base URLs for auth API, backend API, and WebSocket server.
- `Frontend/src/lib/axios.ts`: auth-focused Axios client for `Auth-Backend`.
- `Frontend/src/lib/backendClient.ts`: backend-focused Axios client; attaches bearer tokens and auto-refreshes on `401`.

### 7.5 Auth feature files

- `Frontend/src/features/auth/context/AuthContext.tsx`: global auth state container; loads current user, exposes login/register/logout, and syncs the backend token store.
- `Frontend/src/features/auth/services/authService.ts`: typed auth API wrapper for register, login, refresh, logout, and `/users/me`.
- `Frontend/src/features/auth/hooks/useLogin.ts`: custom hook for login form handling.
- `Frontend/src/features/auth/hooks/useRegister.ts`: custom hook for registration form handling.
- `Frontend/src/features/auth/components/LoginForm.tsx`: login screen UI and submit behavior.
- `Frontend/src/features/auth/components/RegisterForm.tsx`: registration UI and submit behavior.

### 7.6 Landing feature files

- `Frontend/src/features/landing/components/LandingPage.tsx`: marketing-style public homepage and first entry experience.
- `Frontend/src/features/landing/components/LandingPage.css`: styles for the landing page.

### 7.7 Profile feature files

- `Frontend/src/features/profile/services/profileService.ts`: patient profile API wrapper for load/update flows.
- `Frontend/src/features/profile/components/CompleteProfile.tsx`: form shown after signup for patients who must finish profile details before using the product.
- `Frontend/src/features/profile/components/CompleteProfile.css`: styling for the profile completion flow.

### 7.8 Dashboard feature files

- `Frontend/src/features/dashboard/components/Dashboard.tsx`: patient home screen; loads profile and appointment data, hosts chat UI, voice button, quick actions, and editable profile/settings panels.
- `Frontend/src/features/dashboard/components/Dashboard.css`: patient dashboard styles.
- `Frontend/src/features/dashboard/services/appointmentService.ts`: patient-facing appointment API wrapper.

### 7.9 Chat feature files

- `Frontend/src/hooks/useWebSocketChat.ts`: core chat state machine for WebSocket connect/reconnect, ping/pong, streamed messages, optimistic user messages, and chat reset.
- `Frontend/src/features/chat/components/ChatPage.tsx`: standalone page wrapper for chat.
- `Frontend/src/features/chat/components/ChatWindow.tsx`: renders messages and input controls for the AI chat interface.
- `Frontend/src/features/chat/components/Chat.css`: styles for chat UI elements.
- `Frontend/src/features/chat/components/CallButton.tsx`: triggers voice-call initiation from the UI.
- `Frontend/src/features/chat/hooks/useVoiceCall.ts`: hook that manages frontend state for starting a voice session.
- `Frontend/src/features/chat/services/voiceService.ts`: typed API wrapper for voice-call endpoints.

### 7.10 Admin feature files

- `Frontend/src/features/admin/components/AdminDashboard.tsx`: front-desk/admin workspace with schedule board, date navigation, doctor creation, time blocking, booking modal, slot inspection, and appointment cancellation.
- `Frontend/src/features/admin/components/AdminDashboard.css`: admin scheduling dashboard styling.
- `Frontend/src/features/admin/services/adminService.ts`: admin API wrapper for schedules, doctors, appointments, departments, appointment types, and blocked time.

## 8. Auth-Backend overview

This service is a focused auth microservice. It does not manage appointments or clinic operations; it only manages identity, tokens, and RBAC-linked user data.

### 8.1 Auth-Backend top-level files

- `Auth-Backend/dockerfile`: container build instructions for the auth service.
- `Auth-Backend/requirements.txt`: auth backend Python dependency list.
- `Auth-Backend/seed.py`: seed utility for auth-related bootstrap data.
- `Auth-Backend/test.py`: ad hoc test/helper script for auth backend behavior.

### 8.2 Auth-Backend application entry and route wiring

- `Auth-Backend/src/main.py`: ASGI import entrypoint; exposes `app`.
- `Auth-Backend/src/api/rest/app.py`: creates FastAPI app, applies CORS, and registers health/auth/user routes.
- `Auth-Backend/src/api/rest/dependencies.py`: shared dependency providers, especially DB session injection and current-user extraction.
- `Auth-Backend/src/api/rest/routes/health.py`: lightweight health endpoint.
- `Auth-Backend/src/api/rest/routes/auth.py`: register/login/refresh/logout endpoints and cookie handling.
- `Auth-Backend/src/api/rest/routes/users.py`: current-user route(s) such as `/users/me`.

### 8.3 Auth-Backend config files

- `Auth-Backend/src/config/settings.py`: auth service environment settings.
- `Auth-Backend/src/config/security.py`: auth constants such as JWT algorithm and token expiration durations.
- `Auth-Backend/src/config/database.py`: SQLAlchemy engine/session setup for the auth DB connection.

### 8.4 Auth-Backend service layer

- `Auth-Backend/src/core/services/auth_service.py`: central auth workflow; validates credentials, creates tokens, stores refresh tokens, refreshes sessions, and revokes on logout.
- `Auth-Backend/src/core/services/jwt_service.py`: token creation and decoding logic.
- `Auth-Backend/src/core/services/password_service.py`: password hashing and verification orchestration.
- `Auth-Backend/src/core/services/user_service.py`: user-oriented business operations.
- `Auth-Backend/src/core/services/role_service.py`: role-related lookup/business logic.
- `Auth-Backend/src/core/services/authorization_service.py`: role/permission authorization helpers.

### 8.5 Auth-Backend data clients

- `Auth-Backend/src/data/clients/postgres_client.py`: DB session generator/helpers for the auth service.

### 8.6 Auth-Backend ORM models

- `Auth-Backend/src/data/models/postgres/base.py`: SQLAlchemy base metadata for auth models.
- `Auth-Backend/src/data/models/postgres/user.py`: user table definition including email, password hash, active state, role, and profile completion state.
- `Auth-Backend/src/data/models/postgres/role.py`: role table definition.
- `Auth-Backend/src/data/models/postgres/permission.py`: permission table definition.
- `Auth-Backend/src/data/models/postgres/role_permission.py`: join table linking roles to permissions.
- `Auth-Backend/src/data/models/postgres/refresh_token.py`: persisted refresh token hashes and expiry/revocation state.

### 8.7 Auth-Backend repositories

- `Auth-Backend/src/data/repositories/user_repository.py`: user queries and persistence helpers.
- `Auth-Backend/src/data/repositories/role_repository.py`: role lookup helpers.
- `Auth-Backend/src/data/repositories/permission_repository.py`: permission lookup helpers.
- `Auth-Backend/src/data/repositories/role_permission_repository.py`: role-permission join queries.
- `Auth-Backend/src/data/repositories/refresh_token_repository.py`: refresh token insert, revoke, and lookup behavior.

### 8.8 Auth-Backend schemas

- `Auth-Backend/src/schemas/auth/login_request.py`: login request payload validation.
- `Auth-Backend/src/schemas/auth/register_request.py`: registration payload validation.
- `Auth-Backend/src/schemas/auth/token_response.py`: auth response model containing access token and profile status.
- `Auth-Backend/src/schemas/auth/user_response.py`: current-user response model.

### 8.9 Auth-Backend utility files

- `Auth-Backend/src/utils/password_utils.py`: lower-level password hashing helpers.
- `Auth-Backend/src/utils/jwt_utils.py`: lower-level JWT helper functions.
- `Auth-Backend/src/utils/cookie_utils.py`: reusable auth cookie helpers.

## 9. Main Backend overview

This is the business and AI core of the platform. It exposes REST routes for clinic operations and real-time protocols for chat and voice.

### 9.1 Backend top-level files

- `Backend/ReadMe.md`: backend-specific documentation notes.
- `Backend/dockerfile`: container build instructions for the main backend.
- `Backend/alembic.ini`: backend-scoped Alembic config.
- `Backend/src/main.py`: ASGI import entrypoint exposing the backend `app`.
- `Backend/src/seed.py`: data seed script for clinic-domain entities.
- `Backend/requirements/requirements.md`: notes about backend dependency requirements.

### 9.2 Backend docs folder

- `Backend/docs/Architecture.md`: short architecture summary.
- `Backend/docs/Project_overview.md`: project goals and actor summary.
- `Backend/docs/DB_schema.md`: schema documentation for database design.
- `Backend/docs/Chat_flow.md`: notes about AI chat lifecycle.
- `Backend/docs/Voice_flow.md`: notes about voice-call flow.
- `Backend/docs/Redis_design.md`: Redis usage notes.
- `Backend/docs/Agent_Architecture.md`: AI agent design description.
- `Backend/docs/Appointment.md`: appointment-related domain notes.
- `Backend/docs/Non_Funtional_requiremements.md`: quality and operational requirement notes.

### 9.3 Backend Alembic files

- `Backend/alembic/env.py`: Alembic runtime environment for backend migrations.
- `Backend/alembic/script.py.mako`: backend migration template.
- `Backend/alembic/README`: Alembic notes.
- `Backend/alembic/versions/06dc6fb5628f_initial_schema_auth_and_backend_tables.py`: major initial schema migration that ties auth and domain tables together.
- `Backend/alembic/versions/add_user_id_to_patients.py`: migration that links patients back to auth users.

### 9.4 Backend API application files

- `Backend/src/api/rest/app.py`: main FastAPI app bootstrap, CORS config, route registration, background tasks, and LLM warmup.
- `Backend/src/api/rest/dependencies.py`: DB session injection, JWT extraction, and role enforcement dependency factory.
- `Backend/src/api/middleware/error_handler.py`: catch-all JSON error middleware to stop unhandled exceptions from crashing the app.

### 9.5 Backend REST route files

- `Backend/src/api/rest/routes/health.py`: simple health endpoint.
- `Backend/src/api/rest/routes/departments.py`: CRUD/read routes for departments.
- `Backend/src/api/rest/routes/staff.py`: routes for staff records and staff-facing operations.
- `Backend/src/api/rest/routes/doctors.py`: doctor listing and creation endpoints.
- `Backend/src/api/rest/routes/patients.py`: patient profile endpoints such as current patient details and updates.
- `Backend/src/api/rest/routes/appointment_types.py`: appointment type list/manage endpoints.
- `Backend/src/api/rest/routes/appointments.py`: appointment booking, rescheduling, cancellation, patient history, and admin schedule endpoints.
- `Backend/src/api/rest/routes/doctor_unavailability.py`: manual doctor blocked-time endpoints.
- `Backend/src/api/rest/routes/notifications.py`: notification retrieval/management endpoints.
- `Backend/src/api/rest/routes/conversations.py`: conversation history endpoints.
- `Backend/src/api/rest/routes/audit_logs.py`: audit log listing or inspection endpoints.
- `Backend/src/api/rest/routes/websockets.py`: WebSocket chat protocol, session setup, patient preloading, graph invocation, rate limiting, streaming response behavior, and message persistence.
- `Backend/src/api/rest/routes/voice.py`: Twilio-facing voice endpoints; handles telephony protocol and delegates session logic to `voice_service.py`.

### 9.6 Backend config files

- `Backend/src/config/settings.py`: environment settings for DB, Redis, auth service URL, and JWT verification.
- `Backend/src/config/database.py`: SQLAlchemy engine and session configuration for the main backend.

### 9.7 Backend data clients

- `Backend/src/data/clients/postgres_client.py`: DB session helpers for request-scoped and manual DB usage.
- `Backend/src/data/clients/redis_client.py`: Redis session-store and temporary state helpers used by agent/voice flows.

### 9.8 Backend ORM model files

- `Backend/src/data/models/postgres/base.py`: SQLAlchemy base and shared model metadata.
- `Backend/src/data/models/postgres/__init__.py`: model package export wiring.
- `Backend/src/data/models/postgres/department.py`: clinic departments such as cardiology or dermatology.
- `Backend/src/data/models/postgres/doctor.py`: doctors, specialization, department link, work hours, and active state.
- `Backend/src/data/models/postgres/staff.py`: staff identities for front desk/admin actors.
- `Backend/src/data/models/postgres/patient.py`: patient record linked to auth user and used throughout booking flows.
- `Backend/src/data/models/postgres/appointment_type.py`: appointment type catalog and default duration definition.
- `Backend/src/data/models/postgres/appointment.py`: appointment entity with patient, doctor, type, time range, status, and source metadata.
- `Backend/src/data/models/postgres/doctor_unavailability.py`: blocked windows for doctors, including manual blocks and appointment-reserved slots.
- `Backend/src/data/models/postgres/notification.py`: outbound or internal notification records.
- `Backend/src/data/models/postgres/conversation.py`: parent conversation/session records for chat or voice interactions.
- `Backend/src/data/models/postgres/conversation_message.py`: individual messages inside a conversation.
- `Backend/src/data/models/postgres/audit_log.py`: audit trail records for important system actions.

### 9.9 Backend repository files

- `Backend/src/data/repositories/department_repository.py`: department queries.
- `Backend/src/data/repositories/doctor_repository.py`: doctor queries and persistence.
- `Backend/src/data/repositories/staff_repository.py`: staff queries.
- `Backend/src/data/repositories/patient_repository.py`: patient lookup helpers including user-linked lookup.
- `Backend/src/data/repositories/appointment_type_repository.py`: appointment type lookups and active-type retrieval.
- `Backend/src/data/repositories/appointment_repository.py`: appointment persistence and time-range conflict queries.
- `Backend/src/data/repositories/doctor_unavailability_repository.py`: blocked-time queries across doctor/date windows.
- `Backend/src/data/repositories/notification_repository.py`: notification read/write helpers.
- `Backend/src/data/repositories/conversation_repository.py`: conversation parent record queries.
- `Backend/src/data/repositories/conversation_message_repository.py`: individual conversation-message queries.
- `Backend/src/data/repositories/audit_log_repository.py`: audit persistence and retrieval.

### 9.10 Backend service layer files

- `Backend/src/core/services/department_service.py`: business rules around departments.
- `Backend/src/core/services/doctor_service.py`: doctor creation/listing and doctor-related validations.
- `Backend/src/core/services/staff_service.py`: staff business logic.
- `Backend/src/core/services/patient_service.py`: patient profile retrieval/update and patient resolution by user or phone.
- `Backend/src/core/services/appointment_service.py`: the core appointment engine; validates patient and doctor existence, checks working hours and conflicts, creates bookings, manages reschedules/cancellations, and calculates availability.
- `Backend/src/core/services/notification_service.py`: notification handling.
- `Backend/src/core/services/conversation_service.py`: conversation-history business logic.
- `Backend/src/core/services/audit_log_service.py`: audit-log business operations.
- `Backend/src/core/services/voice_service.py`: voice session lifecycle, patient identification, Twilio call state support, shared agent invocation for speech input, and session cleanup.
- `Backend/src/core/exceptions/__init__.py`: exception package placeholder/shared exports.

### 9.11 Backend AI control layer

This is the most distinctive part of the codebase. It contains the AI receptionist implementation.

#### General control files

- `Backend/src/control/chat.py`: likely local/manual chat runner for text-based testing outside the WebSocket route.
- `Backend/src/control/chat_live.py`: likely live chat/testing harness for agent behavior.

#### Control config and factories

- `Backend/src/control/config/openrouter_config.py`: OpenRouter-related configuration for model access.
- `Backend/src/control/factories/llm_factory.py`: builds the right LLM clients for standard chat, routing, and voice use cases.
- `Backend/src/control/factories/tool_factory.py`: constructs the tool registry for the graph using DB-backed service dependencies.

#### Control models and state

- `Backend/src/control/models/intent.py`: intent enum definitions such as booking, availability, rescheduling, cancellation, escalation, and general support.
- `Backend/src/control/models/intent_score.py`: scored intent structure used during routing/tool selection.
- `Backend/src/control/models/routing_result.py`: typed routing output container.
- `Backend/src/control/state/conversation_state.py`: LangGraph state schema for all conversation/session fields.

#### Control routing and graph files

- `Backend/src/control/routing/llm_intent_router.py`: LLM-driven intent classifier/router.
- `Backend/src/control/routing/tool_registry.py`: maps intents to the correct tool set.
- `Backend/src/control/nodes/router_node.py`: graph node that determines the current intent.
- `Backend/src/control/nodes/workflow_node.py`: graph node that runs the intent-specific prompt and tools.
- `Backend/src/control/graphs/frontdesk_graph.py`: assembles the whole LangGraph flow and compiles it with a checkpointer.

#### Control prompt files

- `Backend/src/control/prompts/system_prompt.py`: system prompts for each workflow type such as booking, cancellation, rescheduling, escalation, availability, and general conversation.

#### Control adapter files

- `Backend/src/control/adapters/tool_adapter.py`: adapter layer that makes internal tool implementations compatible with graph/tool calling.

#### Control tool files

- `Backend/src/control/tools/base_tool.py`: base abstraction shared by concrete agent tools.
- `Backend/src/control/tools/doctor_tool.py`: doctor search/selection support for the agent.
- `Backend/src/control/tools/availability_tool.py`: checks available time slots for doctors and appointment types.
- `Backend/src/control/tools/patient_tool.py`: patient identity or patient-data operations needed by the agent.
- `Backend/src/control/tools/appointment_tool.py`: creates appointments from the AI workflow.
- `Backend/src/control/tools/reschedule_tool.py`: handles moving existing appointments.
- `Backend/src/control/tools/cancellation_tool.py`: cancels appointments through the AI workflow.
- `Backend/src/control/tools/active_bookings_tool.py`: retrieves a patient’s existing active bookings to support follow-up actions.
- `Backend/src/control/tools/escalation_tool.py`: marks or triggers escalation to human support.
- `Backend/src/control/tools/sms_tool.py`: sends SMS notifications or confirmations.

#### Voice support files

- `Backend/src/control/voice/__init__.py`: voice package marker/exports.
- `Backend/src/control/voice/voice_config.py`: voice-related configuration values for AI/telephony flows.

## 10. How the layers depend on each other

The dependency direction is mostly:

1. frontend components call frontend services
2. frontend services call auth/backend APIs
3. backend routes call backend services
4. backend services call repositories
5. repositories operate on SQLAlchemy models
6. AI routes additionally call graph/factory/tool logic

That means business rules are not embedded directly into route handlers or React components. Most important logic lives in service files and AI tool files.

## 11. Files that matter most for understanding the system quickly

If someone is onboarding and wants the shortest useful path through the codebase, these are the first files to read:

1. `README.md`
2. `docker-compose.yml`
3. `Frontend/src/app/routes/AppRouter.tsx`
4. `Frontend/src/features/auth/context/AuthContext.tsx`
5. `Frontend/src/features/dashboard/components/Dashboard.tsx`
6. `Frontend/src/features/admin/components/AdminDashboard.tsx`
7. `Frontend/src/hooks/useWebSocketChat.ts`
8. `Auth-Backend/src/api/rest/routes/auth.py`
9. `Auth-Backend/src/core/services/auth_service.py`
10. `Backend/src/api/rest/app.py`
11. `Backend/src/api/rest/routes/websockets.py`
12. `Backend/src/api/rest/routes/voice.py`
13. `Backend/src/core/services/appointment_service.py`
14. `Backend/src/core/services/voice_service.py`
15. `Backend/src/control/graphs/frontdesk_graph.py`
16. `Backend/src/control/routing/llm_intent_router.py`
17. `Backend/src/control/tools/appointment_tool.py`
18. `Backend/src/control/tools/availability_tool.py`


## 13. Final summary

This project works as an AI-powered clinic operating system with:

- a patient-facing React app
- a role-aware admin/front-desk dashboard
- a dedicated authentication microservice
- a main clinic-domain backend
- a LangGraph-powered conversational booking agent
- WebSocket chat and Twilio voice support
- PostgreSQL for durable data and Redis for transient session/state support

