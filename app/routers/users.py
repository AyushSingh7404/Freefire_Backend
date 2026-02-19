"""
Users router: profile management and avatar upload.

Endpoints:
  GET  /users/me         → current user's full profile
  PUT  /users/me         → update username, age, freeFireId, freeFireName
  POST /users/me/avatar  → upload avatar to Cloudinary
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import ConflictException
from app.models.user import User
from app.schemas.user import UserOut, UserUpdateRequest, AvatarUploadResponse
from app.services.cloudinary_service import (
    upload_avatar,
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_BYTES,
)

router = APIRouter()


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Return the authenticated user's full profile.
    No DB call needed — get_current_user already fetched the user.
    """
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update profile fields. Only provided fields are changed (PATCH-like behaviour
    even though this is a PUT — all fields in the request body are optional).

    Username uniqueness is checked before applying the update.
    """
    if body.username and body.username != current_user.username:
        existing = db.query(User).filter(User.username == body.username).first()
        if existing:
            raise ConflictException("This username is already taken")
        current_user.username = body.username

    if body.age is not None:
        current_user.age = body.age

    if body.free_fire_id is not None:
        current_user.free_fire_id = body.free_fire_id.strip() or None

    if body.free_fire_name is not None:
        current_user.free_fire_name = body.free_fire_name.strip() or None

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload or replace the current user's avatar.

    Validation:
      - Only JPEG, PNG, WebP accepted
      - Max 5 MB
    Cloudinary overwrites the previous avatar using the user ID as public_id,
    so there are never orphaned images.
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file.content_type}' not allowed. Use JPEG, PNG, or WebP.",
        )

    # Read and validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is 5 MB.",
        )

    # Upload to Cloudinary (synchronous SDK call — runs in thread pool via FastAPI)
    avatar_url = upload_avatar(contents, str(current_user.id))

    # Persist the returned CDN URL
    current_user.avatar_url = avatar_url
    db.commit()

    return AvatarUploadResponse(avatar_url=avatar_url)
