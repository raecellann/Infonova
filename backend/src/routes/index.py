from fastapi import APIRouter
import os
import sys

# Add current directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))

from accountRoutes import accountRouter
from homeRoutes import homeRouter
from ngramRoutes import ngramRouter
from tfidfRoutes import tfidf_router
# from naiveBayesRoutes import naiveBayesRouter

# Create main router
v1 = APIRouter()

# Include all routers
v1.include_router(router=accountRouter, prefix="/account", tags=["ACCOUNT ROUTES"])
v1.include_router(router=homeRouter, prefix="", tags=["HOME"])
v1.include_router(router=ngramRouter, prefix="/ngram", tags=["NGRAM"])
v1.include_router(router=tfidf_router, prefix="/tfidf", tags=["TF-IDF SEARCH"])

# v1.include_router(router=naiveBayesRouter, prefix="/naive-bayes", tags=["CLASSIFICATION"])
