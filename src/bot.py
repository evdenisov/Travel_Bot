import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Состояния разговора
DESTINATION, DATES, BUDGET, TRAVELERS, INTERESTS = range(5)

# Глобальные переменные
redis_manager = None
temp_storage = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога - запрос направления"""
    user = update.effective_user
    
    welcome_text = f"""
Привет, {user.first_name}! ✈️

Я - твой AI-помощник для планирования путешествий! 
Использую современные AI-модели для создания персонализированных маршрутов.

Давай спланируем твое идеальное путешествие! 

📍 **Куда бы ты хотел поехать?**
(Например: Санкт-Петербург, Россия или Бали, Индонезия)
    """
    
    await update.message.reply_text(welcome_text)
    
    # Инициализируем сессию пользователя
    user_id = user.id
    if redis_manager and redis_manager.redis_client:
        redis_manager.set_user_state(user_id, DESTINATION)
        redis_manager.set_user_data(user_id, 'conversation_started', 'true')
    else:
        if user_id not in temp_storage:
            temp_storage[user_id] = {}
        temp_storage[user_id]['state'] = DESTINATION
    
    return DESTINATION

async def get_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем направление"""
    user_id = update.effective_user.id
    destination = update.message.text
    
    # Сохраняем данные
    if redis_manager and redis_manager.redis_client:
        redis_manager.set_user_data(user_id, 'destination', destination)
        redis_manager.set_user_state(user_id, DATES)
    else:
        temp_storage[user_id]['destination'] = destination
        temp_storage[user_id]['state'] = DATES
    
    await update.message.reply_text(
        f"Отлично! {destination} - прекрасный выбор! 🌍\n\n"
        "🗓️ **На какие даты планируете поездку?**\n"
        "(Например: 15.08.2024 - 25.08.2024 или 'в августе 2024')"
    )
    
    return DATES

async def get_dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем даты"""
    user_id = update.effective_user.id
    dates = update.message.text
    
    if redis_manager and redis_manager.redis_client:
        redis_manager.set_user_data(user_id, 'dates', dates)
        redis_manager.set_user_state(user_id, BUDGET)
    else:
        temp_storage[user_id]['dates'] = dates
        temp_storage[user_id]['state'] = BUDGET
    
    await update.message.reply_text(
        "Записал даты! 📅\n\n"
        "💰 **Какой бюджет на поездку?**\n"
        "(Например: 50000 рублей, 1000$ или 'средний бюджет')"
    )
    
    return BUDGET

async def get_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем бюджет"""
    user_id = update.effective_user.id
    budget = update.message.text
    
    if redis_manager and redis_manager.redis_client:
        redis_manager.set_user_data(user_id, 'budget', budget)
        redis_manager.set_user_state(user_id, TRAVELERS)
    else:
        temp_storage[user_id]['budget'] = budget
        temp_storage[user_id]['state'] = TRAVELERS
    
    await update.message.reply_text(
        "Понял бюджет! 💵\n\n"
        "👥 **Сколько человек поедет?**\n"
        "(Например: 2 взрослых, семья с 1 ребенком)"
    )
    
    return TRAVELERS

async def get_travelers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем количество путешественников"""
    user_id = update.effective_user.id
    travelers = update.message.text
    
    if redis_manager and redis_manager.redis_client:
        redis_manager.set_user_data(user_id, 'travelers', travelers)
        redis_manager.set_user_state(user_id, INTERESTS)
    else:
        temp_storage[user_id]['travelers'] = travelers
        temp_storage[user_id]['state'] = INTERESTS
    
    await update.message.reply_text(
        "Отлично! 🎯\n\n"
        "**Расскажи о своих интересах:**\n"
        "(Например: пляжный отдых, экскурсии, горные походы, местная кухня, шоппинг, музеи, ночная жизнь)"
    )
    
    return INTERESTS

async def get_interests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем интересы и генерируем несколько планов через OpenRouter"""
    user_id = update.effective_user.id
    interests = update.message.text
    
    # Показываем что начали генерацию
    processing_msg = await update.message.reply_text(
        "🎯 Отлично! Собираю всю информацию...\n"
        "🤖 Обращаюсь к нескольким AI-моделям для создания вариантов маршрута...\n"
        "⏳ Это займет 30-60 секунд..."
    )
    
    # Получаем все данные пользователя
    user_data = {}
    if redis_manager and redis_manager.redis_client:
        user_data = redis_manager.get_all_user_data(user_id)
        # Сбрасываем состояние
        redis_manager.set_user_state(user_id, None)
    else:
        user_data = temp_storage.get(user_id, {})
        # Удаляем состояние из временного хранилища
        if user_id in temp_storage:
            temp_storage[user_id]['state'] = None
    
    # Добавляем интересы
    user_data['interests'] = interests
    
    # Генерируем несколько планов через OpenRouter
    try:
        from src.ai_openrouter import openrouter_ai
        
        # Выполняем запрос в отдельном потоке чтобы не блокировать бота
        travel_plans = await asyncio.get_event_loop().run_in_executor(
            None, openrouter_ai.generate_travel_plans, user_data, 3
        )
        
        # Проверяем что планы сгенерированы
        if not travel_plans or len(travel_plans) == 0:
            await processing_msg.delete()
            await update.message.reply_text(
                "❌ Не удалось сгенерировать планы. Сервис временно недоступен.\n"
                "Попробуйте позже или используйте /start для нового запроса."
            )
            return ConversationHandler.END
        
        # Удаляем сообщение о процессе
        await processing_msg.delete()
        
        # Отправляем заголовок с информацией о сравнении
        await update.message.reply_text(
            f"✨ **Получено {len(travel_plans)} варианта плана от разных AI-моделей!**\n\n"
            "🤖 *Сравните подходы разных моделей и выберите самый подходящий для вас.*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        # Отправляем каждый план с информацией о модели
        for i, plan in enumerate(travel_plans, 1):
            # Заголовок плана
            header = f"**📋 ВАРИАНТ {i} из {len(travel_plans)}**\n"
            header += f"📊 Длина: {plan['length']} символов\n"
            header += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            await update.message.reply_text(header)
            
            # Отправляем содержимое плана частями (уже содержит информацию о модели)
            content = plan['content']
            if len(content) > 4000:
                parts = [content[i:i+4000] for i in range(0, len(content), 4000)]
                for part in parts:
                    await update.message.reply_text(part)
                    await asyncio.sleep(1)
            else:
                await update.message.reply_text(content)
            
            # Разделитель между планами
            if i < len(travel_plans):
                await update.message.reply_text("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                await asyncio.sleep(2)  # Пауза между планами
            
    except ImportError:
        logging.error("OpenRouter service not found")
        await processing_msg.delete()
        await update.message.reply_text(
            "❌ Сервис планирования временно недоступен.\n"
            "Используйте /start для повторной попытки."
        )
    except Exception as e:
        logging.error(f"Error generating travel plans with OpenRouter: {e}")
        await processing_msg.delete()
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации планов. Попробуйте позже или используйте /start для нового запроса."
        )
    
    # Финальное сообщение
    await update.message.reply_text(
        "🎉 **Все планы готовы!**\n\n"
        "💡 *Сравните разные подходы и выберите самый подходящий вариант.*\n\n"
        "Если хотите спланировать еще одно путешествие - отправьте /start\n"
        "Нужна помощь? - /help\n"
        "Проверить статус API - /status"
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога"""
    user = update.effective_user
    user_id = user.id
    
    if redis_manager and redis_manager.redis_client:
        redis_manager.set_user_state(user_id, None)
    else:
        if user_id in temp_storage:
            temp_storage[user_id]['state'] = None
    
    await update.message.reply_text(
        "❌ Диалог прерван.\n"
        "Если захочешь спланировать путешествие - отправь /start"
    )
    
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Помощь"""
    help_text = """
🤖 **Помощь по Travel Bot с AI**

**Команды:**
/start - Начать планирование путешествия
/help - Показать эту справку  
/cancel - Отменить текущий диалог
/status - Проверить статус сервисов

**Как это работает:**
1. Я задам 5 вопросов о вашем путешествии
2. Использую несколько AI-моделей для создания разных вариантов маршрута
3. Вы получите 3 персонализированных плана от разных AI для сравнения

**Вопросы:**
📍 Направление путешествия
🗓️ Даты поездки
💰 Бюджет
👥 Количество путешественников  
🎯 Ваши интересы

**AI создаст для вас:**
📅 Детальные маршруты по дням
🏨 Рекомендации по проживанию
🍽️ Советы по питанию
🚇 Транспортные варианты
💡 Полезные советы и лайфхаки

**Особенность:** Вы получите 3 разных плана от разных AI-моделей для сравнения!

Начните с /start для планирования! ✈️
    """
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка статуса сервисов"""
    try:
        from src.ai_openrouter import openrouter_ai
        openrouter_status = "✅ Доступен"
        models_count = len(openrouter_ai.available_models)
    except ImportError:
        openrouter_status = "❌ Недоступен"
        models_count = 0
    except Exception as e:
        openrouter_status = f"❌ Ошибка: {e}"
        models_count = 0
    
    # Проверяем Redis
    redis_status = "✅ Подключен" if redis_manager and redis_manager.redis_client else "⚠️ Временное хранилище"
    
    status_text = f"""
🔍 **Статус сервисов:**

🤖 OpenRouter AI: {openrouter_status}
📊 Доступно моделей: {models_count}
💾 Хранилище: {redis_status}
👥 Пользователей в памяти: {len(temp_storage)}

💡 **Статистика:**
- Активные диалоги: {sum(1 for data in temp_storage.values() if data.get('state') is not None)}
- Всего пользователей: {len(temp_storage)}

🎲 **При каждом запросе бот случайно выбирает 3 модели из {models_count} доступных**
    """
    
    await update.message.reply_text(status_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")

def main() -> None:
    """Основная функция запуска бота"""
    global redis_manager
    
    logger.info("=" * 50)
    logger.info("🚀 STARTING TRAVEL BOT WITH OPENROUTER...")
    logger.info("=" * 50)
    
    # Проверяем переменные окружения
    token = os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        logger.error("❌ TELEGRAM_TOKEN not found!")
        return
    
    logger.info(f"✅ TELEGRAM_TOKEN: {token[:10]}...")
    
    # Инициализируем Redis
    try:
        from src.database import init_redis
        redis_manager = init_redis()
        
        if redis_manager.redis_client:
            logger.info("✅ Redis connected successfully!")
        else:
            logger.warning("⚠️ Redis not available, using temporary storage")
            
    except Exception as e:
        logger.warning(f"⚠️ Redis initialization failed: {e}")
        logger.info("🔄 Continuing with temporary storage...")
    
    # Инициализируем OpenRouter
    try:
        from src.ai_openrouter import openrouter_ai
        logger.info(f"✅ OpenRouter AI initialized successfully with {len(openrouter_ai.available_models)} models!")
    except Exception as e:
        logger.error(f"❌ OpenRouter initialization failed: {e}")
    
    try:
        # Создаем Application
        application = Application.builder().token(token).build()

        # Создаем ConversationHandler для диалога
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_destination)],
                DATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_dates)],
                BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_budget)],
                TRAVELERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_travelers)],
                INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interests)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )

        # Добавляем обработчики
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("cancel", cancel))
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)

        # Запускаем бота
        logger.info("✅ Bot starting polling with OpenRouter...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()