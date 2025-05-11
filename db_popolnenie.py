import sqlite3

DB_PATH = "lknbank.db"


def check_table_structure():
    try:
        # Подключение к базе данных
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Выполнение запроса для получения структуры таблицы
        cursor.execute("PRAGMA table_info(transactions);")

        # Извлечение данных
        columns = cursor.fetchall()

        # Выводим имена всех столбцов
        print("Структура таблицы transactions:")
        for column in columns:
            print(f"Колонка: {column[1]}")

        # Закрытие соединения
        conn.close()

    except Exception as e:
        print(f"Ошибка при получении данных из базы: {e}")


# Вызов функции для проверки структуры
check_table_structure()
