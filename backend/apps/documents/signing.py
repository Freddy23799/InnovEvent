from django.core import signing


def sign_payload(kind: str, value) -> str:
    return signing.dumps({"kind": kind, "value": str(value)}, salt=f"innovevent.{kind}")


def verify_payload(token: str, kind: str, max_age=None):
    try:
        payload = signing.loads(token, salt=f"innovevent.{kind}", max_age=max_age)
    except signing.BadSignature:
        return None
    return payload.get("value")
