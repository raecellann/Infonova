import os, sys
from datetime import datetime
from fastapi import HTTPException


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core.mongodb_connect import create_connection
from utils.hash import encrypt_password





# conn = create_connection()

# cursor = conn.cursor(dictionary=True)

# cursor.execute("SELECT * FROM user")

# for user in cursor.fetchall():
#     print(user)


class User:

    def __init__(self):
        self.conn = create_connection()
        self.cursor = self.conn.cursor(dictionary=True)

    
    def create(self, username: str, email: str, password: str, balance: float, fullname: str):
        """
            Create a new user account. ✨
            
            - **username**: unique username 🌝
            - **email**: unique email ✉️
            - **password**: raw password 🔑
            - **balance**: balance 💸
            - **fullname**: user's full name 💯
        """
        try:
            db = create_connection()
            cur = db.cursor(dictionary=True)

            # if not username or not email or not password or not fullname:
            if not all([username, email, password, fullname]):
                db.rollback()
                cur.close()
                db.close()
                raise HTTPException(status_code=404, detail={
                    "success": False,
                    "message": "Invalid input 🔴"
                    })
            

            # Check if user already exist
            cur.execute("SELECT 1 FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user = cur.fetchone()
            if existing_user:
                db.rollback()  # Rollback if user exists
                cur.close()
                db.close()
                raise HTTPException(
                    status_code=422,
                    detail={"success": False, "message": "Username or Email already exists."}
                )


            # Insert new User in the database
            cur.execute(
                "INSERT INTO users(username, email, password, balance, created_at, fullname) VALUES (%s, %s, %s, %s, %s, %s)",
                (username, email, encrypt_password(password), balance, datetime.now(), fullname))
            
            lastRowAffected = cur.lastrowid

            db.commit()

            

            return {
                "insertId": lastRowAffected
            }
            


        except Exception as e:
            raise HTTPException(status_code=422, detail={
                "success": False,
                "Error": str(e)
            })
        
        finally:
            if cur: cur.close()
            if db: db.close()
        


    
    def verify(self, username: str, password: str):
        """
            Verify user credentials. 🚦✨
            
            - **username**: unique username 🌝
            - **password**: raw password 🔑
        """
        try:
            db = create_connection()
            cur = db.cursor(dictionary=True)

            cur.execute("SELECT user_id, username FROM users WHERE username = %s AND password = %s",
                        (username, encrypt_password(password)))

            user = cur.fetchone()

            return user

        except Exception as e:
            raise HTTPException(status_code=500, detail={
                "success": False,
                "message": "Internal Server Error",
                "Error": str(e)
                })
        

    def getUserProfileByID(self, user_id: int):
        """
            Get *user* By user_id. 🥴
            
            - **user_id**: user's ID 🪪
        """
        

        try:
            if not user_id:
                return {
                    "Response": "False",
                    "message": "No user found!"
                }
            
            db = create_connection()
            cur = db.cursor(dictionary=True)

            cur.execute("SELECT * FROM users WHERE user_id = %s", 
                        [user_id])

            user = cur.fetchone()
            return {
                "Response": "True",
                "data": {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "fullname": user["fullname"]
                }
            }

        except Exception as e:
            return {
                "Response": False,
                "Error": e
            }
    
    # @staticmethod
    # def create(username, email, password):
        
    #     try:
    #         if not username or not email or not password:
    #             return {
    #                 "Response": "False",
    #                 "message": "Invalid Input"
    #             }
            
    #         db = create_connection()
    #         cur = db.cursor(dictionary=True)

    #         cur.execute("SELECT * FROM user")

    #         user = cur.fetchone()


    #         return {
    #             "Response": "True",
    #             "data": {
    #                 "id": user["id"],
    #                 "username": user["username"]
    #             }
    #         }

    #         # for row in cur.fetchall():
    #         #     return {
    #         #         "Response": "True",
    #         #         "data": {
    #         #             "id": row["id"],
    #         #             "username": row["username"],
    #         #             "email": row["email"],
    #         #         }
    #         #     }

    #     except Exception as e:
    #         return {
    #             "Error": e
    #         }

        
        

    

    # @staticmethod
    # def getUserProfileByID(user_id: int):

        

    #     try:
    #         if not user_id:
    #             return {
    #                 "Response": "False",
    #                 "message": "No user found!"
    #             }
            
    #         db = create_connection()
    #         cur = db.cursor(dictionary=True)

    #         cur.execute("SELECT * FROM user")

    #         user = cur.fetchone()
    #         return {
    #             "Response": "True",
    #             "data": {
    #                 "id": user["id"],
    #                 "username": user["username"]
    #             }
    #         }

    #     except Exception as e:
    #         return {
    #             "Response": False,
    #             "Error": e
    #         }

    

    



