from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import urllib.parse, os
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("URI")

def create_connection():
    # encode your password if it has special chars


    client = MongoClient(URI, server_api=ServerApi('1'))
    
    try:
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas!")
    except Exception as e:
        print("❌ Connection failed:", e)
    
    return client

