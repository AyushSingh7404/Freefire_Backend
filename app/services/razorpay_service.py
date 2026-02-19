"""
Razorpay payment service.

Flow:
  1. Frontend calls POST /wallet/payment/initiate → backend creates Razorpay order
  2. Backend returns {order_id, amount, key_id} to frontend
  3. Frontend opens Razorpay JS checkout modal — user pays
  4. Razorpay returns {payment_id, order_id, signature} to frontend
  5. Frontend POSTs all three to POST /wallet/payment/verify
  6. Backend verifies HMAC-SHA256 signature (CRITICAL security step)
  7. If valid, backend credits coins to wallet

WITHOUT step 6, anyone could fake a successful payment by sending any strings.
The signature is an HMAC of "{order_id}|{payment_id}" using your Razorpay secret.
"""
import hmac
import hashlib
import razorpay
from app.config import settings

# Initialize Razorpay client once at module level
client = razorpay.Client(
    auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
)


def create_order(amount_inr: float, coins: int) -> dict:
    """
    Create a Razorpay order.

    Args:
        amount_inr: amount in INR rupees (e.g., 100.0 for ₹100)
        coins: how many coins this purchase is for (stored in receipt for reference)

    Returns:
        Razorpay order dict containing 'id', 'amount', 'currency', etc.

    Note: Razorpay amounts are in PAISE (1 rupee = 100 paise).
    """
    data = {
        "amount": int(amount_inr * 100),   # convert to paise
        "currency": "INR",
        "receipt": f"coins_{coins}_order",
        "payment_capture": 1,               # auto-capture payment on success
    }
    return client.order.create(data=data)


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """
    Verify Razorpay payment signature using HMAC-SHA256.

    The signature is computed as:
        HMAC-SHA256(key=razorpay_secret, msg="{order_id}|{payment_id}")

    Returns True if valid, False if tampered or invalid.
    Uses hmac.compare_digest for timing-safe comparison (prevents timing attacks).
    """
    message = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected_signature = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, razorpay_signature)
