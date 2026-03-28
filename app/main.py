from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.routes import auth, match, websocket
from app.db.mongo import init_indexes
from app.logger import main_logger
import os

app = FastAPI(title="IPL Nexus Backend")

# Global Exception Handler for Production-level Logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    main_logger.error(f"Nexus Global Error: {request.method} {request.url} - {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Nexus server error. Connectivity logs recorded."}
    )

# Mount frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")
main_logger.info(f"Mounted static files from {frontend_path}")

@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(frontend_path, "index.html"))

main_logger.info("Initializing routes...")
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(match.router, prefix="/matches", tags=["match"])
app.include_router(websocket.router, tags=["websocket"])
main_logger.info("Routes successfully integrated.")

@app.on_event("startup")
async def startup():
    main_logger.info("Launching Nexus Backend...")
    try:
        await init_indexes()
        main_logger.info("Database indexes confirmed and initialized.")
    except Exception as e:
        main_logger.critical(f"Startup sequence failed: {str(e)}")
        raise e
