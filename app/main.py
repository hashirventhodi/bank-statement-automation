from fastapi import FastAPI
from app.api.routes import router as api_router
from config.config import API_CONFIG
import uvicorn

app = FastAPI(title="Bank Statement Processor API")

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Bank Statement Processor API"}

# Run the app if executed directly
def main():
    uvicorn.run("app.main:app", host=API_CONFIG["host"], port=API_CONFIG["port"], reload=True)

if __name__ == "__main__":
    main()
