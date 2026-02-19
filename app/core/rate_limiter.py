"""
slowapi rate limiter instance.
Import `limiter` into routers and decorate endpoints with @limiter.limit("N/period").

IMPORTANT: Every rate-limited endpoint MUST have `request: Request` as a parameter
(slowapi needs it to extract the client IP). The @limiter.limit decorator must be
placed BELOW the @router.xxx decorator, not above it.

Example:
    @router.post("/send-otp")
    @limiter.limit("3/minute")
    async def send_otp(request: Request, ...):
        ...
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    # Default limit applied to ALL endpoints unless overridden.
    # Individual endpoints can override with their own @limiter.limit() decorator.
    default_limits=["200/minute"],
)
