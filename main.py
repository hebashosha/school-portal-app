# main.py
import uvicorn
from fastapi import FastAPI
from app.api.v1.endpoints import users
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/swagger-ui",       # Familiar Swagger UI route
    openapi_url="/api/v1/openapi.json"
)

app.include_router(users.router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)