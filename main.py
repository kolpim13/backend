import time
import dotenv

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from endpoints_passes import router as router_passes
from endpoints_userManagement import router as router_user_management, startup as startup_user_management
from endpoints_logs import router as router_logging
from endpoints_statistics import router as router_statistics

import project_utils as utils
#===========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    print("StartUp")
    await startup_user_management()

    # Program execution
    yield

    # Finilazing code
    print("Finish")
#===========================================================

""" START THE APPLICATION """
# Load environment variables
dotenv.load_dotenv()

# Prepare environment for work
utils.load_environment_variables()
utils.check_create_paths()
utils.databases_init_tables()
utils.check_create_root()

# FastAPI application to run --> add all routers
app = FastAPI(title="Dance School Backend",
              lifespan=lifespan)

# Mount static pages under root
app.mount("/static", StaticFiles(directory="static"), name="signup")
app.mount("/static", StaticFiles(directory="static"), name="terms_and_agreement")

# Add all API routers
app.include_router(router_passes)
app.include_router(router_user_management)
app.include_router(router_logging)
app.include_router(router_statistics)

@app.middleware("http")
async def post_checkin_add_time_log(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"{request.method} {request.url.path} executed in {process_time:.4f} seconds")
    return response

# Load Impakt logo once on the beginning
# impakt_logo = PIL.Image.open("impakt_logo.jpg")
# impakt_logo = impakt_logo.resize((75, 100))
#===========================================================
