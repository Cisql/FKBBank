import aiosqlite
import logging
from typing import List, Dict, Any, Optional
import config
from datetime import datetime
import random

# Путь к файлу базы данных
DB_PATH = config.DB_PATH

async def init_db():
    """Инициализация базы данных и создание таблиц"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Создание таблицы пользователей
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0,
            blocked_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Создание таблицы транзакций
        await db.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            amount INTEGER NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (user_id),
            FOREIGN KEY (receiver_id) REFERENCES users (user_id)
        )
        ''')
        
        # Создание таблицы промокодов
        await db.execute('''
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            amount INTEGER NOT NULL,
            is_used INTEGER DEFAULT 0,
            used_by INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (used_by) REFERENCES users (user_id),
            FOREIGN KEY (created_by) REFERENCES users (user_id)
        )
        ''')
        
        # Создание таблицы администраторских действий
        await db.execute('''
        CREATE TABLE IF NOT EXISTS admin_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            target_user_id INTEGER,
            description TEXT,
            amount INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users (user_id),
            FOREIGN KEY (target_user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Создание таблицы для данных кликера
        await db.execute('''
        CREATE TABLE IF NOT EXISTS clicker_data (
            user_id INTEGER PRIMARY KEY,
            clicks INTEGER DEFAULT 0,
            balance REAL DEFAULT 0,
            multiplier INTEGER DEFAULT 1,
            multiplier_end_time TIMESTAMP,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Создание таблицы для игры "Угадай число"
        await db.execute('''
        CREATE TABLE IF NOT EXISTS guess_game (
            user_id INTEGER PRIMARY KEY,
            attempts_left INTEGER DEFAULT 3,
            last_attempt_date DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Создание таблицы для игры "Кубик"
        await db.execute('''
        CREATE TABLE IF NOT EXISTS dice_game (
            user_id INTEGER PRIMARY KEY,
            attempts_left INTEGER DEFAULT 1,
            last_attempt_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        await db.commit()
    
    logging.info("База данных инициализирована")

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение информации о пользователе"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
            if user:
                return dict(user)
    return None

async def create_user(user_id: int, username: str, first_name: str, last_name: str) -> None:
    """Создание нового пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, существует ли пользователь
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            existing_user = await cursor.fetchone()
        
        if not existing_user:
            # Если это новый пользователь, добавляем его с начальным бонусом
            await db.execute(
                "INSERT INTO users (user_id, username, first_name, last_name, balance) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, first_name, last_name, config.DEFAULT_WELCOME_BONUS)
            )
            
            # Создаем транзакцию для начального бонуса
            await db.execute(
                "INSERT INTO transactions (sender_id, receiver_id, amount, description) VALUES (NULL, ?, ?, ?)",
                (user_id, config.DEFAULT_WELCOME_BONUS, "Приветственный бонус")
            )
        else:
            # Если пользователь существует, обновляем его информацию
            await db.execute(
                "UPDATE users SET username = ?, first_name = ?, last_name = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                (username, first_name, last_name, user_id)
            )
        
        await db.commit()

async def update_balance(user_id: int, amount: int) -> None:
    """Обновление баланса пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()

async def update_user_balance(user_id: int, new_balance: float) -> None:
    """Установка нового значения баланса пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_balance, user_id)
        )
        await db.commit()

async def create_transaction(sender_id: int, receiver_id: int, amount: int, description: str = None) -> int:
    """Создание новой транзакции"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, не заблокирован ли отправитель
        if sender_id:
            async with db.execute("SELECT is_blocked FROM users WHERE user_id = ?", (sender_id,)) as cursor:
                sender = await cursor.fetchone()
                if sender and sender[0] == 1:
                    raise ValueError("Ваш аккаунт заблокирован, отправка средств недоступна")
        
        # Проверяем, не заблокирован ли получатель
        if receiver_id:
            async with db.execute("SELECT is_blocked FROM users WHERE user_id = ?", (receiver_id,)) as cursor:
                receiver = await cursor.fetchone()
                if receiver and receiver[0] == 1:
                    raise ValueError("Аккаунт получателя заблокирован, перевод невозможен")
        
        cursor = await db.execute(
            "INSERT INTO transactions (sender_id, receiver_id, amount, description) VALUES (?, ?, ?, ?)",
            (sender_id, receiver_id, amount, description)
        )
        transaction_id = cursor.lastrowid
        
        # Уменьшаем баланс отправителя, если это не система (sender_id = None)
        if sender_id:
            await db.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (amount, sender_id)
            )
        
        # Увеличиваем баланс получателя
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, receiver_id)
        )
        
        await db.commit()
        return transaction_id

async def get_transaction(transaction_id: int) -> Optional[Dict[str, Any]]:
    """Получение информации о транзакции по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT t.*, 
                   s.username as sender_username, s.first_name as sender_first_name,
                   r.username as receiver_username, r.first_name as receiver_first_name
            FROM transactions t
            LEFT JOIN users s ON t.sender_id = s.user_id
            LEFT JOIN users r ON t.receiver_id = r.user_id
            WHERE t.id = ?
            """,
            (transaction_id,)
        ) as cursor:
            transaction = await cursor.fetchone()
            if transaction:
                return dict(transaction)
    return None

async def get_top_users(limit: int = 10) -> List[Dict[str, Any]]:
    """Получение списка топ пользователей по балансу"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, username, first_name, last_name, balance FROM users WHERE is_blocked = 0 ORDER BY balance DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_transactions(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Получение списка транзакций пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT t.*, 
                   s.username as sender_username, s.first_name as sender_first_name,
                   r.username as receiver_username, r.first_name as receiver_first_name
            FROM transactions t
            LEFT JOIN users s ON t.sender_id = s.user_id
            LEFT JOIN users r ON t.receiver_id = r.user_id
            WHERE t.sender_id = ? OR t.receiver_id = ?
            ORDER BY t.created_at DESC LIMIT ?
            """,
            (user_id, user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def create_promo_code(code: str, amount: int, admin_id: int) -> None:
    """Создание нового промокода"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO promo_codes (code, amount, created_by) VALUES (?, ?, ?)",
            (code, amount, admin_id)
        )
        
        # Логирование действия администратора
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action_type, description, amount) VALUES (?, ?, ?, ?)",
            (admin_id, "CREATE_PROMO", f"Создан промокод: {code}", amount)
        )
        
        await db.commit()

async def use_promo_code(code: str, user_id: int) -> Optional[int]:
    """Использование промокода пользователем"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Проверяем, не заблокирован ли пользователь (кроме администраторов)
        if user_id:
            async with db.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
                if user and user[0] == 1:
                    raise ValueError("Ваш аккаунт заблокирован, активация промокода недоступна")
        
        # Проверяем, существует ли промокод и не использован ли он
        async with db.execute(
            "SELECT * FROM promo_codes WHERE code = ? AND is_used = 0",
            (code,)
        ) as cursor:
            promo = await cursor.fetchone()
            if not promo:
                return None
            
            # Помечаем промокод как использованный
            await db.execute(
                "UPDATE promo_codes SET is_used = 1, used_by = ? WHERE code = ?",
                (user_id, code)
            )
            
            # Пополняем баланс пользователя
            amount = promo["amount"]
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, user_id)
            )
            
            # Создаем транзакцию
            await db.execute(
                "INSERT INTO transactions (sender_id, receiver_id, amount, description) VALUES (NULL, ?, ?, ?)",
                (user_id, amount, f"Активация промокода: {code}")
            )
            
            await db.commit()
            return amount

# Новые функции для администрирования

async def block_user(admin_id: int, user_id: int, reason: str) -> bool:
    """Блокировка пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Блокируем пользователя
        await db.execute(
            "UPDATE users SET is_blocked = 1, blocked_reason = ? WHERE user_id = ?",
            (reason, user_id)
        )
        
        # Логируем действие администратора
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action_type, target_user_id, description) VALUES (?, ?, ?, ?)",
            (admin_id, "BLOCK_USER", user_id, reason)
        )
        
        await db.commit()
        return True

async def unblock_user(admin_id: int, user_id: int) -> bool:
    """Разблокировка пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем причину блокировки для лога
        async with db.execute(
            "SELECT blocked_reason FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
            reason = user[0] if user else "Не указана"
        
        # Разблокируем пользователя
        await db.execute(
            "UPDATE users SET is_blocked = 0, blocked_reason = NULL WHERE user_id = ?",
            (user_id,)
        )
        
        # Логируем действие администратора
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action_type, target_user_id, description) VALUES (?, ?, ?, ?)",
            (admin_id, "UNBLOCK_USER", user_id, f"Разблокирован (прежняя причина: {reason})")
        )
        
        await db.commit()
        return True

async def add_balance(admin_id: int, user_id: int, amount: int, description: str = None) -> bool:
    """Добавление баланса пользователю администратором"""
    if admin_id:
        return False
    
    if amount <= 0:
        return False
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, существует ли пользователь
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                return False
        
        # Добавляем баланс
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        
        # Создаем транзакцию
        await db.execute(
            "INSERT INTO transactions (sender_id, receiver_id, amount, description) VALUES (?, ?, ?, ?)",
            (admin_id, user_id, amount, description or f"Начисление от администратора")
        )
        
        # Логирование действия администратора
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action_type, target_user_id, amount, description) VALUES (?, ?, ?, ?, ?)",
            (admin_id, "ADD_BALANCE", user_id, amount, description or "Начисление баланса")
        )
        
        await db.commit()
        return True

async def remove_balance(admin_id: int, user_id: int, amount: int, description: str = None) -> bool:
    """Списание баланса у пользователя администратором"""
    if admin_id:
        return False
    
    if amount <= 0:
        return False
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, существует ли пользователь и хватает ли баланса
        async with db.execute("SELECT user_id, balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                return False
            
            if user[1] < amount:
                # Если баланса недостаточно, списываем весь имеющийся
                amount = user[1]
                if amount == 0:
                    return False
        
        # Уменьшаем баланс
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (amount, user_id)
        )
        
        # Создаем транзакцию
        await db.execute(
            "INSERT INTO transactions (sender_id, receiver_id, amount, description) VALUES (?, ?, ?, ?)",
            (user_id, admin_id, amount, description or f"Списание администратором")
        )
        
        # Логирование действия администратора
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action_type, target_user_id, amount, description) VALUES (?, ?, ?, ?, ?)",
            (admin_id, "REMOVE_BALANCE", user_id, amount, description or "Списание баланса")
        )
        
        await db.commit()
        return True

async def get_all_users(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Получение списка всех пользователей для администраторов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT user_id, username, first_name, last_name, balance, is_blocked, blocked_reason, created_at, last_active
            FROM users
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_admin_actions(admin_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Получение истории действий администраторов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = """
        SELECT a.*, 
               u1.username as admin_username, u1.first_name as admin_first_name,
               u2.username as target_username, u2.first_name as target_first_name
        FROM admin_actions a
        LEFT JOIN users u1 ON a.admin_id = u1.user_id
        LEFT JOIN users u2 ON a.target_user_id = u2.user_id
        """
        
        params = []
        if admin_id is not None:
            query += " WHERE a.admin_id = ?"
            params.append(admin_id)
        
        query += " ORDER BY a.created_at DESC LIMIT ?"
        params.append(limit)
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_user_stats() -> Dict[str, Any]:
    """Получение статистики пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Общее количество пользователей
        async with db.execute("SELECT COUNT(*) as count FROM users") as cursor:
            total_users = (await cursor.fetchone())["count"]
        
        # Активные пользователи (не заблокированные)
        async with db.execute("SELECT COUNT(*) as count FROM users WHERE is_blocked = 0") as cursor:
            active_users = (await cursor.fetchone())["count"]
        
        # Заблокированные пользователи
        async with db.execute("SELECT COUNT(*) as count FROM users WHERE is_blocked = 1") as cursor:
            blocked_users = (await cursor.fetchone())["count"]
        
        # Общая сумма всех балансов
        async with db.execute("SELECT SUM(balance) as total FROM users") as cursor:
            total_balance = (await cursor.fetchone())["total"] or 0
        
        # Новые пользователи за последние 24 часа
        async with db.execute("SELECT COUNT(*) as count FROM users WHERE created_at >= datetime('now', '-1 day')") as cursor:
            new_users_24h = (await cursor.fetchone())["count"]
        
        # Количество транзакций за последние 24 часа
        async with db.execute("SELECT COUNT(*) as count FROM transactions WHERE created_at >= datetime('now', '-1 day')") as cursor:
            transactions_24h = (await cursor.fetchone())["count"]
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "total_balance": total_balance,
            "new_users_24h": new_users_24h,
            "transactions_24h": transactions_24h
        }

async def find_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Поиск пользователя по имени пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Удаляем символ @ из начала имени пользователя, если он есть
        if username.startswith('@'):
            username = username[1:]
        
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ) as cursor:
            user = await cursor.fetchone()
            if user:
                return dict(user)
    return None

async def search_users(query: str) -> List[Dict[str, Any]]:
    """Поиск пользователей по ID, имени или юзернейму"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Если запрос - это число, пробуем искать по ID
        if query.isdigit():
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ?", (int(query),)
            ) as cursor:
                user = await cursor.fetchone()
                if user:
                    return [dict(user)]
        
        # Если запрос начинается с @, ищем по точному юзернейму
        if query.startswith('@'):
            username = query[1:]
            async with db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ) as cursor:
                user = await cursor.fetchone()
                if user:
                    return [dict(user)]
        
        # Иначе ищем по частичному совпадению имени, фамилии или юзернейма
        search_pattern = f"%{query}%"
        async with db.execute(
            """SELECT * FROM users 
               WHERE username LIKE ? 
               OR first_name LIKE ? 
               OR last_name LIKE ?
               LIMIT 20""", 
            (search_pattern, search_pattern, search_pattern)
        ) as cursor:
            users = await cursor.fetchall()
            return [dict(user) for user in users]

async def get_clicker_data(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение данных кликера для пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM clicker_data WHERE user_id = ?", (user_id,)
        ) as cursor:
            data = await cursor.fetchone()
            if data:
                return dict(data)
    return None

async def create_or_update_clicker_data(user_id: int, clicks: int, balance: float, 
                               multiplier: int = 1, multiplier_end_time = None) -> None:
    """Создание или обновление данных кликера для пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, существуют ли данные кликера для пользователя
        async with db.execute("SELECT user_id FROM clicker_data WHERE user_id = ?", (user_id,)) as cursor:
            existing_data = await cursor.fetchone()
        
        if not existing_data:
            # Если это новые данные, добавляем их
            if multiplier_end_time:
                await db.execute(
                    "INSERT INTO clicker_data (user_id, clicks, balance, multiplier, multiplier_end_time) VALUES (?, ?, ?, ?, ?)",
                    (user_id, clicks, balance, multiplier, multiplier_end_time)
                )
            else:
                await db.execute(
                    "INSERT INTO clicker_data (user_id, clicks, balance, multiplier) VALUES (?, ?, ?, ?)",
                    (user_id, clicks, balance, multiplier)
                )
        else:
            # Если данные существуют, обновляем их
            if multiplier_end_time:
                await db.execute(
                    """UPDATE clicker_data SET 
                       clicks = ?, balance = ?, multiplier = ?, 
                       multiplier_end_time = ?, last_update = CURRENT_TIMESTAMP 
                       WHERE user_id = ?""",
                    (clicks, balance, multiplier, multiplier_end_time, user_id)
                )
            else:
                await db.execute(
                    """UPDATE clicker_data SET 
                       clicks = ?, balance = ?, multiplier = ?, 
                       multiplier_end_time = NULL, last_update = CURRENT_TIMESTAMP 
                       WHERE user_id = ?""",
                    (clicks, balance, multiplier, user_id)
                )
        
        await db.commit()

async def reset_clicker_balance(user_id: int) -> None:
    """Сброс баланса кликера для пользователя (после вывода средств)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE clicker_data SET balance = 0, last_update = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()

async def get_top_clickers(limit: int = 10) -> List[Dict[str, Any]]:
    """Получение списка топ пользователей по количеству кликов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT c.*, u.username, u.first_name 
               FROM clicker_data c
               JOIN users u ON c.user_id = u.user_id
               WHERE u.is_blocked = 0 
               ORDER BY c.clicks DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_blocked_users() -> List[Dict[str, Any]]:
    """Получение списка заблокированных пользователей"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE is_blocked = 1"
        ) as cursor:
            users = await cursor.fetchall()
            return [dict(user) for user in users]

async def get_guess_game_data(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение данных игры 'Угадай число' пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM guess_game WHERE user_id = ?", (user_id,)
        ) as cursor:
            data = await cursor.fetchone()
            if data:
                return dict(data)
    return None

async def create_or_update_guess_game(user_id: int, attempts_left: int = None) -> None:
    """Создание или обновление данных игры 'Угадай число'"""
    current_date = "CURRENT_DATE"
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, существует ли запись
        async with db.execute(
            "SELECT * FROM guess_game WHERE user_id = ?", (user_id,)
        ) as cursor:
            data = await cursor.fetchone()
            
            if data:
                # Если существует, проверяем дату
                async with db.execute(
                    "SELECT last_attempt_date FROM guess_game WHERE user_id = ?", (user_id,)
                ) as date_cursor:
                    date_row = await date_cursor.fetchone()
                    last_date = date_row[0] if date_row else None
                
                # Если дата не сегодняшняя, сбрасываем попытки
                query = "SELECT DATE(last_attempt_date) < DATE('now') FROM guess_game WHERE user_id = ?"
                async with db.execute(query, (user_id,)) as check_cursor:
                    is_new_day = await check_cursor.fetchone()
                    if is_new_day and is_new_day[0]:
                        await db.execute(
                            "UPDATE guess_game SET attempts_left = 3, last_attempt_date = CURRENT_DATE WHERE user_id = ?",
                            (user_id,)
                        )
                    elif attempts_left is not None:
                        # Иначе просто обновляем количество попыток
                        await db.execute(
                            "UPDATE guess_game SET attempts_left = ? WHERE user_id = ?",
                            (attempts_left, user_id)
                        )
            else:
                # Если не существует, создаем новую запись
                await db.execute(
                    "INSERT INTO guess_game (user_id, attempts_left, last_attempt_date) VALUES (?, 3, CURRENT_DATE)",
                    (user_id,)
                )
        
        await db.commit()

async def update_guess_attempts(user_id: int, attempts_used: int = 1) -> Optional[int]:
    """Обновляет количество попыток, возвращает оставшееся количество"""
    today = datetime.now().date()
    data = await get_guess_game_data(user_id)
    
    if not data:
        await create_or_update_guess_game(user_id)
        data = await get_guess_game_data(user_id)
    
    # Если последняя попытка была в другой день - обнуляем счетчик
    last_attempt_date = None
    if data["last_attempt_date"]:
        # Проверяем тип данных last_attempt_date
        if isinstance(data["last_attempt_date"], str):
            try:
                last_attempt_date = datetime.fromisoformat(data["last_attempt_date"]).date()
            except ValueError:
                # Если не удалось преобразовать строку в дату, считаем что последней попытки не было
                last_attempt_date = None
        else:
            last_attempt_date = data["last_attempt_date"].date()
    
    if last_attempt_date != today:
        attempts_left = config.GUESS_GAME_MAX_ATTEMPTS - attempts_used
    else:
        attempts_left = max(0, data["attempts_left"] - attempts_used)
    
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """
            UPDATE guess_game
            SET attempts_left = ?, last_attempt_date = ?
            WHERE user_id = ?
            """,
            (attempts_left, datetime.now().isoformat(), user_id)
        )
        await conn.commit()
    
    return attempts_left

async def get_guess_game_attempts_left(user_id: int) -> int:
    """Возвращает количество оставшихся попыток в игре 'Угадай число'"""
    today = datetime.now().date()
    data = await get_guess_game_data(user_id)
    
    if not data:
        await create_or_update_guess_game(user_id)
        return config.GUESS_GAME_MAX_ATTEMPTS
    
    # Если последняя попытка была в другой день - сбрасываем счетчик
    last_attempt_date = None
    if data["last_attempt_date"]:
        # Проверяем тип данных last_attempt_date
        if isinstance(data["last_attempt_date"], str):
            try:
                last_attempt_date = datetime.fromisoformat(data["last_attempt_date"]).date()
            except ValueError:
                # Если не удалось преобразовать строку в дату, считаем что последней попытки не было
                last_attempt_date = None
        else:
            last_attempt_date = data["last_attempt_date"].date()
    
    if last_attempt_date != today:
        await create_or_update_guess_game(user_id, config.GUESS_GAME_MAX_ATTEMPTS)
        return config.GUESS_GAME_MAX_ATTEMPTS
    
    return data["attempts_left"]

async def play_guess_game(user_id: int, guess: int) -> Dict[str, Any]:
    """Основная логика игры 'Угадай число'"""
    # Получаем данные об игре
    attempts_left = await get_guess_game_attempts_left(user_id)
    
    # Проверяем, есть ли у пользователя попытки
    if attempts_left <= 0:
        raise ValueError("У вас закончились попытки на сегодня. Возвращайтесь завтра!")
    
    # Генерируем случайное число от 1 до 10
    random_number = random.randint(1, 10)
    
    # Проверяем угадал ли пользователь
    is_correct = guess == random_number
    
    # Обновляем количество попыток
    attempts_left = await update_guess_attempts(user_id, 1)
    
    user = await get_user(user_id)
    old_balance = user["balance"]
    
    # Если пользователь угадал, начисляем ему бонус
    if is_correct:
        # Начисляем награду за правильный ответ
        await create_transaction(None, user_id, config.GUESS_GAME_REWARD, "Выигрыш в игре 'Угадай число'")
        user = await get_user(user_id)
        new_balance = user["balance"]
        
        return {
            "success": True,
            "correct": True,
            "random_number": random_number,
            "attempts_left": attempts_left,
            "reward": config.GUESS_GAME_REWARD,
            "old_balance": old_balance,
            "new_balance": new_balance
        }
    else:
        # Если не угадал - снимаем штраф
        # Проверяем что у пользователя достаточно средств
        user_balance = user["balance"]
        penalty = min(user_balance, config.GUESS_GAME_PENALTY)  # Снимаем штраф или весь баланс, если он меньше штрафа
        
        if penalty > 0:
            await create_transaction(user_id, None, penalty, "Проигрыш в игре 'Угадай число'")
        
        user = await get_user(user_id)
        new_balance = user["balance"]
        
        return {
            "success": True,
            "correct": False,
            "random_number": random_number,
            "attempts_left": attempts_left,
            "penalty": penalty,
            "old_balance": old_balance,
            "new_balance": new_balance
        }

# Функции для игры "Кубик"
async def get_dice_game_data(user_id: int) -> Optional[Dict[str, Any]]:
    """Получает данные об игре 'Кубик' для пользователя"""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT * FROM dice_game WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
    
    if row:
        return {
            "user_id": row[0],
            "attempts_left": row[1],
            "last_attempt_date": datetime.fromisoformat(row[2]) if row[2] else None
        }
    return None

async def create_or_update_dice_game(user_id: int, attempts_left: int = None) -> None:
    """Создает или обновляет запись об игре 'Кубик' для пользователя"""
    today = datetime.now().date()
    data = await get_dice_game_data(user_id)
    
    async with aiosqlite.connect(DB_PATH) as conn:
        if not data:
            # Если записи нет, создаем новую
            await conn.execute(
                """
                INSERT INTO dice_game (user_id, attempts_left, last_attempt_date)
                VALUES (?, ?, ?)
                """,
                (user_id, config.DICE_GAME_MAX_ATTEMPTS if attempts_left is None else attempts_left, None)
            )
        else:
            # Если запись есть, проверяем дату последней попытки
            last_attempt_date = None
            if data["last_attempt_date"]:
                # Проверяем тип данных last_attempt_date
                if isinstance(data["last_attempt_date"], str):
                    try:
                        last_attempt_date = datetime.fromisoformat(data["last_attempt_date"]).date()
                    except ValueError:
                        # Если не удалось преобразовать строку в дату, считаем что последней попытки не было
                        last_attempt_date = None
                else:
                    last_attempt_date = data["last_attempt_date"].date()
            
            if last_attempt_date != today:
                # Если день изменился, сбрасываем счетчик попыток
                await conn.execute(
                    """
                    UPDATE dice_game
                    SET attempts_left = ?, last_attempt_date = NULL
                    WHERE user_id = ?
                    """,
                    (config.DICE_GAME_MAX_ATTEMPTS if attempts_left is None else attempts_left, user_id)
                )
            elif attempts_left is not None:
                # Если день тот же и нам передали новое количество попыток, обновляем его
                await conn.execute(
                    """
                    UPDATE dice_game
                    SET attempts_left = ?
                    WHERE user_id = ?
                    """,
                    (attempts_left, user_id)
                )
        
        await conn.commit()

async def update_dice_attempts(user_id: int, attempts_used: int = 1) -> Optional[int]:
    """Обновляет количество попыток, возвращает оставшееся количество"""
    today = datetime.now().date()
    data = await get_dice_game_data(user_id)
    
    if not data:
        await create_or_update_dice_game(user_id)
        data = await get_dice_game_data(user_id)
    
    # Если последняя попытка была в другой день - обнуляем счетчик
    last_attempt_date = None
    if data["last_attempt_date"]:
        # Проверяем тип данных last_attempt_date
        if isinstance(data["last_attempt_date"], str):
            try:
                last_attempt_date = datetime.fromisoformat(data["last_attempt_date"]).date()
            except ValueError:
                # Если не удалось преобразовать строку в дату, считаем что последней попытки не было
                last_attempt_date = None
        else:
            last_attempt_date = data["last_attempt_date"].date()
    
    if last_attempt_date != today:
        attempts_left = config.DICE_GAME_MAX_ATTEMPTS - attempts_used
    else:
        attempts_left = max(0, data["attempts_left"] - attempts_used)
    
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """
            UPDATE dice_game
            SET attempts_left = ?, last_attempt_date = ?
            WHERE user_id = ?
            """,
            (attempts_left, datetime.now().isoformat(), user_id)
        )
        await conn.commit()
    
    return attempts_left

async def get_dice_game_attempts_left(user_id: int) -> int:
    """Возвращает количество оставшихся попыток в игре 'Кубик'"""
    today = datetime.now().date()
    data = await get_dice_game_data(user_id)
    
    if not data:
        await create_or_update_dice_game(user_id)
        return config.DICE_GAME_MAX_ATTEMPTS
    
    # Если последняя попытка была в другой день - сбрасываем счетчик
    last_attempt_date = None
    if data["last_attempt_date"]:
        # Проверяем тип данных last_attempt_date
        if isinstance(data["last_attempt_date"], str):
            try:
                last_attempt_date = datetime.fromisoformat(data["last_attempt_date"]).date()
            except ValueError:
                # Если не удалось преобразовать строку в дату, считаем что последней попытки не было
                last_attempt_date = None
        else:
            last_attempt_date = data["last_attempt_date"].date()
    
    if last_attempt_date != today:
        await create_or_update_dice_game(user_id, config.DICE_GAME_MAX_ATTEMPTS)
        return config.DICE_GAME_MAX_ATTEMPTS
    
    return data["attempts_left"]

async def play_dice_game(user_id: int) -> Dict[str, Any]:
    """Основная логика игры 'Кубик'"""
    # Получаем данные об игре
    attempts_left = await get_dice_game_attempts_left(user_id)
    
    # Проверяем, есть ли у пользователя попытки
    if attempts_left <= 0:
        raise ValueError("У вас закончились попытки на сегодня. Возвращайтесь завтра!")
    
    # Генерируем случайное число от 1 до 6 (как на кубике)
    dice_value = random.randint(1, 6)
    
    # Рассчитываем награду в зависимости от выпавшего значения
    # Чем больше значение, тем больше награда
    min_reward = config.DICE_GAME_MIN_REWARD
    max_reward = config.DICE_GAME_MAX_REWARD
    reward_step = (max_reward - min_reward) / 5  # 5 шагов от 1 до 6
    
    reward = int(min_reward + (dice_value - 1) * reward_step)
    
    # Обновляем количество попыток
    attempts_left = await update_dice_attempts(user_id, 1)
    
    user = await get_user(user_id)
    old_balance = user["balance"]
    
    # Начисляем награду
    await create_transaction(None, user_id, reward, f"Выигрыш в игре 'Кубик': выпало {dice_value}")
    
    user = await get_user(user_id)
    new_balance = user["balance"]
    
    return {
        "success": True,
        "value": dice_value,
        "reward": reward,
        "attempts_left": attempts_left,
        "old_balance": old_balance,
        "new_balance": new_balance
    }