import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    
    # Yandex Cloud
    YANDEX_API_KEY = os.getenv('YANDEX_API_KEY', '')
    YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID', '')
    YANDEX_IAM_TOKEN = os.getenv('YANDEX_IAM_TOKEN', '')
    
    # Database
    DB_NAME = os.getenv('DB_NAME', 'travel_bot')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_TOKEN:
            raise ValueError("Missing required environment variable: TELEGRAM_TOKEN")