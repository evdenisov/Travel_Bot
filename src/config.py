import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    
    # OpenRouter AI
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    # Модели OpenRouter (бесплатные варианты)
    DEFAULT_MODEL = "google/gemini-flash-1.5"  # Быстрая и качественная
    FALLBACK_MODEL = "meta-llama/llama-3-8b-instruct"  # Резервная модель
    
    # Настройки генерации
    MAX_TOKENS = 1500
    TEMPERATURE = 0.7
    
    # Database
    DB_NAME = os.getenv('DB_NAME', 'travel_bot')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    
    # Список доступных моделей для переключения
    AVAILABLE_MODELS = {
        "gemini": "google/gemini-flash-1.5",
        "claude": "anthropic/claude-3-haiku", 
        "llama": "meta-llama/llama-3-8b-instruct",
        "wizard": "microsoft/wizardlm-2-8x22b"
    }

    @classmethod
    def validate(cls):
        """Валидация обязательных переменных окружения"""
        missing_vars = []
        
        if not cls.TELEGRAM_TOKEN:
            missing_vars.append("TELEGRAM_TOKEN")
        
        if not cls.OPENROUTER_API_KEY:
            missing_vars.append("OPENROUTER_API_KEY")
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        print("✅ Configuration validated successfully")
        print(f"🤖 Using AI model: {cls.DEFAULT_MODEL}")