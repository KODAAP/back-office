# config/env.py
from pathlib import Path

# TODO change this to .env.prod in production env
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
CUR_ENV_FILE = BASE_DIR / ".envs" / ".env.local"
