import requests
import logging
from src.config import Config

class OpenRouterAI:
    def __init__(self):
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/evdenisov/Travel_Bot/",
            "X-Title": "Travel Bot"
        }
        self.model = "anthropic/claude-3.5-sonnet"  # Простая модель по умолчанию
        logging.info("✅ OpenRouter AI configured")
    
    def generate_response(self, prompt):
        """Простой запрос к OpenRouter API"""
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logging.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"OpenRouter API request failed: {e}")
            return None
    
    def generate_travel_plan(self, user_data):
        """Простая генерация плана путешествия"""
        destination = user_data.get('destination', 'неизвестное направление')
        budget = user_data.get('budget', 'не указан')
        
        prompt = f"""
        Создай краткий план путешествия в {destination} с бюджетом {budget}.
        Включи основные достопримечательности и советы по транспорту.
        Ответь на русском языке.
        """
        
        return self.generate_response(prompt)

# Глобальный экземпляр
openrouter_ai = OpenRouterAI()