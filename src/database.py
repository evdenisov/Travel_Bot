import redis
import logging
import time
from src.config import Config

class RedisManager:
    def __init__(self):
        self.redis_client = None
        self.max_retries = 3
        self.retry_delay = 2
        self.connect_with_retry()
    
    def connect_with_retry(self):
        """Подключение к Redis с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                # Используем правильное имя хоста 'redis' (как в docker-compose)
                self.redis_client = redis.Redis(
                    host='redis',  # имя сервиса в docker-compose
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                
                # Проверяем подключение
                self.redis_client.ping()
                logging.info("✅ Redis connected successfully")
                return
                
            except redis.ConnectionError as e:
                logging.warning(f"⚠️ Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    logging.info(f"🔄 Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logging.error("❌ All Redis connection attempts failed")
                    self.redis_client = None
            except Exception as e:
                logging.error(f"❌ Unexpected Redis error: {e}")
                self.redis_client = None
                break
    
    def set_user_state(self, user_id, state):
        """Устанавливаем состояние пользователя"""
        if self.redis_client:
            try:
                # Добавляем проверку для state
                if state is None:
                    state = ""
                    
                self.redis_client.set(f"user:{user_id}:state", state, ex=3600)
            except Exception as e:
                logging.error(f"Redis set error: {e}")
    
    def get_user_state(self, user_id):
        """Получаем состояние пользователя"""
        if self.redis_client:
            try:
                return self.redis_client.get(f"user:{user_id}:state")
            except Exception as e:
                logging.error(f"Redis get error: {e}")
        return None
    
    def set_user_data(self, user_id, key, value):
        """Сохраняем данные пользователя"""
        if self.redis_client:
            try:
                # Заменяем None на пустую строку чтобы избежать ошибок Redis
                if value is None:
                    value = ""
                    
                self.redis_client.hset(f"user:{user_id}:data", key, value)
                self.redis_client.expire(f"user:{user_id}:data", 3600)
            except Exception as e:
                logging.error(f"Redis hset error: {e}")
    
    def get_user_data(self, user_id, key):
        """Получаем данные пользователя"""
        if self.redis_client:
            try:
                return self.redis_client.hget(f"user:{user_id}:data", key)
            except Exception as e:
                logging.error(f"Redis hget error: {e}")
        return None
    
    def get_all_user_data(self, user_id):
        """Получаем все данные пользователя"""
        if self.redis_client:
            try:
                return self.redis_client.hgetall(f"user:{user_id}:data")
            except Exception as e:
                logging.error(f"Redis hgetall error: {e}")
        return {}

# Глобальный экземпляр (но не подключаем сразу)
redis_manager = None

def init_redis():
    """Инициализация Redis (вызывается после запуска бота)"""
    global redis_manager
    redis_manager = RedisManager()
    return redis_manager