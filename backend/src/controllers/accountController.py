from fastapi import Request, Depends, HTTPException
import os, sys, jwt
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from schemas.createAccount import CreateAccountRequest
from models.User import User

class AccountController:
    
    def __init__(self):
        self.user = User


    async def create(self, request: Request):
        body = await request.json()

        username = body["username"]
        email = body["email"]
        password = body["PASSWORD"]
        balance = body["balance"]
        fullname = body["fullname"]

        result = self.user.create(self=self.user, username=username, email=email, password=password, balance=balance, fullname=fullname)


        return {
            "message": "Successfully Created account 🟢",
            "data": {
                "recordIndex": result["insertId"]
            }
        }
    



    async def login(self, request: Request):
        body = await request.json()
        username = body["username"]
        password = body["PASSWORD"]
        # print(body["id"], body["username"])

        user = self.user.verify(self=self.user, username=username, password=password)

        print(f"User id: {user["user_id"]}")

        if not user["user_id"]:
            raise HTTPException(status_code=422, detail={
                "success": False,
                "message": "Invalid username or password"
            })


        return {
            "success": True,
            "message": "Successfully Login 🟢",
            "data": {
                "user_id": user["user_id"],
                "username": user["username"],
                "token": jwt.encode({
                    "username": user["username"],
                    "user_id": user["user_id"],
                    "exp": datetime.now() + timedelta(days=1)
                }, os.getenv("API_SECRET_KEY"),
                algorithm="HS256")
            }}
    

    
    



    # async def create(self, request: Request):
    #     body = await request.json()

    #     print(body["username"])
        
    #     return {
    #         "message": "Successfully Create Account",
    #         "data": {
    #             "username": body["username"]
    #         }}



    async def profile(self, request: Request):


        user_id = int(request.state.user_id)

        print(user_id)


        user_info = self.user.getUserProfileByID(self=self.user, user_id=user_id)

        # print(user_info['data']['user_id'])
        # print(user_info)
        
        return {
            "message": "Successfully Get user profile! 🟢",
            "data": {
                "user_id": user_info['data']['user_id'],
                "username": user_info['data']['username'],
                "fullname": user_info['data']['fullname'],
            }
            }
