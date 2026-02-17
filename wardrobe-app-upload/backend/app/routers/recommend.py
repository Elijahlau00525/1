from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ClothingItem, User
from ..schemas import ClothingOut, OutfitResponse, OutfitSlot
from ..services.recommendation import generate_outfit

router = APIRouter(prefix="/recommend", tags=["recommend"])


@router.get("", response_model=OutfitResponse)
def recommend_outfit(
    occasion: str = Query(default="all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = db.query(ClothingItem).filter(ClothingItem.user_id == current_user.id).all()

    result = generate_outfit(items, occasion=occasion)
    if not result:
        raise HTTPException(status_code=400, detail="Not enough items to generate outfit")

    slots = []
    order = ["top", "bottom", "shoes", "outer", "accessory"]
    for key in order:
        if key in result.slots:
            slots.append(OutfitSlot(slot=key, item=_to_schema(result.slots[key])))

    return OutfitResponse(
        occasion=occasion,
        score=result.score,
        reasons=result.reasons,
        slots=slots,
    )


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
