from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.database import init_db
from routes import admin, pages, recipes
from routes import menu_new
from fastapi.responses import FileResponse

app = FastAPI(title="Virentoftakoket")

# Initiera databasen vid start
init_db()

# Routers
app.include_router(pages.router)
app.include_router(recipes.router, prefix="/api", tags=["recipes"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(menu_new.router)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.data_dir / "images"), name="uploads")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Enkel hälso-kontroll för lokal utveckling."""
    return {"status": "ok"}


@app.get("/favicon.ico")
def favicon() -> FileResponse:
    """Serva favicon till klienter som implicit frågar efter /favicon.ico."""
    return FileResponse(settings.static_dir / "favicon.png")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
