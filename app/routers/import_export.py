from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.models import ExportFilter
from app.services import import_export_service
from app.services.user_service import get_user_by_token

router = APIRouter(prefix="/api/import-export", tags=["import-export"])


def _resolve_user(x_user_id: Optional[str]) -> dict:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-ID header required")
    user = get_user_by_token(x_user_id)
    if not user:
        from app.services.user_service import get_user
        user = get_user(x_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token or ID")
    return user


@router.post("/import/tbx")
async def import_tbx(file: UploadFile, x_user_id: Optional[str] = Header(None)):
    """Import terms from a TBX file."""
    user = _resolve_user(x_user_id)
    content = await file.read()
    result = import_export_service.import_tbx(content, user["user_id"])
    return result


@router.post("/import/csv")
async def import_csv(file: UploadFile, x_user_id: Optional[str] = Header(None)):
    """Import terms from a CSV file."""
    user = _resolve_user(x_user_id)
    content = await file.read()
    result = import_export_service.import_csv(content, user["user_id"])
    return result


@router.post("/import/excel")
async def import_excel(file: UploadFile, x_user_id: Optional[str] = Header(None)):
    """Import terms from an Excel file."""
    user = _resolve_user(x_user_id)
    content = await file.read()
    result = import_export_service.import_excel(content, user["user_id"])
    return result


@router.get("/export/tbx")
def export_tbx(
    status: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    approved_by: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Export terms as TBX XML."""
    terms = import_export_service.get_filtered_terms_for_export(
        status=status,
        domain=domain,
        approved_by=approved_by,
        date_from=date_from,
        date_to=date_to,
    )
    stream = import_export_service.export_tbx(terms)
    return StreamingResponse(iter([stream]), media_type="application/xml")


@router.get("/export/csv")
def export_csv(
    status: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    approved_by: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Export terms as CSV."""
    terms = import_export_service.get_filtered_terms_for_export(
        status=status,
        domain=domain,
        approved_by=approved_by,
        date_from=date_from,
        date_to=date_to,
    )
    stream = import_export_service.export_csv(terms)
    return StreamingResponse(iter([stream]), media_type="text/csv")


@router.get("/export/excel")
def export_excel(
    status: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    approved_by: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Export terms as Excel."""
    terms = import_export_service.get_filtered_terms_for_export(
        status=status,
        domain=domain,
        approved_by=approved_by,
        date_from=date_from,
        date_to=date_to,
    )
    stream = import_export_service.export_excel(terms)
    return StreamingResponse(
        iter([stream]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
