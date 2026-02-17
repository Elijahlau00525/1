from __future__ import annotations

import json
from urllib.parse import parse_qs, urlencode
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import TokenResponse, UserCreate, UserLogin, UserOut
from ..security import (
    create_access_token,
    create_oauth_state,
    decode_oauth_state,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/providers/status")
def providers_status():
    return {
        "wechat": {
            "configured": bool(settings.wechat_app_id and settings.wechat_app_secret),
            "display_name": "微信",
            "login_flow": "website_qr",
            "callback_url": settings.wechat_redirect_uri,
            "required_env": ["WECHAT_APP_ID", "WECHAT_APP_SECRET", "WECHAT_REDIRECT_URI"],
            "doc_url": "https://open.weixin.qq.com/",
        },
        "qq": {
            "configured": bool(settings.qq_app_id and settings.qq_app_secret),
            "display_name": "QQ",
            "login_flow": "website_oauth2",
            "callback_url": settings.qq_redirect_uri,
            "required_env": ["QQ_APP_ID", "QQ_APP_SECRET", "QQ_REDIRECT_URI"],
            "doc_url": "https://connect.qq.com/",
        },
    }


@router.get("/{provider}/login")
def oauth_login(provider: str, front_redirect: str | None = Query(default=None)):
    provider = provider.lower().strip()
    if provider not in {"wechat", "qq"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported provider")
    safe_front_redirect = _validate_front_redirect(front_redirect)

    if provider == "wechat":
        if not settings.wechat_app_id or not settings.wechat_app_secret:
            raise HTTPException(status_code=400, detail="WeChat OAuth is not configured")

        state = create_oauth_state("wechat", extra={"front_redirect": safe_front_redirect} if safe_front_redirect else None)
        query = urlencode(
            {
                "appid": settings.wechat_app_id,
                "redirect_uri": settings.wechat_redirect_uri,
                "response_type": "code",
                "scope": "snsapi_login",
                "state": state,
            }
        )
        return {"provider": "wechat", "authorization_url": f"https://open.weixin.qq.com/connect/qrconnect?{query}#wechat_redirect"}

    if not settings.qq_app_id or not settings.qq_app_secret:
        raise HTTPException(status_code=400, detail="QQ OAuth is not configured")

    state = create_oauth_state("qq", extra={"front_redirect": safe_front_redirect} if safe_front_redirect else None)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": settings.qq_app_id,
            "redirect_uri": settings.qq_redirect_uri,
            "scope": "get_user_info",
            "state": state,
        }
    )
    return {"provider": "qq", "authorization_url": f"https://graph.qq.com/oauth2.0/authorize?{query}"}


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    provider = provider.lower().strip()
    if provider not in {"wechat", "qq"}:
        raise HTTPException(status_code=404, detail="Unsupported provider")

    try:
        state_payload = decode_oauth_state(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid oauth state")

    if state_payload.get("provider") != provider:
        raise HTTPException(status_code=400, detail="Mismatched oauth provider")

    if provider == "wechat":
        profile = await _fetch_wechat_profile(code)
    else:
        profile = await _fetch_qq_profile(code)

    if not profile["openid"]:
        raise HTTPException(status_code=400, detail="Unable to resolve openid from provider")

    user = (
        db.query(User)
        .filter(User.provider == provider, User.provider_openid == profile["openid"])
        .first()
    )

    if not user:
        user = User(
            username=_build_unique_username(db, provider, profile["nickname"]),
            password_hash=None,
            provider=provider,
            provider_openid=profile["openid"],
            avatar_url=profile.get("avatar_url"),
        )
        db.add(user)
    else:
        if profile.get("avatar_url"):
            user.avatar_url = profile["avatar_url"]

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="OAuth account conflict")

    db.refresh(user)

    token_payload = {
        "access_token": create_access_token(str(user.id)),
        "token_type": "bearer",
        "user": UserOut.model_validate(user),
    }
    front_redirect = state_payload.get("front_redirect")
    if isinstance(front_redirect, str) and front_redirect.startswith("http"):
        query = urlencode(
            {
                "token": token_payload["access_token"],
                "provider": provider,
                "username": user.username,
            }
        )
        return RedirectResponse(url=f"{front_redirect}?{query}")

    return token_payload


async def _fetch_wechat_profile(code: str) -> dict:
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise HTTPException(status_code=400, detail="WeChat OAuth is not configured")

    async with httpx.AsyncClient(timeout=12) as client:
        token_resp = await client.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": settings.wechat_app_id,
                "secret": settings.wechat_app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()

        if "errcode" in token_data:
            raise HTTPException(status_code=400, detail=f"WeChat token error: {token_data.get('errmsg', 'unknown')}")

        access_token = token_data.get("access_token")
        openid = token_data.get("openid")

        if not access_token or not openid:
            raise HTTPException(status_code=400, detail="WeChat token exchange returned incomplete data")

        profile_resp = await client.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={"access_token": access_token, "openid": openid, "lang": "zh_CN"},
        )
        profile_data = profile_resp.json()

        return {
            "openid": openid,
            "nickname": profile_data.get("nickname") or f"wx_{openid[:8]}",
            "avatar_url": profile_data.get("headimgurl"),
        }


async def _fetch_qq_profile(code: str) -> dict:
    if not settings.qq_app_id or not settings.qq_app_secret:
        raise HTTPException(status_code=400, detail="QQ OAuth is not configured")

    async with httpx.AsyncClient(timeout=12) as client:
        token_resp = await client.get(
            "https://graph.qq.com/oauth2.0/token",
            params={
                "grant_type": "authorization_code",
                "client_id": settings.qq_app_id,
                "client_secret": settings.qq_app_secret,
                "code": code,
                "redirect_uri": settings.qq_redirect_uri,
            },
        )

        token_text = token_resp.text
        parsed = parse_qs(token_text)
        access_token = parsed.get("access_token", [None])[0]

        if not access_token:
            raise HTTPException(status_code=400, detail="QQ token exchange failed")

        me_resp = await client.get("https://graph.qq.com/oauth2.0/me", params={"access_token": access_token})
        me_text = me_resp.text.strip()

        openid = None
        if me_text.startswith("callback"):
            try:
                json_part = me_text[me_text.index("(") + 1 : me_text.rindex(")")]
                openid = json.loads(json_part).get("openid")
            except Exception:
                openid = None

        if not openid:
            raise HTTPException(status_code=400, detail="QQ openid fetch failed")

        profile_resp = await client.get(
            "https://graph.qq.com/user/get_user_info",
            params={
                "access_token": access_token,
                "oauth_consumer_key": settings.qq_app_id,
                "openid": openid,
            },
        )
        profile_data = profile_resp.json()

        return {
            "openid": openid,
            "nickname": profile_data.get("nickname") or f"qq_{openid[:8]}",
            "avatar_url": profile_data.get("figureurl_qq_2") or profile_data.get("figureurl_qq_1"),
        }


def _build_unique_username(db: Session, provider: str, nickname: str | None) -> str:
    base = (nickname or provider).strip().replace(" ", "_")
    if not base:
        base = provider
    base = base[:32]

    for idx in range(1, 9999):
        candidate = f"{provider}_{base}_{idx}" if idx > 1 else f"{provider}_{base}"
        exists = db.query(User).filter(User.username == candidate).first()
        if not exists:
            return candidate

    return f"{provider}_user"


def _validate_front_redirect(front_redirect: str | None) -> str | None:
    if not front_redirect:
        return None

    parsed = urlparse(front_redirect)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid front_redirect")

    allowed = set(settings.cors_origin_list)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if allowed and origin not in allowed:
        raise HTTPException(status_code=400, detail="front_redirect origin is not allowed")

    return front_redirect
