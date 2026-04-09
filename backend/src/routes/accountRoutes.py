from fastapi import APIRouter, Depends
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from middlewares.authorization import authorization
from middlewares.authentication import authentication
from controllers.accountController import AccountController

accountRouter = APIRouter()
accountController = AccountController()



accountRouter.post("/login", dependencies=[Depends(authorization)])(accountController.login)
accountRouter.post("/sign-up", dependencies=[Depends(authorization)])(accountController.create)
accountRouter.get("/profile", dependencies=[Depends(authentication)])(accountController.profile)