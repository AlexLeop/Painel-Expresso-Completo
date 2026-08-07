import jwt

token = jwt.encode({"sub": "123"}, "secret", algorithm="HS256")
try:
    jwt.decode(token, "wrong_secret", algorithms=["HS256"])
except Exception as e:
    print("Exception class:", e.__class__.__name__)
    print("Is instance of InvalidTokenError:", isinstance(e, jwt.InvalidTokenError))
