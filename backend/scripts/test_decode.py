import jwt

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kcnV0YXdncm9wd2dzbXd5Z3R6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc0NTI3NSwiZXhwIjoyMDk3MzIxMjc1fQ.yOnMaVfpwksz_9TdufDMOVVDHIeZHTuuJGsM7uPiLMY"
secret = "super-secret-jwt-token-with-at-least-32-characters-long"
audience = "authenticated"

try:
    decoded = jwt.decode(token, secret, algorithms=["HS256"], audience=audience)
    print("Success:", decoded)
except Exception as e:
    print(f"Error ({type(e).__name__}): {e}")
