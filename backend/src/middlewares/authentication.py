from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import os, jwt

# from fastapi import APIRouter


from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("API_SECRET_KEY")

# print(f"SECRET KEY: {SECRET_KEY}")


async def authentication(request: Request):
    token = request.headers.get("token")
    if not token:
        # return JSONResponse(status_code=401, content={"message": "Unauthenticated User."},)
        raise HTTPException(status_code=401, detail={"message": "Unauthenticated User"})
    
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid Token")
    

    request.state.username = decoded.get("username")
    request.state.user_id = decoded.get("user_id")
    request.state.authenticated = True


    return decoded