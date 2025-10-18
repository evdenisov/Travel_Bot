import requests
import logging
import asyncio
import random
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
        # Расширенный список бесплатных моделей
        self.available_models = [
            "meta-llama/llama-3.3-70b-instruct:free",      # Llama 3.3 70B - мощная
            "google/gemini-2.0-flash-exp:free",            # Gemini 2.0 Flash - быстрая
            "qwen/qwen2.5-72b-instruct:free",              # Qwen 2.5 72B - китайская модель
            "mistralai/mistral-nemo:free",                 # Mistral Nemo - от Mistral и NVIDIA
            "deepseek/deepseek-r1-distill-llama-70b:free", # DeepSeek R1 Distill
            "microsoft/wizardlm-2-8x22b:free",             # WizardLM 2
            "anthropic/claude-3.5-sonnet:free",            # Claude 3.5 Sonnet
            "openai/gpt-4o-mini:free",                     # GPT-4o Mini
            "meta-llama/llama-3.1-8b-instruct:free",       # Llama 3.1 8B - легкая
            "google/gemma-2-9b-it:free",                   # Gemma 2 9B
            "mistralai/mistral-7b-instruct:free",          # Mistral 7B
            "qwen/qwen2.5-coder-32b-instruct:free",        # Qwen Coder 32B
        ]
        logging.info(f"✅ OpenRouter AI configured with {len(self.available_models)} free models")
    
    def generate_travel_plans(self, user_data, num_plans=3):
        """Генерация нескольких планов путешествия от разных моделей"""
        if not Config.OPENROUTER_API_KEY:
            logging.error("❌ OpenRouter API key not configured")
            return [self._get_fallback_response(user_data, "Система (запасной вариант)")]
        
        destination = user_data.get('destination', 'неизвестное направление')
        dates = user_data.get('dates', 'не указаны')
        budget = user_data.get('budget', 'не указан')
        travelers = user_data.get('travelers', 'не указано')
        interests = user_data.get('interests', 'не указаны')
        
        prompt = self._build_travel_prompt(destination, dates, budget, travelers, interests)
        
        # Перемешиваем модели для случайного порядка
        shuffled_models = self.available_models.copy()
        random.shuffle(shuffled_models)
        logging.info(f"🎲 Models shuffled. First 3: {shuffled_models[:3]}")
        
        successful_plans = []
        used_models = []
        
        # Пробуем модели в случайном порядке пока не получим нужное количество планов
        for model in shuffled_models:
            if len(successful_plans) >= num_plans:
                break
                
            if model in used_models:
                continue
                
            logging.info(f"🔄 Trying model: {self._get_model_display_name(model)}")
            result = self._make_api_request(prompt, model)
            
            if result:
                # Добавляем информацию о модели в начало ответа
                model_display_name = self._get_model_display_name(model)
                content_with_model = self._add_model_info(result, model_display_name)
                
                successful_plans.append({
                    'model': model,
                    'model_display_name': model_display_name,
                    'content': content_with_model,
                    'length': len(content_with_model)
                })
                used_models.append(model)
                logging.info(f"✅ Added plan from {model_display_name}, length: {len(content_with_model)}")
            else:
                logging.warning(f"❌ Model failed: {self._get_model_display_name(model)}")
        
        # Если не получили достаточно планов, добавляем запасные
        while len(successful_plans) < num_plans:
            fallback_num = len(successful_plans) + 1
            fallback_plan = self._get_fallback_response(user_data, f"Система (вариант {fallback_num})")
            successful_plans.append({
                'model': f'fallback_{fallback_num}',
                'model_display_name': f"Система (вариант {fallback_num})",
                'content': fallback_plan,
                'length': len(fallback_plan)
            })
        
        return successful_plans
    
    def _get_model_display_name(self, model):
        """Получаем красивое имя модели для отображения"""
        model_names = {
            "meta-llama/llama-3.3-70b-instruct:free": "Meta Llama 3.3 70B",
            "google/gemini-2.0-flash-exp:free": "Google Gemini 2.0 Flash",
            "qwen/qwen2.5-72b-instruct:free": "Qwen 2.5 72B",
            "mistralai/mistral-nemo:free": "Mistral Nemo",
            "deepseek/deepseek-r1-distill-llama-70b:free": "DeepSeek R1 Distill",
            "microsoft/wizardlm-2-8x22b:free": "Microsoft WizardLM 2",
            "anthropic/claude-3.5-sonnet:free": "Anthropic Claude 3.5 Sonnet",
            "openai/gpt-4o-mini:free": "OpenAI GPT-4o Mini",
            "meta-llama/llama-3.1-8b-instruct:free": "Meta Llama 3.1 8B",
            "google/gemma-2-9b-it:free": "Google Gemma 2 9B",
            "mistralai/mistral-7b-instruct:free": "Mistral 7B",
            "qwen/qwen2.5-coder-32b-instruct:free": "Qwen Coder 32B",
        }
        return model_names.get(model, model.split('/')[-1].replace(':free', ''))
    
    def _add_model_info(self, content, model_name):
        """Добавляем информацию о модели в ответ"""
        model_header = f"🤖 **Создано моделью: {model_name}**\n\n"
        return model_header + content
    
    def _build_travel_prompt(self, destination, dates, budget, travelers, interests):
        return f"""
Ты - опытный турагент с 15-летним опытом. Создай максимально детальный и практичный план путешествия.

ДАННЫЕ КЛИЕНТА:
📍 Направление: {destination}
🗓️ Даты: {dates}
💰 Бюджет: {budget}
👥 Путешественники: {travelers}
🎯 Интересы: {interests}

ТРЕБОВАНИЯ К ОТВЕТУ:
1. Будь КОНКРЕТНЫМ - называй реальные типы мест и активностей
2. Указывай примерные цены в рублях
3. Создай детальное расписание по дням и часам
4. Учитывай логистику и транспорт
5. Предлагай альтернативные варианты
6. Структурируй информацию четко по разделам
7. Используй смайлики для наглядности
8. Отвечай на русском языке
9. Будь оригинальным в рекомендациях

ОБЯЗАТЕЛЬНАЯ СТРУКТУРА ОТВЕТА:

🌍 ДЕТАЛЬНЫЙ ПЛАН ПУТЕШЕСТВИЯ В {destination}

📅 ПОДРОБНЫЙ МАРШРУТ ПО ДНЯМ И ЧАСАМ:

[Для каждого дня создай расписание по времени с конкретными активностями]

🏨 РЕКОМЕНДАЦИИ ПО ПРОЖИВАНИЮ:

🍽️ ГАСТРОНОМИЧЕСКИЕ РЕКОМЕНДАЦИИ:

🚇 ТРАНСПОРТ И ЛОГИСТИКА:

💡 ПРАКТИЧЕСКИЕ СОВЕТЫ:

💰 РАСЧЕТ БЮДЖЕТА:

Создай уникальный и полезный план, который полностью заменит услуги турагента!
"""
    
    def _make_api_request(self, prompt, model):
        """Отправка запроса к OpenRouter API с указанной моделью"""
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": "Ты опытный турагент и гид с многолетним опытом. Создаешь детальные, практичные и персонализированные планы путешествий. Ты должен предоставлять конкретную информацию: примерные цены, детальные маршруты, практические советы. Используй смайлики для наглядности и структурируй информацию для легкого чтения. Отвечай на русском языке. Будь оригинальным в своих рекомендациях."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1800,
            "temperature": 0.8  # Увеличим температуру для разнообразия
        }
        
        try:
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json=data, 
                timeout=25
            )
            
            model_display = self._get_model_display_name(model)
            logging.info(f"📡 Model {model_display} - Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    logging.info(f"✅ Response received from {model_display}, length: {len(content)}")
                    return content
                else:
                    logging.error(f"❌ No choices in response from {model_display}")
                    return None
            else:
                error_text = response.text[:200] if response.text else "No error details"
                logging.error(f"❌ API Error {response.status_code} from {model_display}: {error_text}")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"❌ Timeout with model: {self._get_model_display_name(model)}")
            return None
        except requests.exceptions.ConnectionError:
            logging.error(f"❌ Connection error with model: {self._get_model_display_name(model)}")
            return None
        except Exception as e:
            logging.error(f"❌ Unexpected error with model {self._get_model_display_name(model)}: {e}")
            return None
    
    def _get_fallback_response(self, user_data, model_name):
        """Качественный запасной ответ с указанием модели"""
        destination = user_data.get('destination', 'выбранное направление')
        budget = user_data.get('budget', 'не указан')
        travelers = user_data.get('travelers', 'не указано')
        interests = user_data.get('interests', 'не указаны')
        
        return f"""🤖 **Создано моделью: {model_name}**

🌍 **АЛЬТЕРНАТИВНЫЙ ПЛАН ПУТЕШЕСТВИЯ В {destination}**

💰 **Бюджет:** {budget}
👥 **Путешественники:** {travelers}
🎯 **Интересы:** {interests}

📅 **УНИВЕРСАЛЬНЫЙ МАРШРУТ НА 5 ДНЕЙ:**

**День 1: Прибытие и адаптация 🛬**
⏰ 10:00-12:00 - Перелет/переезд в {destination}
⏰ 12:30-13:30 - Трансфер до отеля в центре города
⏰ 14:00-15:00 - Заселение в отель
⏰ 15:30-17:00 - Обед в местном кафе
⏰ 17:30-19:30 - Пешая прогулка по историческому центру
⏰ 20:00-21:30 - Ужин в ресторане национальной кухни

**День 2: Основные достопримечательности 🏛️**
⏰ 09:00-10:00 - Завтрак
⏰ 10:30-13:30 - Экскурсия по главным достопримечательностям
⏰ 14:00-15:00 - Обед с местными специалитетами
⏰ 15:30-18:00 - Посещение музеев и культурных объектов
⏰ 19:00-21:00 - Свободное время и ужин

**День 3: {interests.split(',')[0] if interests else 'Культурная программа'} 🎨**
⏰ 09:30-12:00 - Тематические активности по интересам
⏰ 12:30-14:00 - Обед в аутентичном заведении
⏰ 14:30-17:30 - Прогулка по паркам и набережным
⏰ 18:30-20:30 - Вечерняя развлекательная программа

🏨 **Проживание:** Отели 3-4* в центре города
🍽️ **Питание:** ~2000-3000 рублей в день на человека
🚇 **Транспорт:** Общественный транспорт + такси

💡 *Этот план создан автоматически. AI-модели обычно предлагают более детальные и персонализированные рекомендации.*
"""

# Глобальный экземпляр
openrouter_ai = OpenRouterAI()