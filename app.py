import os
import time
import requests
import json
from typing import Dict, Any, Optional

# Константы
API_BASE_URL = "https://lknbank.live/api"

class BankAPI:
    """Класс для взаимодействия с API банка"""
    
    def __init__(self, base_url=API_BASE_URL):
        self.base_url = base_url
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Базовый метод для выполнения запросов к API"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            if method.lower() == 'get':
                response = requests.get(url, params=params)
            elif method.lower() == 'post':
                response = requests.post(url, data=data)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")
                
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Ошибка API: {e}")
            return None
    
    def get_user(self, user_id):
        """Получение данных пользователя"""
        return self._make_request('get', f"user/{user_id}")
    
    def auth(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Авторизация пользователя по имени пользователя (устаревший метод)"""
        try:
            # Для совместимости со старым кодом
            # Этот метод находит пользователя по имени пользователя
            response = requests.get(f"{self.base_url}/user-by-username/{username}")
            
            if response.status_code == 200:
                user_data = response.json()
                return user_data
            return None
        except Exception as e:
            print(f"Ошибка авторизации: {e}")
            return None
    
    def auth_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Авторизация пользователя по Telegram ID"""
        try:
            # Создаем данные формы для отправки
            form_data = {'user_id': user_id}
            
            # Отправляем POST запрос на авторизацию
            response = requests.post(f"{self.base_url}/auth", data=form_data)
            
            if response.status_code == 200:
                user_data = response.json()
                return user_data
            return None
        except Exception as e:
            print(f"Ошибка авторизации: {e}")
            return None
    
    def get_balance(self, user_id: int) -> float:
        """Получение баланса пользователя"""
        try:
            response = requests.get(f"{self.base_url}/balance/{user_id}")
            
            if response.status_code == 200:
                balance_data = response.json()
                return balance_data.get("balance", 0)
            return 0
        except Exception as e:
            print(f"Ошибка получения баланса: {e}")
            return 0
    
    def add_balance(self, user_id, amount):
        """Пополнение баланса пользователя"""
        data = {
            'user_id': str(user_id),
            'amount': int(amount),
            'description': 'Пополнение через терминал'
        }
        return self._make_request('post', "admin/add_balance", data=data)
    
    def get_transactions(self, user_id, limit=10):
        """Получение истории транзакций пользователя"""
        params = {'limit': limit}
        result = self._make_request('get', f"transactions/{user_id}", params=params)
        return result if result else []
