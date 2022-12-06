import os
from dotenv import load_dotenv

load_dotenv()
cfg = {
    'token': os.getenv('DISCORD_TOKEN'),
    'prefix': 'tc',
}