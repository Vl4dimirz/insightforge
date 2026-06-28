"""
Report endpoints — download a profile as Excel or PDF.

  • POST /report/excel → .xlsx (summary + column profile)
  • POST /report/pdf   → .pdf (profile + optional AI analysis)
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response

from app.data import load_dataframe, clean, profile, DataError
from app.insights import analyze_profile
from app.ai import AIError
from app.reports import build_excel, build_pdf

router = APIRouter(prefix="/report", tags=["Report"])

MAX_BYTES = 10 * 1024 * 1024
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _profile_from_upload(file: UploadFile) -> tuple[str, dict]:
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
    try:
        df = clean(load_dataframe(file.filename, content))
    except DataError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if df.empty:
        raise HTTPException(status_code=400, detail="No usable rows to report on.")
    return file.filename, profile(df)


@router.post("/excel")
async def report_excel(file: UploadFile = File(...)) -> Response:
    source, prof = await _profile_from_upload(file)
    data = build_excel(source, prof)
    return Response(
        content=data,
        media_type=XLSX,
        headers={"Content-Disposition": 'attachment; filename="insightforge-report.xlsx"'},
    )


@router.post("/pdf")
async def report_pdf(
    file: UploadFile = File(...),
    include_ai: bool = Form(False),
) -> Response:
    source, prof = await _profile_from_upload(file)
    insights = None
    if include_ai:
        try:
            insights = analyze_profile(prof)
        except AIError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
    data = build_pdf(source, prof, insights)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="insightforge-report.pdf"'},
    )
