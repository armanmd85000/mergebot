# config.py

import os

class Config:
    # VJ-Forward-Bot core configs
    API_ID = int(os.environ.get("API_ID", "25570420"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    BOT_SESSION = os.environ.get("BOT_SESSION", "vjbot")
    DATABASE_URI = os.environ.get("DATABASE_URI", "")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "vj-forward-bot")
    BOT_OWNER = int(os.environ.get("BOT_OWNER", "7552584508"))

# If you want to support loading direct gita1 variables/envs independently, you could do:
GITA1_EXTRA = {
    "MAX_MESSAGES_PER_BATCH": int(os.environ.get("GITA1_MAX_MESSAGES_PER_BATCH", "100000")),
    "PHOTO_FORWARD_MODE": bool(os.environ.get("GITA1_PHOTO_FORWARD_MODE", False))
}
