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
        self.model = "anthropic/claude-3.5-sonnet"
        logging.info("✅ OpenRouter AI configured")
    
    def generate_travel_plan(self, user_data):
        """Генерация плана путешествия на основе данных от пользователя"""
        # Извлекаем данные из user_data (как в вашем боте)
        destination = user_data.get('destination', 'неизвестное направление')
        dates = user_data.get('dates', 'не указаны')
        budget = user_data.get('budget', 'не указан')
        travelers = user_data.get('travelers', 'не указано')
        interests = user_data.get('interests', 'не указаны')
        
        # Строим промпт на основе данных от бота
        prompt = self._build_travel_prompt(destination, dates, budget, travelers, interests)
        
        # Отправляем запрос к OpenRouter
        return self._make_api_request(prompt)
    
    def _build_travel_prompt(self, destination, dates, budget, travelers, interests):
        """Строим промпт для генерации плана путешествия"""
        return f"""
Создай детальный план путешествия на основе следующих данных:

📍 **Направление:** {destination}
🗓️ **Даты:** {dates}
💰 **Бюджет:** {budget}
👥 **Путешественники:** {travelers}
🎯 **Интересы:** {interests}

**Требования к ответу:**
1. Создай структурированный план с разделами
2. Укажи практические рекомендации
3. Предложи варианты проживания, питания и транспорта
4. Учитывай бюджет {budget}
5. Учти интересы: {interests}
6. Ответ должен быть полезным и конкретным
7. Используй смайлики для наглядности
8. Пиши на русском языке

**Структура ответа:**
🌍 Обзор путешествия в {destination}
📅 Маршрут по дням
🏨 Проживание
🍽️ Питание  
🚇 Транспорт
💡 Советы и рекомендации
💰 Бюджетные расчеты

Сделай ответ максимально полезным для путешественников!
"""
    
    def _make_api_request(self, prompt):
        """Отправка запроса к OpenRouter API"""
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты - опытный турагент и гид с многолетним опытом. Создаешь детальные, практичные и персонализированные планы путешествий. Отвечаешь на русском языке."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.7
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
                return self._get_fallback_response()
                
        except Exception as e:
            logging.error(f"OpenRouter API request failed: {e}")
            return self._get_fallback_response()
    
    def _get_fallback_response(self):
        """Запасной ответ если API недоступно"""
        return """
🌍 К сожалению, сервис AI-рекомендаций временно недоступен.

Но вот общие рекомендации для планирования путешествия:

📅 **Планирование маршрута:**
• Изучите достопримечательности заранее
• Составьте примерное расписание по дням
• Оставьте время для отдыха и непредвиденных обстоятельств

🏨 **Проживание:**
• Бронируйте отели через проверенные сайты
• Читайте отзывы предыдущих гостей
• Учитывайте расположение относительно центра

🚇 **Транспорт:**
• Изучите варианты общественного транспорта
• Узнайте о местных такси и их стоимости
• Рассмотрите аренду авто если нужно

💡 **Советы:**
• Имейте при себе копии документов
• Узнайте о местных обычаях и правилах
• Сохраните контакты экстренных служб

Для получения персонализированного плана попробуйте позже!
"""

# Глобальный экземпляр
openrouter_ai = OpenRouterAI()