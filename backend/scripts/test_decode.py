import os
import sys

import jwt

token = os.environ.get("JWT_TO_INSPECT")
secret = os.environ.get("JWT_SIGNING_SECRET")
audience = os.environ.get("JWT_AUDIENCE")

if not token or not secret:
    sys.exit("Defina JWT_TO_INSPECT e JWT_SIGNING_SECRET no ambiente.")

try:
    options = {"verify_aud": bool(audience)}
    decoded = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience=audience,
        options=options,
    )
    print("Success:", decoded)
except Exception as e:
    print(f"Error ({type(e).__name__}): {e}")
