import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
BOT_USERNAME = "sos_suiHelp_bot"
ADMIN_ID = int(os.getenv("ADMIN_ID", "8858971713"))
