import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from database import init_db
from routers import auth, products, admin, dashboard, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Shafi's Affiliate Marketplace",
    description="Affiliate marketplace for Amazon, Alibaba, AliExpress & Daraz",
    lifespan=lifespan,
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(profile.router)


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/img/favicon.ico")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
