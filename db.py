import sqlite3

# Подключение к базе
conn = sqlite3.connect("lknbank.db")
cursor = conn.cursor()

# Получить список всех таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Таблицы:", tables)

# Посмотреть содержимое первой таблицы
for table_name in tables:
    print(f"\nСодержимое таблицы {table_name[0]}:")
    cursor.execute(f"SELECT * FROM {table_name[0]} LIMIT 5000000;")  # Показываем первые 5 строк
    rows = cursor.fetchall()
    for row in rows:
        print(row)

conn.close()