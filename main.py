from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes import router
from pages.routes import router as pages_router


app = FastAPI(
    title="Windows Scheduler Local API",
    description="API for accessing and managing local scheduler prompts.",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)
app.include_router(pages_router)
