import os
import sys
import time
import json
import requests
from PyQt6.QtCore import (Qt, QSize, QTimer, QPropertyAnimation, 
                          QEasingCurve, QThread, pyqtSignal, QRect,
                          QRegularExpression)
from PyQt6.QtGui import (QFont, QIcon, QPixmap, QColor, QPalette, 
                         QLinearGradient, QBrush, QPainter, QFontDatabase,
                         QRegularExpressionValidator)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                            QStackedWidget, QScrollArea, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QFrame, 
                            QDialog, QGraphicsDropShadowEffect, QSizePolicy)

# Константы стилей - изменяем на темную тему с оранжевыми акцентами
COLORS = {
    "primary": "#FF8C00",  # Оранжевый основной
    "primary_dark": "#E67300",  # Темно-оранжевый
    "accent": "#FFA726",   # Светло-оранжевый
    "background": "#121212",  # Темный фон
    "card": "#1E1E1E",     # Темные карточки
    "text_primary": "#FFFFFF",  # Белый текст
    "text_secondary": "#B0B0B0",  # Серый текст
    "error": "#FF5252",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "info": "#2196F3",
}

# Стили кнопок
BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS["primary"]};
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 20px;
    font-size: 16px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {COLORS["primary_dark"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["primary_dark"]};
}}

QPushButton:disabled {{
    background-color: #555555;
}}
"""

# Стили карточек
CARD_STYLE = f"""
QFrame {{
    background-color: {COLORS["card"]};
    border-radius: 16px;
    padding: 20px;
    border: 1px solid #333333;
}}
"""

# Стили для текстовых полей
INPUT_STYLE = f"""
QLineEdit {{
    border: 2px solid #444444;
    border-radius: 12px;
    padding: 12px 16px;
    background-color: #2A2A2A;
    font-size: 16px;
    color: {COLORS["text_primary"]};
}}

QLineEdit:focus {{
    border: 2px solid {COLORS["primary"]};
}}
"""

class LoadingThread(QThread):
    """Поток для выполнения длительных операций в фоне"""
    finished = pyqtSignal(object)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        result = self.func(*self.args, **self.kwargs)
        self.finished.emit(result)

class LoadingScreen(QWidget):
    """Полноэкранный экран загрузки вместо диалога"""
    def __init__(self, message="Загрузка...", parent=None):
        super().__init__(parent)
        
        # Настраиваем внешний вид
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
        # Компоновка
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем контейнер для центрирования
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        
        # Карточка с информацией о загрузке
        loading_card = CardWidget()
        loading_card_layout = QVBoxLayout(loading_card)
        
        # Анимированный индикатор загрузки
        loading_icon = QLabel()
        loading_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_icon.setStyleSheet(f"color: {COLORS['primary']}; font-size: 48px;")
        loading_icon.setText("⌛")
        loading_card_layout.addWidget(loading_icon)
        
        # Текст загрузки
        self.loading_label = QLabel(message)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 24px; font-weight: bold; margin: 20px 0;")
        loading_card_layout.addWidget(self.loading_label)
        
        # Подсказка о процессе
        loading_hint = QLabel("Пожалуйста, подождите. Операция выполняется...")
        loading_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_hint.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 16px;")
        loading_card_layout.addWidget(loading_hint)
        
        center_layout.addWidget(loading_card)
        
        # Добавляем контейнер в основной макет
        layout.addWidget(center_container, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Анимация точек
        self.dots = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_loading_text)
        self.timer.start(300)  # Обновляем каждые 300 мс
        
        self.base_message = message
        
        # Анимация иконки
        self.icon_timer = QTimer(self)
        self.icon_timer.timeout.connect(self.rotate_icon)
        self.icon_timer.start(100)  # Обновляем каждые 100 мс
        self.icon_rotation = 0
        self.loading_icon = loading_icon
        
    def update_loading_text(self):
        """Обновление текста загрузки для анимации"""
        self.dots = (self.dots + 1) % 4
        dots_text = "." * self.dots
        self.loading_label.setText(f"{self.base_message}{dots_text}")
    
    def rotate_icon(self):
        """Анимация вращения иконки"""
        icons = ["⌛", "⏳"]
        self.icon_rotation = (self.icon_rotation + 1) % len(icons)
        self.loading_icon.setText(icons[self.icon_rotation])
        
    def closeEvent(self, event):
        """Останавливаем таймеры при закрытии"""
        self.timer.stop()
        self.icon_timer.stop()
        super().closeEvent(event)

class NotificationOverlay(QWidget):
    """Оверлей для отображения уведомлений в стиле терминала"""
    def __init__(self, message, notification_type="info", parent=None, duration=3000):
        super().__init__(parent)
        self.parent = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Настраиваем цвет в зависимости от типа уведомления
        if notification_type == "success":
            color = COLORS["success"]
            icon = "✅"
        elif notification_type == "error":
            color = COLORS["error"]
            icon = "❌"
        elif notification_type == "warning":
            color = COLORS["warning"]
            icon = "⚠️"
        else:  # info
            color = COLORS["info"]
            icon = "ℹ️"
        
        # Создаем макет
        layout = QHBoxLayout(self)
        
        # Создаем карточку уведомления
        notification_card = QFrame()
        notification_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-left: 8px solid {color};
                border-radius: 8px;
            }}
        """)
        
        card_layout = QHBoxLayout(notification_card)
        
        # Иконка
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 24px; padding: 5px;")
        card_layout.addWidget(icon_label)
        
        # Сообщение
        message_label = QLabel(message)
        message_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: bold;")
        card_layout.addWidget(message_label)
        
        layout.addWidget(notification_card)
        
        # Размещаем уведомление в нижней части экрана
        self.setMinimumWidth(500)
        self.setMaximumWidth(800)
        
        # Устанавливаем таймер закрытия
        QTimer.singleShot(duration, self.close)
        
    def showEvent(self, event):
        """Позиционирование при показе"""
        if self.parent:
            parent_rect = self.parent.geometry()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.height() - self.height() - 100
            )
        super().showEvent(event)

class CardWidget(QFrame):
    """Виджет карточки с тенью и закругленными углами"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(CARD_STYLE)
        
        # Добавляем тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

class ActionButton(QPushButton):
    """Кнопка с иконкой и текстом"""
    def __init__(self, text, icon_path=None, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(BUTTON_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(24, 24))
            
        # Эффект при наведении и нажатии
        self.setAutoFillBackground(True)
        
        # Анимация нажатия
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(100)
        self._animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
    def mousePressEvent(self, event):
        """Анимация нажатия"""
        if event.button() == Qt.MouseButton.LeftButton:
            original_geometry = self.geometry()
            self._animation.setStartValue(original_geometry)
            new_geometry = QRect(
                original_geometry.x(), 
                original_geometry.y() + 2, 
                original_geometry.width(), 
                original_geometry.height()
            )
            self._animation.setEndValue(new_geometry)
            self._animation.start()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Анимация отпускания"""
        if event.button() == Qt.MouseButton.LeftButton:
            original_geometry = self.geometry()
            self._animation.setStartValue(original_geometry)
            new_geometry = QRect(
                original_geometry.x(), 
                original_geometry.y() - 2, 
                original_geometry.width(), 
                original_geometry.height()
            )
            self._animation.setEndValue(new_geometry)
            self._animation.start()
        super().mouseReleaseEvent(event)

# Временно создаем имитацию API вместо реального
class DemoAPI:
    """Демонстрационная версия API для оффлайн-режима"""
    def __init__(self):
        # Демо-пользователи
        self.users = {
            123456: {
                'user_id': 123456,
                'username': 'Демо-пользователь',
                'balance': 10000  # Начальный баланс для демо
            }
        }
        
        # Демо-транзакции
        self.transactions = {
            123456: [
                {
                    'id': 1,
                    'sender_id': 654321,
                    'receiver_id': 123456,
                    'amount': 5000,
                    'description': 'Пополнение демо-счета',
                    'created_at': '10.03.2024 15:30:22'
                },
                {
                    'id': 2,
                    'sender_id': 123456,
                    'receiver_id': 654321,
                    'amount': 1200,
                    'description': 'Оплата услуг',
                    'created_at': '12.03.2024 09:15:03'
                },
                {
                    'id': 3,
                    'sender_id': 654321,
                    'receiver_id': 123456,
                    'amount': 8000,
                    'description': 'Зачисление средств',
                    'created_at': '15.03.2024 16:45:18'
                }
            ]
        }
    
    def auth_by_id(self, user_id):
        """Имитация авторизации по ID"""
        # Для демо режима возвращаем пользователя с любым ID
        if user_id not in self.users:
            # Создаем нового пользователя с введенным ID
            self.users[user_id] = {
                'user_id': user_id,
                'username': f'Демо-пользователь {user_id}',
                'balance': 10000
            }
            self.transactions[user_id] = self.transactions[123456].copy()
            
        return self.users.get(user_id)
    
    def get_balance(self, user_id):
        """Имитация получения баланса"""
        if user_id in self.users:
            return self.users[user_id]['balance']
        return 0
    
    def add_balance(self, user_id, amount):
        """Имитация пополнения баланса"""
        if user_id in self.users:
            self.users[user_id]['balance'] += amount
            
            # Добавляем запись в историю транзакций
            if user_id not in self.transactions:
                self.transactions[user_id] = []
                
            self.transactions[user_id].append({
                'id': len(self.transactions[user_id]) + 1,
                'sender_id': 654321,  # Демо-отправитель
                'receiver_id': user_id,
                'amount': amount,
                'description': 'Пополнение счета',
                'created_at': time.strftime("%d.%m.%Y %H:%M:%S")
            })
            
            return {
                'success': True,
                'new_balance': self.users[user_id]['balance']
            }
        return {'success': False}
    
    def get_transactions(self, user_id):
        """Имитация получения истории транзакций"""
        return self.transactions.get(user_id, [])

class BankTerminalApp(QMainWindow):
    """Главное окно приложения банковского терминала"""
    def __init__(self):
        super().__init__()
        self.api = DemoAPI()    # Используем демо-API
        self.current_user = None
        self.threads = []  # Список для хранения ссылок на все потоки
        
        # Настройка окна
        self.setWindowTitle("LKNBank - Банковский Терминал (Демо-режим)")
        self.setMinimumSize(1000, 700)
        
        # Настройка стилей и шрифтов
        self.setup_styles()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной контейнер
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Контейнер для контента
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)
        
        # Создаем экраны
        self.setup_login_screen()
        self.setup_main_menu_screen()
        self.setup_balance_screen()
        self.setup_deposit_screen()
        self.setup_transaction_history_screen()
        self.setup_loading_screen()  # Добавляем экран загрузки
        
        # Начинаем с экрана входа
        self.content_stack.setCurrentIndex(0)
        
        # Переходим в полноэкранный режим
        self.showFullScreen()  # Используем полноэкранный режим для терминала
        
    def closeEvent(self, event):
        """Метод перехватывает закрытие окна приложения"""
        # Дожидаемся завершения всех потоков
        for thread in self.threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
        super().closeEvent(event)
        
    def setup_styles(self):
        """Настройка стилей приложения"""
        # Устанавливаем глобальные стили
        app = QApplication.instance()
        app.setStyle("Fusion")
        
        # Настройка цветов приложения для темной темы
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["background"]))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text_primary"]))
        palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["card"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["text_primary"]))
        app.setPalette(palette)
        
        # Настраиваем шрифты
        try:
            QFontDatabase.addApplicationFont(":/fonts/Roboto-Regular.ttf")
            QFontDatabase.addApplicationFont(":/fonts/Roboto-Bold.ttf")
            
            app_font = QFont("Roboto", 10)
            app.setFont(app_font)
        except Exception:
            print("Не удалось загрузить шрифты, используются системные")
        
    def setup_login_screen(self):
        """Настройка экрана входа"""
        login_container = QWidget()
        login_layout = QVBoxLayout(login_container)
        login_layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем фон с градиентом (оранжевые оттенки)
        login_container.setAutoFillBackground(True)
        palette = login_container.palette()
        gradient = QLinearGradient(0, 0, 0, login_container.height())
        gradient.setColorAt(0, QColor("#FF8C00"))  # Оранжевый
        gradient.setColorAt(1, QColor("#E67300"))  # Темно-оранжевый
        palette.setBrush(QPalette.ColorRole.Window, QBrush(gradient))
        login_container.setPalette(palette)
        
        # Центрируем форму входа
        login_form_container = QWidget()
        login_form_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        login_form_layout = QVBoxLayout(login_form_container)
        login_layout.addWidget(login_form_container, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Логотип
        logo_label = QLabel()
        try:
            logo_pixmap = QPixmap(":/images/logo.png")
            if not logo_pixmap.isNull():
                logo_label.setPixmap(logo_pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                # Если изображения нет, используем текст
                logo_label.setText("LKNBank")
                logo_label.setStyleSheet("font-size: 40px; color: white; font-weight: bold;")
        except Exception:
            # Если не удалось загрузить изображение, используем текст
            logo_label.setText("LKNBank")
            logo_label.setStyleSheet("font-size: 40px; color: white; font-weight: bold;")
        
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_form_layout.addWidget(logo_label)
        
        # Заголовок
        title_label = QLabel("Вход в банковский терминал")
        title_label.setStyleSheet("font-size: 24px; color: white; font-weight: bold; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_form_layout.addWidget(title_label)
        
        # Карточка для формы входа
        login_card = CardWidget()
        login_card_layout = QVBoxLayout(login_card)
        login_form_layout.addWidget(login_card)
        
        # Поле ввода Telegram ID
        telegram_id_label = QLabel("Telegram ID")
        telegram_id_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        login_card_layout.addWidget(telegram_id_label)
        
        self.telegram_id_input = QLineEdit()
        self.telegram_id_input.setStyleSheet(INPUT_STYLE)
        self.telegram_id_input.setPlaceholderText("Введите ваш Telegram ID")
        # Валидация для ввода только цифр
        self.telegram_id_input.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d+$")))
        login_card_layout.addWidget(self.telegram_id_input)
        
        # Инструкция по получению Telegram ID
        help_label = QLabel("Как узнать свой Telegram ID? Напишите боту @userinfobot в Telegram")
        help_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; margin-top: 5px;")
        help_label.setWordWrap(True)
        login_card_layout.addWidget(help_label)
        
        # Кнопка входа
        login_button = ActionButton("Войти в систему")
        login_button.clicked.connect(self.login)
        login_card_layout.addWidget(login_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Добавляем экран в стек
        self.content_stack.addWidget(login_container)
    
    def setup_main_menu_screen(self):
        """Настройка экрана главного меню"""
        main_menu_container = QWidget()
        main_menu_layout = QVBoxLayout(main_menu_container)
        main_menu_layout.setContentsMargins(40, 40, 40, 40)
        main_menu_layout.setSpacing(20)
        
        # Верхняя панель
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Логотип и название
        logo_label = QLabel("LKNBank")
        logo_label.setStyleSheet(f"color: {COLORS['primary']}; font-size: 24px; font-weight: bold;")
        top_bar_layout.addWidget(logo_label)
        
        # Информация о пользователе и кнопка выхода
        user_widget = QWidget()
        user_layout = QHBoxLayout(user_widget)
        user_layout.setContentsMargins(0, 0, 0, 0)
        
        self.user_label = QLabel()
        self.user_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 16px;")
        user_layout.addWidget(self.user_label)
        
        logout_button = ActionButton("Выйти")
        logout_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['text_secondary']};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #F5F5F5;
            }}
        """)
        logout_button.clicked.connect(self.logout)
        user_layout.addWidget(logout_button)
        
        top_bar_layout.addWidget(user_widget, 0, Qt.AlignmentFlag.AlignRight)
        main_menu_layout.addWidget(top_bar)
        
        # Карточка с информацией о балансе
        balance_card = CardWidget()
        balance_card.setMinimumHeight(150)
        balance_layout = QVBoxLayout(balance_card)
        
        balance_title = QLabel("Текущий баланс")
        balance_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        balance_layout.addWidget(balance_title)
        
        self.balance_label = QLabel()
        self.balance_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 36px; font-weight: bold;")
        balance_layout.addWidget(self.balance_label)
        
        main_menu_layout.addWidget(balance_card)
        
        # Сетка с кнопками действий - добавляем рекламный блок
        actions_grid = QWidget()
        actions_layout = QHBoxLayout(actions_grid)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(20)
        
        # Карточки для каждого действия
        # 1. Пополнение счета
        deposit_card = CardWidget()
        deposit_layout = QVBoxLayout(deposit_card)
        
        deposit_icon = QLabel()
        deposit_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        deposit_icon.setStyleSheet(f"color: {COLORS['primary']}; font-size: 36px;")
        deposit_icon.setText("💰")
        deposit_layout.addWidget(deposit_icon)
        
        deposit_title = QLabel("Пополнить счет")
        deposit_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        deposit_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: bold;")
        deposit_layout.addWidget(deposit_title)
        
        deposit_desc = QLabel("Пополните свой счет на любую сумму")
        deposit_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        deposit_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        deposit_desc.setWordWrap(True)
        deposit_layout.addWidget(deposit_desc)
        
        deposit_card.mousePressEvent = lambda event: self.content_stack.setCurrentIndex(3)
        deposit_card.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(deposit_card)
        
        # 2. Проверка баланса
        balance_check_card = CardWidget()
        balance_check_layout = QVBoxLayout(balance_check_card)
        
        balance_check_icon = QLabel()
        balance_check_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        balance_check_icon.setStyleSheet(f"color: {COLORS['primary']}; font-size: 36px;")
        balance_check_icon.setText("🔍")
        balance_check_layout.addWidget(balance_check_icon)
        
        balance_check_title = QLabel("Проверить баланс")
        balance_check_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        balance_check_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: bold;")
        balance_check_layout.addWidget(balance_check_title)
        
        balance_check_desc = QLabel("Подробная информация о состоянии счета")
        balance_check_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        balance_check_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        balance_check_desc.setWordWrap(True)
        balance_check_layout.addWidget(balance_check_desc)
        
        balance_check_card.mousePressEvent = lambda event: self.content_stack.setCurrentIndex(2)
        balance_check_card.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(balance_check_card)
        
        # 3. История операций
        history_card = CardWidget()
        history_layout = QVBoxLayout(history_card)
        
        history_icon = QLabel()
        history_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_icon.setStyleSheet(f"color: {COLORS['primary']}; font-size: 36px;")
        history_icon.setText("📊")
        history_layout.addWidget(history_icon)
        
        history_title = QLabel("История операций")
        history_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: bold;")
        history_layout.addWidget(history_title)
        
        history_desc = QLabel("Просмотр всех транзакций по вашему счету")
        history_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        history_desc.setWordWrap(True)
        history_layout.addWidget(history_desc)
        
        history_card.mousePressEvent = lambda event: self.content_stack.setCurrentIndex(4)
        history_card.setCursor(Qt.CursorShape.PointingHandCursor)
        actions_layout.addWidget(history_card)
        
        # 4. Рекламные предложения (Отключено в демо-режиме)
        ad_card = CardWidget()
        ad_layout = QVBoxLayout(ad_card)
        
        ad_icon = QLabel()
        ad_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ad_icon.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 36px;")  # Серый цвет для неактивной функции
        ad_icon.setText("🎁")
        ad_layout.addWidget(ad_icon)
        
        ad_title = QLabel("Спецпредложения")
        ad_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ad_title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px; font-weight: bold;")
        ad_layout.addWidget(ad_title)
        
        ad_desc = QLabel("Временно недоступно в демо-режиме")
        ad_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ad_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        ad_desc.setWordWrap(True)
        ad_layout.addWidget(ad_desc)
        
        # Не добавляем обработчик нажатия, чтобы карточка была неактивной
        actions_layout.addWidget(ad_card)
        
        main_menu_layout.addWidget(actions_grid)
        main_menu_layout.addStretch()
        
        # Добавляем экран в стек
        self.content_stack.addWidget(main_menu_container)
        
    def setup_balance_screen(self):
        """Настройка экрана проверки баланса"""
        balance_container = QWidget()
        balance_layout = QVBoxLayout(balance_container)
        balance_layout.setContentsMargins(40, 40, 40, 40)
        balance_layout.setSpacing(20)
        
        # Верхняя панель с кнопкой назад
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        back_button = ActionButton("← Назад")
        back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['primary']};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 0;
            }}
            QPushButton:hover {{
                color: {COLORS['primary_dark']};
            }}
        """)
        back_button.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
        top_bar_layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignLeft)
        
        balance_title = QLabel("Проверка баланса")
        balance_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 24px; font-weight: bold;")
        balance_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar_layout.addWidget(balance_title)
        
        # Добавляем пустой виджет для выравнивания
        empty_widget = QWidget()
        empty_widget.setFixedWidth(back_button.sizeHint().width())
        top_bar_layout.addWidget(empty_widget)
        
        balance_layout.addWidget(top_bar)
        
        # Основная карточка с информацией о балансе
        balance_info_card = CardWidget()
        balance_info_layout = QVBoxLayout(balance_info_card)
        
        # Иконка
        balance_icon = QLabel()
        balance_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        balance_icon.setStyleSheet(f"color: {COLORS['primary']}; font-size: 48px;")
        balance_icon.setText("💵")
        balance_info_layout.addWidget(balance_icon)
        
        # Текущий баланс (крупно)
        self.detailed_balance_label = QLabel()
        self.detailed_balance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detailed_balance_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 48px; font-weight: bold;")
        balance_info_layout.addWidget(self.detailed_balance_label)
        
        # Дополнительная информация
        balance_info = QLabel("Доступно для использования")
        balance_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        balance_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        balance_info_layout.addWidget(balance_info)
        
        # Дата последнего обновления
        self.update_time_label = QLabel()
        self.update_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_time_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px; margin-top: 20px;")
        balance_info_layout.addWidget(self.update_time_label)
        
        balance_layout.addWidget(balance_info_card)
        
        # Кнопка обновления баланса
        refresh_button = ActionButton("Обновить информацию")
        refresh_button.clicked.connect(self.refresh_balance)
        balance_layout.addWidget(refresh_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        balance_layout.addStretch()
        
        # Добавляем экран в стек
        self.content_stack.addWidget(balance_container)
        
    def setup_deposit_screen(self):
        """Настройка экрана пополнения счета"""
        deposit_container = QWidget()
        deposit_layout = QVBoxLayout(deposit_container)
        deposit_layout.setContentsMargins(40, 40, 40, 40)
        deposit_layout.setSpacing(20)
        
        # Верхняя панель с кнопкой назад
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        back_button = ActionButton("← Назад")
        back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['primary']};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 0;
            }}
            QPushButton:hover {{
                color: {COLORS['primary_dark']};
            }}
        """)
        back_button.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
        top_bar_layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignLeft)
        
        deposit_title = QLabel("Пополнение счета")
        deposit_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 24px; font-weight: bold;")
        deposit_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar_layout.addWidget(deposit_title)
        
        # Добавляем пустой виджет для выравнивания
        empty_widget = QWidget()
        empty_widget.setFixedWidth(back_button.sizeHint().width())
        top_bar_layout.addWidget(empty_widget)
        
        deposit_layout.addWidget(top_bar)
        
        # Карточка для формы пополнения
        deposit_form_card = CardWidget()
        deposit_form_layout = QVBoxLayout(deposit_form_card)
        
        # Иконка
        deposit_icon = QLabel()
        deposit_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        deposit_icon.setStyleSheet(f"color: {COLORS['primary']}; font-size: 48px;")
        deposit_icon.setText("💰")
        deposit_form_layout.addWidget(deposit_icon)
        
        # Заголовок
        deposit_form_title = QLabel("Введите сумму для пополнения")
        deposit_form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        deposit_form_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 20px; font-weight: bold;")
        deposit_form_layout.addWidget(deposit_form_title)
        
        # Поле ввода суммы
        self.deposit_amount_input = QLineEdit()
        self.deposit_amount_input.setStyleSheet(INPUT_STYLE)
        self.deposit_amount_input.setPlaceholderText("Введите сумму")
        self.deposit_amount_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Валидация на ввод только цифр и точки
        self.deposit_amount_input.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d*\.?\d*$")))
        self.deposit_amount_input.textChanged.connect(self.validate_deposit_amount)
        
        deposit_form_layout.addWidget(self.deposit_amount_input)
        
        # Текущий баланс для информации
        self.current_balance_info = QLabel()
        self.current_balance_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_balance_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 16px;")
        deposit_form_layout.addWidget(self.current_balance_info)
        
        # Кнопка пополнения
        self.deposit_button = ActionButton("Пополнить счет")
        self.deposit_button.clicked.connect(self.make_deposit)
        self.deposit_button.setEnabled(False)  # Изначально отключена
        deposit_form_layout.addWidget(self.deposit_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        deposit_layout.addWidget(deposit_form_card)
        deposit_layout.addStretch()
        
        # Добавляем экран в стек
        self.content_stack.addWidget(deposit_container)
        
    def setup_transaction_history_screen(self):
        """Настройка экрана истории транзакций"""
        history_container = QWidget()
        history_layout = QVBoxLayout(history_container)
        history_layout.setContentsMargins(40, 40, 40, 40)
        history_layout.setSpacing(20)
        
        # Верхняя панель с кнопкой назад
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        back_button = ActionButton("← Назад")
        back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['primary']};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 0;
            }}
            QPushButton:hover {{
                color: {COLORS['primary_dark']};
            }}
        """)
        back_button.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
        top_bar_layout.addWidget(back_button, 0, Qt.AlignmentFlag.AlignLeft)
        
        history_title = QLabel("История операций")
        history_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 24px; font-weight: bold;")
        history_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar_layout.addWidget(history_title)
        
        # Добавляем пустой виджет для выравнивания
        empty_widget = QWidget()
        empty_widget.setFixedWidth(back_button.sizeHint().width())
        top_bar_layout.addWidget(empty_widget)
        
        history_layout.addWidget(top_bar)
        
        # Карточка с таблицей истории
        history_card = CardWidget()
        history_card_layout = QVBoxLayout(history_card)
        
        # Создаем таблицу для истории транзакций
        self.transaction_table = QTableWidget()
        self.transaction_table.setColumnCount(4)
        self.transaction_table.setHorizontalHeaderLabels(["Тип", "Сумма", "Описание", "Дата и время"])
        
        # Настраиваем заголовки таблицы
        self.transaction_table.horizontalHeader().setStyleSheet(f"font-weight: bold; color: {COLORS['text_primary']};")
        self.transaction_table.verticalHeader().setVisible(False)
        self.transaction_table.setShowGrid(False)
        self.transaction_table.setAlternatingRowColors(True)
        self.transaction_table.setStyleSheet(f"""
            QTableWidget {{
                border: none;
                background-color: {COLORS['card']};
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid #EEEEEE;
            }}
            QTableWidget::item:alternate {{
                background-color: #F9F9F9;
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                padding: 10px;
                border: none;
                border-bottom: 2px solid #EEEEEE;
            }}
        """)
        
        # Растягиваем колонки
        header = self.transaction_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        history_card_layout.addWidget(self.transaction_table)
        
        # Сообщение при отсутствии транзакций
        self.no_transactions_label = QLabel("История операций пуста")
        self.no_transactions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_transactions_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 18px;")
        self.no_transactions_label.setVisible(False)
        history_card_layout.addWidget(self.no_transactions_label)
        
        history_layout.addWidget(history_card)
        
        # Кнопка обновления истории
        refresh_button = ActionButton("Обновить историю")
        refresh_button.clicked.connect(self.load_transactions)
        history_layout.addWidget(refresh_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Добавляем экран в стек
        self.content_stack.addWidget(history_container)
    
    def setup_loading_screen(self):
        """Настройка экрана загрузки"""
        self.loading_screen = LoadingScreen()
        self.content_stack.addWidget(self.loading_screen)
    
    def login(self):
        """Обработка входа в систему"""
        telegram_id = self.telegram_id_input.text().strip()
        
        if not telegram_id:
            self.show_notification("Введите любой ID для демо-режима", "info")
            return
        
        try:
            # Преобразуем ID в число
            user_id = int(telegram_id)
            
            # Показываем экран загрузки
            self.loading_screen.base_message = "Вход в систему"
            self.loading_screen.loading_label.setText("Вход в систему")
            self.content_stack.setCurrentWidget(self.loading_screen)
            
            # Имитируем задержку для демонстрации
            time.sleep(1)
            
            # Выполняем авторизацию
            user = self.api.auth_by_id(user_id)
            self.process_login_result(user)
            
        except ValueError:
            self.show_notification("ID должен быть числом", "error")
    
    def process_login_result(self, user):
        """Обработка результата аутентификации"""
        if user:
            self.current_user = user
            self.user_label.setText(f"Привет, {user.get('username', 'Пользователь')}!")
            self.load_user_data()
            self.content_stack.setCurrentIndex(1)  # Переходим к главному меню
            self.show_notification("Вход выполнен успешно", "success")
        else:
            self.content_stack.setCurrentIndex(0)  # Возвращаемся на экран логина
            self.show_notification("Пользователь не найден", "error")
            
    def load_user_data(self):
        """Загрузка данных пользователя"""
        if not self.current_user:
            return
            
        # Загружаем баланс
        self.refresh_balance()
        
        # Загружаем историю транзакций
        self.load_transactions()
        
    def refresh_balance(self):
        """Обновление баланса пользователя"""
        if not self.current_user:
            return
            
        # Показываем экран загрузки
        self.loading_screen.base_message = "Получение баланса"
        self.loading_screen.loading_label.setText("Получение баланса")
        self.content_stack.setCurrentWidget(self.loading_screen)
        
        # Выполняем запрос в отдельном потоке
        balance_thread = LoadingThread(self.api.get_balance, self.current_user['user_id'])
        balance_thread.finished.connect(self.update_balance_display)
        balance_thread.start()
        
        # Сохраняем ссылку на поток
        self.threads.append(balance_thread)
        
    def update_balance_display(self, balance):
        """Обновление отображения баланса"""
        # Возвращаемся на предыдущий экран
        self.content_stack.setCurrentIndex(2)  # Экран баланса
            
        # Форматируем баланс для отображения
        formatted_balance = f"{balance} ₽"
        
        # Обновляем все метки с балансом
        self.balance_label.setText(formatted_balance)
        self.detailed_balance_label.setText(formatted_balance)
        self.current_balance_info.setText(f"Текущий баланс: {formatted_balance}")
        
        # Обновляем время последнего обновления
        current_time = time.strftime("%d.%m.%Y %H:%M:%S")
        self.update_time_label.setText(f"Последнее обновление: {current_time}")
    
    def validate_deposit_amount(self):
        """Валидация введенной суммы пополнения"""
        amount_text = self.deposit_amount_input.text().strip()
        
        if amount_text and float(amount_text or 0) > 0:
            self.deposit_button.setEnabled(True)
        else:
            self.deposit_button.setEnabled(False)
            
    def make_deposit(self):
        """Выполнение операции пополнения счета"""
        if not self.current_user:
            return
            
        amount_text = self.deposit_amount_input.text().strip()
        
        try:
            amount = int(float(amount_text))
            if amount <= 0:
                self.show_notification("Сумма должна быть положительной", "error")
                return
                
            # Показываем экран загрузки
            self.loading_screen.base_message = "Пополнение счета"
            self.loading_screen.loading_label.setText("Пополнение счета")
            self.content_stack.setCurrentWidget(self.loading_screen)
            
            # Выполняем запрос в отдельном потоке
            deposit_thread = LoadingThread(
                self.api.add_balance, 
                self.current_user['user_id'], 
                amount
            )
            deposit_thread.finished.connect(
                lambda result: self.process_deposit_result(result, amount)
            )
            deposit_thread.start()
            
            # Сохраняем ссылку на поток
            self.threads.append(deposit_thread)
            
        except ValueError:
            self.show_notification("Введите корректную сумму", "error")
            
    def process_deposit_result(self, result, amount):
        """Обработка результата операции пополнения"""
        # Возвращаемся на экран пополнения
        self.content_stack.setCurrentIndex(3)
        
        if result and result.get('success', False):
            new_balance = result.get('new_balance', 0)
            
            # Форматируем баланс для отображения
            formatted_balance = f"{new_balance} ₽"
            
            # Обновляем все метки с балансом
            self.balance_label.setText(formatted_balance)
            self.detailed_balance_label.setText(formatted_balance)
            self.current_balance_info.setText(f"Текущий баланс: {formatted_balance}")
            
            self.deposit_amount_input.clear()
            self.show_notification(f"Счет успешно пополнен на {amount} ₽", "success")
        else:
            self.show_notification("Не удалось пополнить счет", "error")
            
    def load_transactions(self):
        """Загрузка истории транзакций"""
        if not self.current_user:
            return
            
        # Показываем экран загрузки
        self.loading_screen.base_message = "Загрузка истории"
        self.loading_screen.loading_label.setText("Загрузка истории")
        self.content_stack.setCurrentWidget(self.loading_screen)
        
        # Выполняем запрос в отдельном потоке
        transactions_thread = LoadingThread(
            self.api.get_transactions, 
            self.current_user['user_id']
        )
        transactions_thread.finished.connect(self.display_transactions)
        transactions_thread.start()
        
        # Сохраняем ссылку на поток
        self.threads.append(transactions_thread)
        
    def display_transactions(self, transactions):
        """Отображение истории транзакций"""
        # Возвращаемся на экран истории транзакций
        self.content_stack.setCurrentIndex(4)
            
        # Очищаем таблицу
        self.transaction_table.setRowCount(0)
        
        if not transactions:
            self.transaction_table.setVisible(False)
            self.no_transactions_label.setVisible(True)
            return
            
        self.transaction_table.setVisible(True)
        self.no_transactions_label.setVisible(False)
        
        # Заполняем таблицу данными
        for row, trans in enumerate(transactions):
            self.transaction_table.insertRow(row)
            
            # Определяем тип транзакции по направлению
            if trans.get('sender_id') == self.current_user['user_id']:
                trans_type = "➖ Расход"
                amount = f"-{trans.get('amount', 0)} ₽"
                amount_color = COLORS['error']
            else:
                trans_type = "➕ Приход"
                amount = f"+{trans.get('amount', 0)} ₽"
                amount_color = COLORS['success']
                
            # Добавляем ячейки
            type_item = QTableWidgetItem(trans_type)
            amount_item = QTableWidgetItem(amount)
            description_item = QTableWidgetItem(trans.get('description', 'Нет описания'))
            date_item = QTableWidgetItem(trans.get('created_at', 'Неизвестно'))
            
            # Устанавливаем цвет для суммы
            amount_item.setForeground(QColor(amount_color))
            
            # Запрещаем редактирование
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            amount_item.setFlags(amount_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            description_item.setFlags(description_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Устанавливаем ячейки в таблицу
            self.transaction_table.setItem(row, 0, type_item)
            self.transaction_table.setItem(row, 1, amount_item)
            self.transaction_table.setItem(row, 2, description_item)
            self.transaction_table.setItem(row, 3, date_item)
            
        # Подгоняем размеры колонок
        self.transaction_table.resizeColumnsToContents()
        
    def logout(self):
        """Выход из учетной записи"""
        self.current_user = None
        self.telegram_id_input.clear()
        self.content_stack.setCurrentIndex(0)
        self.show_notification("Выход выполнен успешно", "info")
        
    def show_notification(self, message, notification_type="info"):
        """Показывает уведомление пользователю в стиле терминала"""
        notification = NotificationOverlay(message, notification_type, self)
        notification.show()

# Запуск приложения
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BankTerminalApp()
    window.show()
    sys.exit(app.exec())