from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import PORT
from app.database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_fts()
    db.load_from_json()
    db.init_default_admin()
    await db.start_dump_loop()
    yield
    await db.shutdown()


app = FastAPI(
    title="Glossary Term Management System",
    description="多语言多领域术语库管理系统",
    version="1.0.0",
    lifespan=lifespan,
)


from app.routers import terms, audit, lookup, check, import_export, users, points, notifications, subscriptions, recommendations, learning, graph, statistics, meetings, workflow

app.include_router(lookup.router)
app.include_router(terms.router)
app.include_router(audit.router)
app.include_router(check.router)
app.include_router(import_export.router)
app.include_router(users.router)
app.include_router(points.router)
app.include_router(notifications.router)
app.include_router(subscriptions.router)
app.include_router(recommendations.router)
app.include_router(learning.router)
app.include_router(graph.router)
app.include_router(statistics.router)
app.include_router(meetings.router)
app.include_router(workflow.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "terms_count": len(db.terms), "users_count": len(db.users)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
