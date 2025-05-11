import datetime
import asyncio
import os
import random
import string
import base64
import secrets
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Form, Cookie, HTTPException, Depends, File, UploadFile, Header, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
import database as db
import config
import aiosqlite
from datetime import datetime
from pathlib import Path
from fastapi import Depends, HTTPException, Header, status
from fastapi import Header, HTTPException, status
import json
from pathlib import Path
from fastapi import FastAPI

# Определяем путь к базе данных
DB_PATH = config.DB_PATH

# Учетные данные для доступа к админке
ADMIN_USERNAME = config.ADMIN_USERNAME
ADMIN_PASSWORD = config.ADMIN_PASSWORD  # В реальном приложении используйте более безопасный подход
TOKENS_FILE = Path("users_tokens.json")

router = APIRouter()
app = FastAPI()

app.include_router(router)

def load_tokens():
    if TOKENS_FILE.exists():
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

async def verify_admin_token(authorization: str = Header(...)):
    tokens = load_tokens()

    # Проверим, есть ли такой токен вообще
    if authorization not in tokens.values():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен"
        )

    # Найдём user_id, которому принадлежит этот токен
    user_ids = [user_id for user_id, token in tokens.items() if token == authorization]

    # Если найденный user_id — число, это обычный пользователь
    if any(user_id.isdigit() for user_id in user_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав администратора"
        )

# Вспомогательная функция для проверки авторизации пользователя
async def validate_user(user_id: int):
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Проверка на блокировку
    if user["is_blocked"] == 1:
        raise HTTPException(status_code=403, detail=f"Ваш аккаунт заблокирован. Причина: {user['blocked_reason'] or 'Не указана'}")

    return user

# Функция проверки HTTP Basic авторизации для админки
async def get_admin_credentials(authorization: str = Header(None)):
    if authorization is None or not authorization.startswith("Basic "):
        return False

    try:
        credentials = authorization.replace("Basic ", "")
        decoded = base64.b64decode(credentials).decode("utf-8")
        username, password = decoded.split(":")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return True
    except Exception:
        pass

    return False

# Прямой доступ к админке через API (запасной вариант)
@router.get("/admin/")
async def direct_admin(request: Request, authorized: bool = Depends(get_admin_credentials)):
    if not authorized:
        # Если авторизация не прошла, запрашиваем учетные данные (используем только английский текст)
        headers = {"WWW-Authenticate": "Basic realm=\"Admin Panel Authentication\""}
        return Response(
            content="Authorization required",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers=headers
        )

    # Если авторизация прошла успешно, отдаем админку
    admin_path = os.path.join("static", "3di3kdidklwks1023.html")

    if os.path.exists(admin_path):
        with open(admin_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse("<html><body><h1>Admin Panel</h1><p>File admin.html not found in static directory.</p></body></html>")

# Регистрация/авторизация пользователя
@router.post("/auth")
async def auth(
    user_id: int = Form(...),
    username: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None)
):
    # Проверяем, существует ли пользователь
    await db.create_user(user_id, username, first_name, last_name)
    user = await db.get_user(user_id)

    # Проверка на блокировку
    if user["is_blocked"] == 1:
        return {
            **user,
            "is_error": True,
            "error_message": f"Ваш аккаунт заблокирован. Причина: {user['blocked_reason'] or 'Не указана'}"
        }

    return user

# Получение информации о пользователе
@router.get("/user/{user_id}")
async def get_user(user_id: int):
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

# Поиск пользователя по нику (используем специфичный путь)
@router.get("/find-user-by-username/{username}")
async def find_user_by_username(username: str):
    user = await db.find_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user

# Получение истории транзакций пользователя
@router.get("/transactions/{user_id}")
async def get_transactions(
    user_id: int,
    limit: int = 20,
    _=Depends(verify_admin_token)  # проверка токена
):
    user = await validate_user(user_id)
    transactions = await db.get_transactions(user_id, limit)
    return transactions

# Перевод средств другому пользователю
@router.post("/transfer")
async def transfer(
    sender_id: int = Form(...),
    receiver_id: int = Form(...),
    amount: int = Form(...),
    description: str = Form(None)
):
    # Проверяем существование отправителя
    sender = await validate_user(sender_id)

    # Проверяем существование получателя
    receiver = await db.get_user(receiver_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="Получатель не найден")

    # Проверяем, что получатель не заблокирован
    if receiver["is_blocked"] == 1:
        raise HTTPException(status_code=400, detail="Получатель заблокирован, перевод невозможен")

    # Проверяем, что отправитель не переводит самому себе
    if sender_id == receiver_id:
        raise HTTPException(status_code=400, detail="Нельзя отправить перевод самому себе")

    # Проверяем, что у отправителя достаточно средств
    if sender["balance"] < amount:
        raise HTTPException(status_code=400, detail="Недостаточно средств на балансе")

    # Проверяем, что сумма перевода положительная
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма перевода должна быть положительной")

    try:
        # Создаем транзакцию
        transaction_id = await db.create_transaction(sender_id, receiver_id, amount, description)

        # Получаем информацию о транзакции
        transaction = await db.get_transaction(transaction_id)

        # Возвращаем обновленную информацию о пользователе и транзакции
        return {
            "success": True,
            "user": await db.get_user(sender_id),
            "transaction": transaction
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Использование промокода
@router.post("/promo")
async def use_promo(
    user_id: int = Form(...),
    code: str = Form(...)
):
    # Проверяем существование пользователя
    user = await validate_user(user_id)

    try:
        # Пытаемся активировать промокод
        amount = await db.use_promo_code(code, user_id)

        if amount is None:
            raise HTTPException(status_code=400, detail="Промокод недействителен или уже использован")

        # Возвращаем обновленную информацию о пользователе
        return {
            "success": True,
            "amount": amount,
            "user": await db.get_user(user_id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Получение топ пользователей по балансу
@router.get("/top")
async def get_top_users(limit: int = 10):
    top_users = await db.get_top_users(limit)
    return top_users

# --- Админские эндпоинты ---

# Генерация нового промокода
@router.post("/admin/promo")
async def create_promo(amount: int = Form(...), length: int = Form(8)):
    """
    Создание промокода администратором
    """
    if amount <= 0:
        return {"success": False, "error": "Сумма должна быть положительной"}

    if length < 4 or length > 16:
        return {"success": False, "error": "Длина промокода должна быть от 4 до 16 символов"}

    # Проверяем структуру таблицы admin_actions
    await ensure_admin_actions_table()

    # Генерируем случайный промокод
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    # Записываем промокод в БД
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO promo_codes (code, amount, created_at) VALUES (?, ?, ?)",
            (code, amount, datetime.now().isoformat())
        )
        await db.commit()

        # Записываем действие администратора без admin_id
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action, timestamp) VALUES (?, ?, ?)",
            (0, f"Создан промокод на сумму {amount} Ⱡ", datetime.now().isoformat())
        )
        await db.commit()

    return {"success": True, "code": code, "amount": amount}

# Проверяем структуру таблицы admin_actions
async def ensure_admin_actions_table():
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем существование таблицы
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_actions'")
        table_exists = await cursor.fetchone()

        if not table_exists:
            # Создаем таблицу если не существует
            await db.execute("""
                CREATE TABLE admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            await db.commit()
        else:
            # Проверяем структуру существующей таблицы
            cursor = await db.execute("PRAGMA table_info(admin_actions)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            # Проверяем каждую необходимую колонку
            columns_to_check = {
                'action': "TEXT DEFAULT 'Действие администратора'",
                'timestamp': "TEXT DEFAULT CURRENT_TIMESTAMP"
            }

            # Пересоздаем таблицу, если нужны множественные изменения
            needs_rebuild = False
            for col_name in columns_to_check:
                if col_name not in column_names:
                    needs_rebuild = True
                    break

            if needs_rebuild:
                try:
                    # Проверяем, есть ли временная таблица
                    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_actions_new'")
                    temp_table_exists = await cursor.fetchone()

                    if temp_table_exists:
                        await db.execute("DROP TABLE admin_actions_new")
                        await db.commit()

                    # Создаем новую структуру таблицы
                    await db.execute("""
                        CREATE TABLE admin_actions_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            admin_id INTEGER NOT NULL,
                            action TEXT NOT NULL,
                            timestamp TEXT NOT NULL
                        )
                    """)

                    # Копируем данные, с учетом существующих колонок
                    select_columns = "id, admin_id"
                    if 'action' in column_names:
                        select_columns += ", action"
                    elif 'description' in column_names:
                        select_columns += ", description as action"
                    else:
                        select_columns += ", 'Действие администратора' as action"

                    if 'timestamp' in column_names:
                        select_columns += ", timestamp"
                    else:
                        select_columns += ", datetime('now') as timestamp"

                    await db.execute(f"""
                        INSERT INTO admin_actions_new (id, admin_id, action, timestamp)
                        SELECT {select_columns} FROM admin_actions
                    """)

                    await db.execute("DROP TABLE admin_actions")
                    await db.execute("ALTER TABLE admin_actions_new RENAME TO admin_actions")
                    await db.commit()

                    print("Таблица admin_actions успешно пересоздана")
                except Exception as e:
                    print(f"Ошибка при пересоздании таблицы admin_actions: {e}")
                    # Пробуем добавить колонки по одной
                    for col_name, col_type in columns_to_check.items():
                        if col_name not in column_names:
                            try:
                                await db.execute(f"ALTER TABLE admin_actions ADD COLUMN {col_name} {col_type}")
                                await db.commit()
                                print(f"Добавлена колонка {col_name} в таблицу admin_actions")
                            except Exception as e2:
                                print(f"Ошибка при добавлении колонки {col_name}: {e2}")
            else:
                # Добавляем колонки по одной, если необходимо
                for col_name, col_type in columns_to_check.items():
                    if col_name not in column_names:
                        try:
                            await db.execute(f"ALTER TABLE admin_actions ADD COLUMN {col_name} {col_type}")
                            await db.commit()
                            print(f"Добавлена колонка {col_name} в таблицу admin_actions")
                        except Exception as e:
                            print(f"Ошибка при добавлении колонки {col_name}: {e}")

# Блокировка пользователя
@router.post("/admin/block_user")
async def block_user(user_id: str = Form(...), reason: str = Form("")):
    """
    Блокировка пользователя администратором
    """
    try:
        user_id = int(user_id)
    except ValueError:
        return {"success": False, "error": "Некорректный ID пользователя"}

    # Проверяем существование пользователя
    user_exists = await user_exists_by_id(user_id)
    if not user_exists:
        return {"success": False, "error": "Пользователь не найден"}

    # Проверяем структуру таблицы admin_actions
    await ensure_admin_actions_table()

    # Блокируем пользователя
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_blocked = 1, blocked_reason = ? WHERE user_id = ?",
            (reason, user_id)
        )

        # Записываем действие администратора без admin_id
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action, timestamp) VALUES (?, ?, ?)",
            (0, f"Блокировка пользователя {user_id}{' по причине: ' + reason if reason else ''}", datetime.now().isoformat())
        )

        await db.commit()

    return {"success": True}

# Разблокировка пользователя
@router.post("/admin/unblock_user")
async def unblock_user(user_id: str = Form(...)):
    """
    Разблокировка пользователя администратором
    """
    try:
        user_id = int(user_id)
    except ValueError:
        return {"success": False, "error": "Некорректный ID пользователя"}

    # Проверяем существование пользователя
    user_exists = await user_exists_by_id(user_id)
    if not user_exists:
        return {"success": False, "error": "Пользователь не найден"}

    # Проверяем структуру таблицы admin_actions
    await ensure_admin_actions_table()

    # Разблокируем пользователя
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_blocked = 0, blocked_reason = NULL WHERE user_id = ?",
            (user_id,)
        )

        # Записываем действие администратора без admin_id
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action, timestamp) VALUES (?, ?, ?)",
            (0, f"Разблокировка пользователя {user_id}", datetime.now().isoformat())
        )

        await db.commit()

    return {"success": True}

# Выдача баланса пользователю
@router.post("/admin/add_balance")
async def add_balance(user_id: str = Form(...), amount: int = Form(...), description: str = Form("")):
    """
    Добавление средств пользователю администратором
    """
    try:
        amount = int(amount)
        user_id = int(user_id)
    except ValueError:
        return {"success": False, "error": "Некорректные параметры"}

    if amount <= 0:
        return {"success": False, "error": "Сумма должна быть положительной"}

    # Проверяем существование пользователя
    user_exists = await user_exists_by_id(user_id)
    if not user_exists:
        return {"success": False, "error": "Пользователь не найден"}

    # Проверяем структуру таблицы admin_actions
    await ensure_admin_actions_table()

    # Пополняем баланс
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем текущий баланс
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        current_balance = row[0]

        # Обновляем баланс
        new_balance = current_balance + amount
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))

        # Создаем транзакцию с system_id вместо admin_id
        await db.execute(
            "INSERT INTO transactions (sender_id, receiver_id, amount, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (0, user_id, amount, f"Пополнение администратором: {description}", datetime.now().isoformat())
        )

        # Записываем действие администратора без admin_id
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action, timestamp) VALUES (?, ?, ?)",
            (0, f"Пополнение баланса пользователя {user_id} на {amount} Ⱡ", datetime.now().isoformat())
        )

        await db.commit()

    return {"success": True, "new_balance": new_balance}

# Списание баланса у пользователя
@router.post("/admin/remove_balance")
async def remove_balance(user_id: str = Form(...), amount: int = Form(...), description: str = Form("")):
    """
    Снятие средств у пользователя администратором
    """
    try:
        amount = int(amount)
        user_id = int(user_id)
    except ValueError:
        return {"success": False, "error": "Некорректные параметры"}

    if amount <= 0:
        return {"success": False, "error": "Сумма должна быть положительной"}

    # Проверяем существование пользователя
    user_exists = await user_exists_by_id(user_id)
    if not user_exists:
        return {"success": False, "error": "Пользователь не найден"}

    # Проверяем структуру таблицы admin_actions
    await ensure_admin_actions_table()

    # Снимаем с баланса
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем текущий баланс
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        current_balance = row[0]

        # Проверяем достаточно ли средств
        if current_balance < amount:
            return {"success": False, "error": "Недостаточно средств на балансе пользователя"}

        # Обновляем баланс
        new_balance = current_balance - amount
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))

        # Создаем транзакцию с system_id вместо admin_id
        await db.execute(
            "INSERT INTO transactions (sender_id, receiver_id, amount, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, 0, amount, f"Списание администратором: {description}", datetime.now().isoformat())
        )

        # Записываем действие администратора без admin_id
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action, timestamp) VALUES (?, ?, ?)",
            (0, f"Списание с баланса пользователя {user_id} на {amount} Ⱡ", datetime.now().isoformat())
        )

        await db.commit()

    return {"success": True, "new_balance": new_balance}

@router.post("/qiwi/remove_balance")
async def remove_balance(
    user_id: str = Form(...),
    amount: int = Form(...),
    description: str = Form(""),
    admin_id: str = Depends(verify_admin_token)
):
    """
    Снятие средств у пользователя администратором
    """
    try:
        amount = int(amount)
        user_id = int(user_id)
    except ValueError:
        return {"success": False, "error": "Некорректные параметры"}

    if amount <= 0:
        return {"success": False, "error": "Сумма должна быть положительной"}

    user_exists = await user_exists_by_id(user_id)
    if not user_exists:
        return {"success": False, "error": "Пользователь не найден"}

    await ensure_admin_actions_table()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        current_balance = row[0]

        if current_balance < amount:
            return {"success": False, "error": "Недостаточно средств на балансе пользователя"}

        new_balance = current_balance - amount
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))

        await db.execute(
            "INSERT INTO transactions (sender_id, receiver_id, amount, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, 0, amount, f"Списание администратором: {description}", datetime.now().isoformat())
        )

        # Сохраняем кто именно списал
        await db.execute(
            "INSERT INTO admin_actions (admin_id, action, timestamp) VALUES (?, ?, ?)",
            (admin_id, f"Списание с баланса пользователя {user_id} на {amount} Ⱡ", datetime.now().isoformat())
        )

        await db.commit()

    return {"success": True, "new_balance": new_balance}

# Получение списка всех пользователей
@router.get("/admin/users")
async def get_users(limit: int = 100, offset: int = 0):
    users = await db.get_all_users(limit, offset)
    return {
        "success": True,
        "users": users
    }

# Получение статистики пользователей
@router.get("/admin/stats")
async def get_stats():
    stats = await db.get_user_stats()
    return {
        "success": True,
        "stats": stats
    }

# Получение истории действий администраторов
@router.get("/admin/actions")
async def get_admin_actions(target_admin_id: Optional[int] = None, limit: int = 50):
    # Проверяем структуру таблицы admin_actions
    await ensure_admin_actions_table()

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Определяем структуру таблицы
            cursor = await db.execute("PRAGMA table_info(admin_actions)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            # Определяем название колонки для действия - action или description
            action_column = "action" if "action" in column_names else "description"

            # Формируем запрос
            if target_admin_id:
                cursor = await db.execute(
                    f"SELECT admin_id, {action_column}, timestamp FROM admin_actions WHERE admin_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (target_admin_id, limit)
                )
            else:
                cursor = await db.execute(
                    f"SELECT admin_id, {action_column}, timestamp FROM admin_actions ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )

            rows = await cursor.fetchall()
            actions = []

            for row in rows:
                actions.append({
                    "admin_id": row[0],
                    "action": row[1],
                    "timestamp": row[2]
                })

            return {
                "success": True,
                "actions": actions
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Игра "Угадай число" - получение статуса
@router.get("/guess_game/{user_id}")
async def get_guess_game_status(user_id: int):
    # Проверяем существование пользователя
    user = await validate_user(user_id)

    # Получаем количество оставшихся попыток
    attempts_left = await db.get_guess_game_attempts_left(user_id)

    return {
        "attempts_left": attempts_left,
        "max_attempts": config.GUESS_GAME_MAX_ATTEMPTS
    }

# Игра "Угадай число" - игра
@router.post("/guess_game/play")
async def play_guess_game(
    user_id: int = Form(...),
    guess: int = Form(...)
):
    # Проверяем существование пользователя
    user = await validate_user(user_id)

    # Проверяем, что число в правильном диапазоне
    if guess < 1 or guess > 10:
        raise HTTPException(status_code=400, detail="Число должно быть от 1 до 10")

    # Получаем количество оставшихся попыток
    attempts_left = await db.get_guess_game_attempts_left(user_id)

    if attempts_left <= 0:
        raise HTTPException(status_code=400, detail="У вас не осталось попыток на сегодня")

    # Играем
    try:
        result = await db.play_guess_game(user_id, guess)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Игра "Кубик" - получение статуса
@router.get("/games/dice/attempts/{user_id}")
async def get_dice_game_attempts(user_id: int):
    # Проверяем существование пользователя
    user = await validate_user(user_id)

    # Получаем количество оставшихся попыток
    attempts_left = await db.get_dice_game_attempts_left(user_id)

    return {
        "attempts_left": attempts_left,
        "max_attempts": config.DICE_GAME_MAX_ATTEMPTS
    }

# Игра "Кубик" - бросок кубика
@router.post("/games/dice/play/{user_id}")
async def play_dice_game(user_id: int):
    # Проверяем существование пользователя
    user = await validate_user(user_id)

    # Получаем количество оставшихся попыток
    attempts_left = await db.get_dice_game_attempts_left(user_id)

    if attempts_left <= 0:
        raise HTTPException(status_code=400, detail="У вас не осталось попыток на сегодня")

    # Играем
    try:
        result = await db.play_dice_game(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Поиск пользователей по запросу (для админки)
@router.get("/admin/search_users")
async def search_users(q: str):
    # Проверяем, что запрос не пустой
    if not q:
        return {"success": False, "error": "Запрос не может быть пустым"}

    try:
        # Ищем пользователей по ID, имени или username
        users = await db.search_users(q)
        return {
            "success": True,
            "users": users
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Получение детальной информации о пользователе (для админки)
@router.get("/admin/user")
async def get_user_details(id: int):
    try:
        user = await db.get_user(id)
        if not user:
            return {"success": False, "error": "Пользователь не найден"}

        return {
            "success": True,
            "user": user
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Получение транзакций пользователя (для админки)
@router.get("/admin/user_transactions")
async def get_user_transactions(id: int, limit: int = 10):
    try:
        transactions = await db.get_transactions(id, limit)

        return {
            "success": True,
            "transactions": transactions
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Проверка существования пользователя по ID
async def user_exists_by_id(user_id: int) -> bool:
    """
    Проверка существования пользователя по ID
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row is not None