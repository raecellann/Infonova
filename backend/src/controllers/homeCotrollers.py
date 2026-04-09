from fastapi.responses import JSONResponse
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


class HomeController:
    
    def __init__(self):
        self.__controllerName = "Home🏠"

    async def index_action(self):
        return JSONResponse(content={
            "message": "V1 API is App and Running!🚀✨",
            "controller": self.__controllerName
        })
