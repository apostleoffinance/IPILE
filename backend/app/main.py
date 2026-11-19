from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1 import api_router
from app.api.v1.health import readiness
from app.core.config import get_settings
from app.core.csrf import CsrfMiddleware
from app.core.db import get_db
from app.core.monitoring import RequestContextMiddleware

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.api_route("/", methods=["GET", "HEAD"], tags=["health"])
def root_health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Render platform probe: require a live database and current migrations."""
    return readiness(db)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CsrfMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token", "X-Household-Id"],
)
app.include_router(api_router)
