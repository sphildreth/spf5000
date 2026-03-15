from fastapi import APIRouter, HTTPException

from app.schemas.imports import ImportJobResponse, LocalImportRunRequest, LocalImportScanRequest, LocalImportScanResponse
from app.services.import_service import ImportService

router = APIRouter()
service = ImportService()


@router.post("/local/scan", response_model=LocalImportScanResponse)
def scan_local_imports(request: LocalImportScanRequest) -> LocalImportScanResponse:
    try:
        job, scan_result = service.scan_local_source(request.source_id, max_samples=request.max_samples)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return LocalImportScanResponse(
        job=ImportJobResponse.from_domain(job),
        import_path=scan_result.import_path,
        discovered_count=scan_result.discovered_count,
        ignored_count=scan_result.ignored_count,
        sample_filenames=[item.filename for item in scan_result.discovered[: request.max_samples]],
    )


@router.post("/local/run", response_model=ImportJobResponse)
def run_local_imports(request: LocalImportRunRequest) -> ImportJobResponse:
    try:
        job = service.import_local_source(
            source_id=request.source_id,
            collection_id=request.collection_id,
            max_samples=request.max_samples,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ImportJobResponse.from_domain(job)
