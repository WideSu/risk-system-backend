import os

from dotenv import load_dotenv

load_dotenv(".env.local")

MMR = 0.25
DATABASE_URL = os.getenv("DATABASE_URL")
