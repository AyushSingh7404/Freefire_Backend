"""
Cloudinary service: avatar upload and management.

Cloudinary automatically:
  - Resizes images to 200×200 with face-aware cropping
  - Converts to WebP for better compression
  - Serves via global CDN
  - Overwrites the previous avatar (same public_id per user)

Setup:
  1. Create free Cloudinary account at cloudinary.com
  2. Go to Dashboard → copy Cloud Name, API Key, API Secret
  3. Add to .env file
"""
import cloudinary
import cloudinary.uploader
from app.config import settings

# Configure Cloudinary once at module level
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,   # always use HTTPS URLs
)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def upload_avatar(file_bytes: bytes, user_id: str) -> str:
    """
    Upload a user's avatar to Cloudinary.

    Args:
        file_bytes: raw file content (read from UploadFile)
        user_id: UUID string — used as Cloudinary public_id so the same
                 user always overwrites their previous avatar (no orphans)

    Returns:
        secure_url (str): HTTPS URL of the uploaded image, stored in user.avatar_url

    Transformations applied:
        - width/height 200×200, crop=fill (fills the frame, no distortion)
        - gravity=face (centers crop on detected face if present)
    """
    result = cloudinary.uploader.upload(
        file_bytes,
        folder="freefire/avatars",
        public_id=f"user_{user_id}",
        overwrite=True,             # replace previous avatar
        invalidate=True,            # bust CDN cache for the old image
        transformation=[
            {
                "width": 200,
                "height": 200,
                "crop": "fill",
                "gravity": "face",
            }
        ],
        resource_type="image",
    )
    return result["secure_url"]
