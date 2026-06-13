from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.models import ExportFilter
from app.services import import_export_service

router = APIRouter(prefix="/api/import-export", tags=["import-export"])


@router.post("/import/tbx")
async def import_tbx(file: UploadFile):
    """Import terms from a TBX file."""
    content = await file.read()
    result = import_export_service.import_tbx(content)
    return result


@router.post("/import/csv")
async def import_csv(file: UploadFile):
    """Import terms from a CSV file."""
    content = await file.read()
    result = import_export_service.import_csv(content)
    return result


@router.post("/import/excel")
async def import_excel(file: UploadFile):
    """Import terms from an Excel file."""
    content = await file.read()
    result = import_export_service.import_excel(content)
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
    filters = ExportFilter(
        status=status,
        domain=domain,
        approved_by=approved_by,
        date_from=date_from,
        date_to=date_to,
    )
    stream = import_export_service.export_tbx(filters)
    return StreamingResponse(stream, media_type="application/xml")


@router.get("/export/csv")
def export_csv(
    status: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    approved_by: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Export terms as CSV."""
    filters = ExportFilter(
        status=status,
        domain=domain,
        approved_by=approved_by,
        date_from=date_from,
        date_to=date_to,
    )
    stream = import_export_service.export_csv(filters)
    return StreamingResponse(stream, media_type="text/csv")


@router.get("/export/excel")
def export_excel(
    status: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    approved_by: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Export terms as Excel."""
    filters = ExportFilter(
        status=status,
        domain=domain,
        approved_by=approved_by,
        date_from=date_from,
        date_to=date_to,
    )
    stream = import_export_service.export_excel(filters)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
