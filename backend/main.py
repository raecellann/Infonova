from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


import uvicorn


# from src.routes.account import accountRouter
# from src.routes.homeRoutes import homeRouter
from src.routes.index import v1



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


# app.include_router(router=accountRouter, prefix="/v1", tags=["DB Connection"])

# app.include_router(router=homeRouter, prefix="/v1", tags=["HOME"])

app.include_router(router=v1, prefix='/v1', tags=["Router v1"])





# if __name__=="__main__":
    