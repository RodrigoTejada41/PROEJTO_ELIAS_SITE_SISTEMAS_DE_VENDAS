"""TOTP verification and protection of authenticator secrets."""

from base64 import b32encode, b64encode
from hmac import compare_digest, digest
from io import BytesIO
from os import environ
from pathlib import Path
from secrets import token_bytes
from time import time
from urllib.parse import quote, urlencode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import qrcode


def required():
    return environ.get("ESTHER_MFA_REQUIRED") == "1"


def cipher():
    key_file = environ.get("ESTHER_MFA_KEY_FILE")
    if not key_file:
        raise ValueError("Configure ESTHER_MFA_KEY_FILE.")
    key = bytes.fromhex(Path(key_file).read_text(encoding="ascii").strip())
    if len(key) != 32:
        raise ValueError("A chave de verificação em duas etapas deve ter 32 bytes.")
    return AESGCM(key)


def encrypt(secret, user_id):
    nonce = token_bytes(12)
    return nonce + cipher().encrypt(nonce, secret, str(user_id).encode("ascii"))


def decrypt(value, user_id):
    return cipher().decrypt(value[:12], value[12:], str(user_id).encode("ascii"))


def setup_image(secret, username):
    key = b32encode(secret).decode("ascii")
    issuer = "Esther Beauty 777"
    label = f"{quote(issuer, safe='')}:{quote(username, safe='')}"
    uri = f"otpauth://totp/{label}?{urlencode({'secret': key, 'issuer': issuer})}"
    image = BytesIO()
    qrcode.make(uri, box_size=5).save(image, format="PNG")
    return key, "data:image/png;base64," + b64encode(image.getvalue()).decode("ascii")


def code_at(secret, step):
    hashed = digest(secret, step.to_bytes(8, "big"), "sha1")
    offset = hashed[-1] & 15
    number = int.from_bytes(hashed[offset:offset + 4], "big") & 0x7fffffff
    return f"{number % 1_000_000:06d}"


def matching_step(secret, code, last_step=None):
    if len(code) != 6 or not code.isascii() or not code.isdecimal():
        return None
    current = int(time()) // 30
    for step in (current, current - 1, current + 1):
        if (last_step is None or step > last_step) and compare_digest(code_at(secret, step), code):
            return step
    return None
