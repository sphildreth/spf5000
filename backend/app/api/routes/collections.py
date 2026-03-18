from fastapi import APIRouter, Depends, HTTPException

from app.schemas.collection import (
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
)
from app.services.collection_service import CollectionService

router = APIRouter()


def get_collection_service() -> CollectionService:
    return CollectionService()


@router.get("", response_model=list[CollectionResponse])
def list_collections(
    svc: CollectionService = Depends(get_collection_service),
) -> list[CollectionResponse]:
    return [CollectionResponse.from_domain(c) for c in svc.list_collections()]


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: str, svc: CollectionService = Depends(get_collection_service)
) -> CollectionResponse:
    collection = svc.get_collection(collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse.from_domain(collection)


@router.post("", response_model=CollectionResponse, status_code=201)
def create_collection(
    request: CollectionCreateRequest,
    svc: CollectionService = Depends(get_collection_service),
) -> CollectionResponse:
    collection = svc.create_collection(
        name=request.name,
        description=request.description,
        source_id=request.source_id,
        is_active=request.is_active,
    )
    return CollectionResponse.from_domain(collection)


@router.put("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: str,
    request: CollectionUpdateRequest,
    svc: CollectionService = Depends(get_collection_service),
) -> CollectionResponse:
    updated = svc.update_collection(
        collection_id,
        request.name,
        request.description,
        request.source_id,
        request.is_active,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse.from_domain(updated)
