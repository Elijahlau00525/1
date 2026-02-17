from datetime import datetime

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    provider: str | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class ClothingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str
    occasion: str
    image_base64: str
    fit: str = "regular"
    warmth: int = Field(default=2, ge=1, le=5)
    style_tags: list[str] = Field(default_factory=list)


class ClothingOut(BaseModel):
    id: int
    name: str
    category: str
    occasion: str
    image_base64: str
    color_hex: str
    hue: float
    saturation: float
    lightness: float
    fit: str
    warmth: int
    style_tags: list[str]
    created_at: datetime


class ImageAnalysisRequest(BaseModel):
    image_base64: str


class ImageAnalysisResult(BaseModel):
    color_hex: str
    hue: float
    saturation: float
    lightness: float
    suggested_category: str
    suggested_fit: str
    suggested_style_tags: list[str]


class OutfitSlot(BaseModel):
    slot: str
    item: ClothingOut


class OutfitResponse(BaseModel):
    occasion: str
    score: float
    reasons: list[str]
    slots: list[OutfitSlot]
