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
Использую YandexGPT для создания персонализированных маршрутов.

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
    """Получаем интересы и генерируем план через YandexGPT"""
    user_id = update.effective_user.id
    interests = update.message.text
    
    # Показываем что начали генерацию
    processing_msg = await update.message.reply_text(
        "🎯 Отлично! Собираю всю информацию...\n"
        "🤖 Обращаюсь к YandexGPT для создания идеального маршрута...\n"
        "⏳ Это займет 15-30 секунд..."
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
    
    # Генерируем план через YandexGPT
    try:
        from src.ai_yandexgpt import yandex_gpt
        travel_plan = await asyncio.get_event_loop().run_in_executor(
            None, yandex_gpt.generate_travel_plan, user_data
        )
        
        # Удаляем сообщение о процессе
        await processing_msg.delete()
        
        # Отправляем план частями (лимит Telegram 4096 символов)
        if len(travel_plan) > 4000:
            parts = [travel_plan[i:i+4000] for i in range(0, len(travel_plan), 4000)]
            for i, part in enumerate(parts):
                await update.message.reply_text(part)
                await asyncio.sleep(1)
        else:
            await update.message.reply_text(travel_plan)
            
    except Exception as e:
        logging.error(f"Error generating travel plan: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации плана. Попробуйте позже или используйте /start для нового запроса."
        )
    
    # Финальное сообщение
    await update.message.reply_text(
        "✨ **План готов!**\n\n"
        "Если хочешь спланировать еще одно путешествие - отправь /start\n"
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
🤖 **Помощь по Travel Bot с YandexGPT**

**Команды:**
/start - Начать планирование путешествия
/help - Показать эту справку  
/cancel - Отменить текущий диалог
/status - Проверить статус сервисов

**Как это работает:**
1. Я задам 5 вопросов о вашем путешествии
2. Использую YandexGPT для создания детального маршрута
3. Вы получите персонализированный план с рекомендациями

**Вопросы:**
📍 Направление путешествия
🗓️ Даты поездки
💰 Бюджет
👥 Количество путешественников  
🎯 Ваши интересы

**YandexGPT создаст для вас:**
📅 Детальный маршрут по дням
🏨 Рекомендации по проживанию
🍽️ Советы по питанию
🚇 Транспортные варианты
💡 Полезные советы и лайфхаки

Начните с /start для планирования! ✈️
    """
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка статуса сервисов"""
    from src.ai_yandexgpt import yandex_gpt
    
    # Проверяем статус YandexGPT
    yandex_status = "✅ Доступен" if yandex_gpt else "❌ Недоступен"
    
    # Проверяем Redis
    redis_status = "✅ Подключен" if redis_manager and redis_manager.redis_client else "⚠️ Временное хранилище"
    
    status_text = f"""
🔍 **Статус сервисов:**

🤖 YandexGPT: {yandex_status}
💾 Хранилище: {redis_status}
📊 Пользователей в памяти: {len(temp_storage)}

💡 **Статистика:**
- Активные диалоги: {sum(1 for data in temp_storage.values() if data.get('state') is not None)}
- Всего пользователей: {len(temp_storage)}
    """
    
    await update.message.reply_text(status_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")

def main() -> None:
    """Основная функция запуска бота"""
    global redis_manager
    
    logger.info("=" * 50)
    logger.info("🚀 STARTING TRAVEL BOT WITH YANDEXGPT...")
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
    
    # Инициализируем YandexGPT
    try:
        from src.ai_yandexgpt import yandex_gpt
        logger.info("✅ YandexGPT initialized successfully!")
    except Exception as e:
        logger.error(f"❌ YandexGPT initialization failed: {e}")
    
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
        logger.info("✅ Bot starting polling with YandexGPT...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()