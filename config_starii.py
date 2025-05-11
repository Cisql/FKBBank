# Конфигурация проекта

# Настройки бота
BOT_TOKEN = "7540787661:AAGPhlB-YxyJI5EcvQPKT07Geug6hF3O9yE"  # Замени на реальный токен бота

# Настройки приложения
APP_HOST = "0.0.0.0"
APP_PORT = 8000
WEBAPP_URL = "https://n.lknbank.live/app"  # Локальный URL для разработки

# Настройки базы данных
DB_PATH = "lknbank.db"

# Настройки промокодов
DEFAULT_PROMO_LENGTH = 8

# Настройки безопасности
DEFAULT_WELCOME_BONUS = 100  # Бонус при первой регистрации

# Игра "Угадай число"
GUESS_GAME_MAX_ATTEMPTS = 3  # Максимальное количество попыток в игре "Угадай число" в день
GUESS_GAME_REWARD = 500  # Награда за правильный ответ
GUESS_GAME_PENALTY = 100  # Штраф за неправильный ответ

# Игра "Кубик"
DICE_GAME_MAX_ATTEMPTS = 1  # Максимальное количество попыток в игре "Кубик" в день
DICE_GAME_MIN_REWARD = 250  # Минимальная награда за бросок кубика
DICE_GAME_MAX_REWARD = 2500  # Максимальная награда за бросок кубика 
