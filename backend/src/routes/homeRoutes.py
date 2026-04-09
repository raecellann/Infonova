from fastapi import APIRouter
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from controllers.homeCotrollers import HomeController
from core.mongodb_connect import create_connection

homeRouter = APIRouter()
home = HomeController()


homeRouter.get('/')(home.index_action)














# @homeRouter.get('/')
# def home():
#     try:

#         mydb = create_connection()

#         cur = mydb.cursor(dictionary=True)

#         cur.execute("SHOW TABLES")

#         for db in cur:
#             print(db)
        
#         port = os.getenv("PORT", 8000)
#         if cur:
#             cur.close()
#             mydb.close()
#             return {
#                 "Response": "True",
#                 "message": f"API is running on port {port}"
#             } 
        
        
#     except Exception as e:
#         return {
#             "Error": e
#         }
