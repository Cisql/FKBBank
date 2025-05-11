# Конфигурация проекта

# Настройки бота
BOT_TOKEN = "8137595032:AAGvlaQJm1k__RHfoIz5he365xZ6EdaHHXE"  # Замени на реальный токен бота

# Учетные данные для доступа к админке
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "lknbank2024secure"  # В реальном приложении используйте более безопасный подход

TOKENS_FILE_JSON = "users_tokens.json"
CODES_FILE = "users_code.json"
LAST_TX_ID_FILE = "last_tx.json"

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
