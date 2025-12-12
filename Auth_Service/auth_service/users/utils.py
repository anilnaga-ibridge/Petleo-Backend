

import os
import json
import time
import hashlib
import random
from uuid import uuid4

from django.conf import settings
import redis


# ---------------------------------------------------------
# Redis Connection (fresh connection per request)
# ---------------------------------------------------------
def get_redis():
    """
    Always return a fresh Redis connection using settings.REDIS_URL.
    This prevents stale connections and localhost issues.
    """
    return redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True
    )


# OTP Settings
OTP_TTL_SECONDS = int(getattr(settings, 'OTP_TTL_SECONDS', 600))  # default 10 minutes


# ---------------------------------------------------------
# Redis Keys
# ---------------------------------------------------------
def _redis_key_session(session_id: str) -> str:
    return f"otp:session:{session_id}"


# ---------------------------------------------------------
# OTP Generation
# ---------------------------------------------------------
def generate_numeric_otp(length=6):
    range_start = 10 ** (length - 1)
    range_end = (10 ** length) - 1
    return str(random.SystemRandom().randrange(range_start, range_end))


# ---------------------------------------------------------
# Create OTP Session
# ---------------------------------------------------------
def create_otp_session(phone_number: str, purpose: str = 'login', otp: str = None, ttl: int = None):
    r = get_redis()

    session_id = str(uuid4())
    if otp is None:
        otp = generate_numeric_otp(6)
    if ttl is None:
        ttl = OTP_TTL_SECONDS

    payload = {
        "phone_number": phone_number,
        "purpose": purpose,
        "otp": otp,
        "created_at": int(time.time()),
        "attempts": 0
    }

    r.setex(_redis_key_session(session_id), ttl, json.dumps(payload))
    return session_id, otp


# ---------------------------------------------------------
# Get OTP Session
# ---------------------------------------------------------
def get_otp_session(session_id: str):
    r = get_redis()
    raw = r.get(_redis_key_session(session_id))
    if not raw:
        return None
    return json.loads(raw)


# ---------------------------------------------------------
# Increment OTP Attempts
# ---------------------------------------------------------
def increment_session_attempts(session_id: str):
    r = get_redis()
    key = _redis_key_session(session_id)

    raw = r.get(key)
    if not raw:
        return None

    payload = json.loads(raw)
    payload['attempts'] = payload.get('attempts', 0) + 1

    r.setex(key, OTP_TTL_SECONDS, json.dumps(payload))
    return payload['attempts']


# ---------------------------------------------------------
# Delete OTP Session
# ---------------------------------------------------------
def delete_otp_session(session_id: str):
    r = get_redis()
    r.delete(_redis_key_session(session_id))


# ---------------------------------------------------------
# Phone Rate Limiter
# ---------------------------------------------------------
def increment_rate_limit(phone_number: str, window_seconds: int, limit: int):
    r = get_redis()
    key = f"rate:phone:{phone_number}"

    val = r.incr(key)
    if val == 1:
        r.expire(key, window_seconds)

    return val <= limit


# ---------------------------------------------------------
# SMS Provider
# ---------------------------------------------------------
def send_sms_via_provider(phone_number: str, message: str):
    """
    Returns True if SMS sent/enqueued.

    Dev mode: console print.
    Production: hook to Twilio/SNS etc.
    """
    backend = getattr(settings, 'SMS_BACKEND', 'console')

    if backend == 'console':
        print(f"[SMS to {phone_number}]: {message}")
        return True

    if backend == 'twilio':
        try:
            from twilio.rest import Client
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            msg = client.messages.create(
                body=message,
                from_=settings.TWILIO_FROM_NUMBER,
                to=phone_number
            )
            return True if msg.sid else False
        except Exception as e:
            print("Twilio send error:", e)
            return False

    # fallback
    print("Unknown SMS_BACKEND, printing message:")
    print(message)
    return True


from django.utils import timezone

from django.utils import timezone

def is_pin_valid_today(user):
    today = timezone.localdate()
    tz = timezone.get_current_timezone()

    if user.pin_set_at:
        if user.pin_set_at.astimezone(tz).date() == today:
            return True

    if user.last_pin_login:
        if user.last_pin_login.astimezone(tz).date() == today:
            return True

    return False


import jwt
from django.conf import settings
from datetime import datetime, timedelta

def generate_reset_pin_token(phone_number):
    payload = {
        "phone_number": phone_number,
        "exp": datetime.utcnow() + timedelta(minutes=10),  # valid 10 minutes
        "purpose": "reset_pin"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_reset_pin_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("purpose") != "reset_pin":
            return None
        return payload
    except Exception:
        return None
