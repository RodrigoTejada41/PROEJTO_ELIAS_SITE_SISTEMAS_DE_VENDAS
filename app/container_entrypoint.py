"""Read the mounted database secret before invoking a container command."""

import os
from ipaddress import ip_address
from pathlib import Path
import sys

from app import mfa


def main():
    if mfa.required():
        mfa.cipher()
    proxy_ip = os.environ.get("ESTHER_PROXY_IP")
    if proxy_ip is not None:
        address = ip_address(proxy_ip)
        if address.is_unspecified or address.is_multicast:
            raise ValueError("ESTHER_PROXY_IP deve identificar o proxy autorizado.")
        os.environ["FORWARDED_ALLOW_IPS"] = str(address)
    secret = os.environ.get("PGPASSWORD_FILE")
    if secret:
        os.environ["PGPASSWORD"] = Path(secret).read_text(encoding="utf-8").strip()
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
