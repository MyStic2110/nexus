import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting IPL Predictor on http://localhost:{settings.PORT}")
    print(f"Backend API: http://localhost:{settings.PORT}")
    print(f"Frontend UI: http://localhost:{settings.PORT}/")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
