"""Tiny reader/writer for backend/.env (keeps passwords out of the code)."""
from pathlib import Path
from django.conf import settings

ENV = Path(settings.BASE_DIR) / ".env"


def read_env():
    d = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip().strip('"')
    return d


def write_env(d):
    lines = ["# Aura ERP settings. Contains passwords - do not share this file."]
    lines += [f"{k}={v}" for k, v in d.items()]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
