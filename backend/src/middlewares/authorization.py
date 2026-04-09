from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import os, jwt


from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("API_KEY")

# print(f"SECRET KEY: {SECRET_KEY}")


async def authorization(request: Request):
    apikey = request.headers.get("apikey")
    
    print(f"apikey: {apikey}")

    if not apikey or (apikey and apikey != API_KEY):
        # return JSONResponse(status_code=401, content={"message": "Unauthenticated User."},)
        raise HTTPException(status_code=401, detail={
            "success": False,
            "message": "Unauthorized"
            })

    

    return