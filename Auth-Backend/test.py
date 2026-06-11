from src.core.services.jwt_service import JWTService

token = JWTService.create_access_token(
    user_id="123",
    email="doctor@gmail.com",
    role="DOCTOR",
    profile_completed=False,
)

print(token)

payload = JWTService.decode_token(token)

print(payload)
