from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ClothingItem, User
from ..schemas import ClothingCreate, ClothingOut, ImageAnalysisRequest, ImageAnalysisResult
from ..services.image_analysis import dominant_color_from_base64, suggest_clothing_metadata

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ClothingOut])
def list_items(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(ClothingItem)
        .filter(ClothingItem.user_id == current_user.id)
        .order_by(ClothingItem.created_at.desc())
        .all()
    )
    return [_to_schema(item) for item in items]


@router.post("", response_model=ClothingOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: ClothingCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        color_hex, hue, saturation, lightness = dominant_color_from_base64(payload.image_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image data") from exc

    item = ClothingItem(
        user_id=current_user.id,
        name=payload.name,
        category=payload.category,
        occasion=payload.occasion,
        image_base64=payload.image_base64,
        color_hex=color_hex,
        hue=hue,
        saturation=saturation,
        lightness=lightness,
        fit=payload.fit,
        warmth=payload.warmth,
        style_tags=",".join(_normalize_tags(payload.style_tags)),
    )

    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_schema(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = (
        db.query(ClothingItem)
        .filter(ClothingItem.user_id == current_user.id, ClothingItem.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()


@router.post("/analyze", response_model=ImageAnalysisResult)
def analyze_image(payload: ImageAnalysisRequest, current_user: User = Depends(get_current_user)):
    try:
        color_hex, hue, saturation, lightness = dominant_color_from_base64(payload.image_base64)
        category, fit, tags = suggest_clothing_metadata(payload.image_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid image data") from exc

    return ImageAnalysisResult(
        color_hex=color_hex,
        hue=hue,
        saturation=saturation,
        lightness=lightness,
        suggested_category=category,
        suggested_fit=fit,
        suggested_style_tags=tags,
    )


def _normalize_tags(tags: list[str]) -> list[str]:
    result: list[str] = []
    for tag in tags:
        clean = tag.strip().lower()
        if clean and clean not in result:
            result.append(clean)
    return result


def _to_schema(item: ClothingItem) -> ClothingOut:
    tags = [tag.strip() for tag in item.style_tags.split(",") if tag.strip()]
    return ClothingOut(
        id=item.id,
        name=item.name,
        category=item.category,
        occasion=item.occasion,
        image_base64=item.image_base64,
        color_hex=item.color_hex,
        hue=item.hue,
        saturation=item.saturation,
        lightness=item.lightness,
        fit=item.fit,
        warmth=item.warmth,
        style_tags=tags,
        created_at=item.created_at,
    )
