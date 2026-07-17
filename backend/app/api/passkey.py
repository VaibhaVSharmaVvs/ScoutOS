"""Passwordless auth via WebAuthn passkeys (W3C Web Authentication).

Discoverable credentials (resident keys) → truly usernameless: the browser
stores a device-bound keypair, the server only ever sees the public key. No
email, no password, no fingerprinting — clean for SOC2 / ISO 27001. On a
successful ceremony we mint the same JWT the rest of the API already uses.

Ceremony state (the per-attempt challenge) is held in-process with a short TTL.
Single-worker only; move to Redis for a multi-worker deploy (Phase 8).
"""

from __future__ import annotations

import json
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.config import get_settings
from app.db.models import User, WebAuthnCredential
from app.db.session import get_session
from app.schemas import TokenResponse
from app.security import create_access_token

router = APIRouter(prefix="/auth/passkey", tags=["auth"])

# ceremony_id -> {challenge: bytes, ...}, expires after _TTL seconds
_CEREMONIES: dict[str, dict] = {}
_TTL = 300


def _stash(data: dict) -> str:
    cid = secrets.token_urlsafe(16)
    _CEREMONIES[cid] = {**data, "exp": time.time() + _TTL}
    # opportunistic cleanup of expired entries
    now = time.time()
    for k in [k for k, v in _CEREMONIES.items() if v["exp"] < now]:
        _CEREMONIES.pop(k, None)
    return cid


def _take(cid: str) -> dict | None:
    data = _CEREMONIES.pop(cid, None)
    if data is None or data["exp"] < time.time():
        return None
    return data


class Begin(BaseModel):
    display_name: str | None = None


class Complete(BaseModel):
    ceremony_id: str
    credential: dict


@router.post("/register/begin")
def register_begin(body: Begin) -> dict:
    s = get_settings()
    user_handle = secrets.token_bytes(16)
    display = (body.display_name or "Scout").strip()[:64]
    options = generate_registration_options(
        rp_id=s.webauthn_rp_id,
        rp_name=s.webauthn_rp_name,
        user_id=user_handle,
        user_name=display,
        user_display_name=display,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    cid = _stash({
        "challenge": options.challenge,
        "user_handle": bytes_to_base64url(user_handle),
        "display_name": display,
    })
    return {"ceremony_id": cid, "options": json.loads(options_to_json(options))}


@router.post("/register/complete", response_model=TokenResponse)
def register_complete(body: Complete, db: Session = Depends(get_session)) -> TokenResponse:
    s = get_settings()
    state = _take(body.ceremony_id)
    if state is None:
        raise HTTPException(status_code=400, detail="ceremony expired — try again")
    try:
        verified = verify_registration_response(
            credential=body.credential,
            expected_challenge=state["challenge"],
            expected_rp_id=s.webauthn_rp_id,
            expected_origin=s.webauthn_origin,
        )
    except Exception as exc:  # noqa: BLE001 - surface as a clean 400
        raise HTTPException(status_code=400, detail=f"passkey registration failed: {exc}") from exc

    user = User(user_handle=state["user_handle"], display_name=state["display_name"])
    db.add(user)
    db.flush()
    db.add(WebAuthnCredential(
        user_id=user.id,
        credential_id=bytes_to_base64url(verified.credential_id),
        public_key=bytes_to_base64url(verified.credential_public_key),
        sign_count=verified.sign_count,
    ))
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login/begin")
def login_begin() -> dict:
    s = get_settings()
    options = generate_authentication_options(
        rp_id=s.webauthn_rp_id,
        user_verification=UserVerificationRequirement.PREFERRED,
    )  # no allow_credentials -> discoverable / usernameless
    cid = _stash({"challenge": options.challenge})
    return {"ceremony_id": cid, "options": json.loads(options_to_json(options))}


@router.post("/login/complete", response_model=TokenResponse)
def login_complete(body: Complete, db: Session = Depends(get_session)) -> TokenResponse:
    s = get_settings()
    state = _take(body.ceremony_id)
    if state is None:
        raise HTTPException(status_code=400, detail="ceremony expired — try again")

    cred_id = body.credential.get("id")
    stored = db.scalar(
        select(WebAuthnCredential).where(WebAuthnCredential.credential_id == cred_id)
    )
    if stored is None:
        raise HTTPException(status_code=404, detail="unknown passkey — register first")
    try:
        verified = verify_authentication_response(
            credential=body.credential,
            expected_challenge=state["challenge"],
            expected_rp_id=s.webauthn_rp_id,
            expected_origin=s.webauthn_origin,
            credential_public_key=base64url_to_bytes(stored.public_key),
            credential_current_sign_count=stored.sign_count,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"passkey login failed: {exc}") from exc

    stored.sign_count = verified.new_sign_count
    db.commit()
    return TokenResponse(access_token=create_access_token(str(stored.user_id)))
