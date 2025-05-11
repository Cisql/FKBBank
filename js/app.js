// Telegram WebApp и основные переменные
document.addEventListener('DOMContentLoaded', function() {
    // Проверка наличия основных элементов UI
    const appContainer = document.getElementById('app');
    if (!appContainer) {
        console.error('Критическая ошибка: не найден контейнер приложения #app');
        alert('Ошибка инициализации приложения. Пожалуйста, обновите страницу.');
        return;
    }

    // Основные переменные
    const tg = window.Telegram.WebApp;
    const colorScheme = tg.colorScheme || 'dark';
    
    // Проверяем наличие основных страниц
    const mainPage = document.getElementById('homePage');
    const transferPage = document.getElementById('sendPage');
    const promoPage = document.getElementById('promoPage');
    const topPage = document.getElementById('topPage');
    const gamesPage = document.getElementById('gamesPage');
    const guessGamePage = document.getElementById('guessGamePage');
    const dicePage = document.getElementById('dicePage');
    
    if (!mainPage) {
        console.error('Критическая ошибка: не найдена главная страница #homePage');
        alert('Ошибка инициализации приложения. Пожалуйста, обновите страницу.');
        return;
    }
    
    let currentPage = mainPage;
    
    // Стили и цвета
    const colors = {
        primary: '#F7A14C',
        secondary: '#FF9500',
        success: '#34C759',
        error: '#FF3B30',
        systemGray: '#8A8A8D',
        systemGray2: '#636366',
        systemGray3: '#48484A',
        systemGray4: '#3A3A3C',
        systemGray5: '#2C2C2E',
        systemGray6: '#1C1C1E'
    };
    
    // Применяем цвета на основе переменных CSS
    document.documentElement.style.setProperty('--primary-color', colors.primary);
    document.documentElement.style.setProperty('--primary-dark', '#E87E0C');
    document.documentElement.style.setProperty('--secondary-color', colors.secondary);
    document.documentElement.style.setProperty('--system-gray', colors.systemGray);
    document.documentElement.style.setProperty('--system-gray3', colors.systemGray3);
    document.documentElement.style.setProperty('--system-gray4', colors.systemGray4);
    document.documentElement.style.setProperty('--system-gray5', colors.systemGray5);
    document.documentElement.style.setProperty('--system-gray6', colors.systemGray6);
    
    // Инициализация Telegram WebApp
    try {
        console.log('Инициализация Telegram WebApp...');
        tg.expand();
        tg.enableClosingConfirmation();
        console.log('Telegram WebApp инициализирован успешно');
    } catch (e) {
        console.error('Ошибка при инициализации Telegram WebApp:', e);
        // Продолжаем работу даже при ошибке инициализации WebApp
    }
    
    // Элементы UI
    const loader = document.querySelector('.loader-container');
    const notificationContainer = document.querySelector('.notification-container') || document.getElementById('notificationContainer');
    
    // Табы и кнопки навигации (используем текущие селекторы из HTML)
    const mainTab = document.getElementById('homeNavButton');
    const transferTab = document.getElementById('sendButton');
    const promoTab = document.getElementById('promoButton');
    
    if (!mainTab || !transferTab || !promoTab) {
        console.warn('Предупреждение: некоторые навигационные кнопки не найдены');
    }
    
    const backButtons = document.querySelectorAll('.back-button');
    const transferForm = document.getElementById('transferForm');
    const promoForm = document.getElementById('promoForm');
    
    // Сегментированный контрол
    const idSegment = document.getElementById('transferByIdBtn');
    const usernameSegment = document.getElementById('transferByUsernameBtn');
    let transferMode = 'id'; // Режим по умолчанию
    
    // API и данные пользователя
    const apiUrl = window.location.origin + '/api';
    let currentUser = null;
    let isBlocked = false;
    let transactions = [];
    let leaderboard = [];
    
    // Добавляем флаг для отслеживания анимации
    let isPageTransitionInProgress = false;
    
    // Инициализация приложения
    try {
        console.log('Запуск инициализации приложения');
        initApp();
    } catch (error) {
        console.error('Критическая ошибка при запуске приложения:', error);
        hideLoader();
        
        // В случае критической ошибки показываем хотя бы главную страницу
        if (mainPage) {
            mainPage.classList.add('active');
        }
        
        // Информируем пользователя
        if (notificationContainer) {
            showNotification('Произошла ошибка при загрузке. Пожалуйста, обновите страницу.', 'error');
        } else {
            alert('Произошла ошибка при загрузке. Пожалуйста, обновите страницу.');
        }
    }
    
    // Основные функции
    async function initApp() {
        console.log('Инициализация приложения начата');
        try {
            if (mainTab) mainTab.classList.add('active');
            
            // Сначала скрываем все страницы
            document.querySelectorAll('.page').forEach(page => {
                page.style.display = 'none';
                page.classList.remove('active', 'slide-left');
            });
            
            // Сначала показываем основную страницу, чтобы она была видна
            if (mainPage) {
                console.log('Активация главной страницы');
                mainPage.style.display = 'block';
                mainPage.classList.add('active');
                document.body.style.overflow = 'auto'; // Разрешаем прокрутку
            }
            
            console.log('Запуск аутентификации пользователя');
            await authenticateUser();
            
            if (!isBlocked) {
                try {
                    console.log('Загрузка данных транзакций и лидерборда');
                    await Promise.all([loadTransactions(), fetchLeaderboard()]);
                } catch (e) {
                    console.error('Ошибка загрузки данных:', e);
                    // Продолжаем работу даже при ошибке загрузки данных
                }
            }
            
            // Скрываем loader только после того, как страница готова
            console.log('Скрытие загрузчика');
            hideLoader();
            
            console.log('Настройка обработчиков событий');
            setupEventListeners();
            
            console.log('Инициализация приложения завершена успешно');
        } catch (error) {
            console.error('Ошибка инициализации:', error);
            showNotification('Произошла ошибка при загрузке приложения', 'error');
            
            // Даже при ошибке скрываем loader и показываем главную страницу
            if (mainPage) {
                mainPage.classList.add('active');
                document.body.style.overflow = 'auto'; // Разрешаем прокрутку
            }
            hideLoader();
        }
    }
    
    async function authenticateUser() {
        try {
            // Проверка на доступность объекта пользователя от Telegram
            let userId;
            let username = null;
            let firstName = null;
            let lastName = null;

            if (!tg.initDataUnsafe.user) {
                console.error('Telegram user data not available');
                showNotification('Приложение должно быть запущено из Telegram', 'error');
                throw new Error('Telegram user data required');
            } 
            
            userId = tg.initDataUnsafe.user.id;
            username = tg.initDataUnsafe.user.username;
            firstName = tg.initDataUnsafe.user.first_name;
            lastName = tg.initDataUnsafe.user.last_name;
            
            // Создаем FormData для отправки
            const formData = new FormData();
            formData.append('user_id', userId);
            if (username) formData.append('username', username);
            if (firstName) formData.append('first_name', firstName);
            if (lastName) formData.append('last_name', lastName);
            
            const response = await fetch(`${apiUrl}/auth`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка авторизации');
            }
            
            const data = await response.json();
            currentUser = data;
            updateUserInfo();
            
            // Проверяем, заблокирован ли пользователь
            if (currentUser.is_blocked) {
                isBlocked = true;
                showBlockedMessage();
            }
            
            // Загружаем транзакции после успешной авторизации
            await loadTransactions();
        } catch (error) {
            console.error('Ошибка авторизации:', error);
            showNotification('Ошибка авторизации: ' + error.message, 'error');
        }
    }
    
    function showBlockedMessage() {
        showNotification('Ваш аккаунт заблокирован. Обратитесь к администратору.', 'error');
        
        // Дополнительное сообщение с информацией о причине блокировки
        if (currentUser && currentUser.blocked_reason) {
            setTimeout(() => {
                showNotification(`Причина: ${currentUser.blocked_reason}`, 'error');
            }, 1000);
        }
    }
    
    function setupEventListeners() {
        // Настраиваем обработчики событий для элементов UI
        
        // Добавляем функционал для кнопки настроек (шестеренки)
        const menuButton = document.getElementById('menuButton');
        if (menuButton) {
            menuButton.addEventListener('click', function() {
                if (isBlocked) return;
                // Показываем меню или настройки
                showNotification('Настройки будут доступны в следующем обновлении', 'success');
            });
        }
        
        // Кнопки действий в главном меню
        if (transferTab) {
            transferTab.addEventListener('click', () => {
                if (isBlocked) {
                    showBlockedMessage();
                    return;
                }
                showPage(transferPage);
            });
        }
        
        if (promoTab) {
            promoTab.addEventListener('click', () => {
                if (isBlocked) {
                    showBlockedMessage();
                    return;
                }
                showPage(promoPage);
            });
        }
        
        // Кнопки навигации
        const homeNavButton = document.getElementById('homeNavButton');
        const topNavButton = document.getElementById('topNavButton');
        const gamesNavButton = document.getElementById('gamesNavButton');
        
        if (homeNavButton) {
            homeNavButton.addEventListener('click', function() {
                if (isBlocked) return;
                
                console.log('Клик на главную кнопку');
                document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Теперь сначала получаем страницу
                const homePage = document.getElementById('homePage');
                if (!homePage) {
                    console.error('Домашняя страница не найдена!');
                    return;
                }
                
                // И только потом вызываем переключение
                showPage(homePage);
            });
        }
        
        if (gamesNavButton) {
            gamesNavButton.addEventListener('click', function() {
                if (isBlocked) return;
                
                console.log('Клик на кнопку игр');
                document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Получаем страницу игр
                const gamesPage = document.getElementById('gamesPage');
                if (!gamesPage) {
                    console.error('Страница игр не найдена!');
                    return;
                }
                
                // Вызываем переключение
                showPage(gamesPage);
            });
        }
        
        if (topNavButton) {
            topNavButton.addEventListener('click', function() {
                if (isBlocked) return;
                
                console.log('Клик на кнопку рейтинга');
                document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Теперь сначала получаем страницу
                const topPage = document.getElementById('topPage');
                if (!topPage) {
                    console.error('Страница рейтинга не найдена!');
                    return;
                }
                
                // И только потом вызываем переключение
                showPage(topPage);
                
                // Обновляем рейтинг при переходе на страницу
                fetchLeaderboard();
            });
        }
        
        // Кнопки назад
        backButtons.forEach(button => {
            button.addEventListener('click', function() {
                if (isBlocked) return;
                
                console.log('Нажата кнопка Назад');
                
                // Получаем главную страницу
                const homePage = document.getElementById('homePage');
                if (!homePage) {
                    console.error('Не найдена главная страница при возврате!');
                    return;
                }
                
                // Переключаемся на главную
                showPage(homePage);
                
                // Обновляем активную вкладку
                const homeNavButton = document.getElementById('homeNavButton');
                const topNavButton = document.getElementById('topNavButton');
                
                if (homeNavButton) homeNavButton.classList.add('active');
                if (topNavButton) topNavButton.classList.remove('active');
            });
        });
        
        // Сегментированный контрол
        if (idSegment && usernameSegment) {
            idSegment.addEventListener('click', function() {
                toggleTransferMode('id');
            });
            
            usernameSegment.addEventListener('click', function() {
                toggleTransferMode('username');
            });
        }
        
        // Формы перевода и промокода
        if (transferForm) {
            transferForm.addEventListener('submit', function(e) {
                e.preventDefault();
                if (isBlocked) {
                    showNotification('Ваш аккаунт заблокирован', 'error');
                    return;
                }
                submitTransfer();
            });
        }
        
        if (promoForm) {
            promoForm.addEventListener('submit', function(e) {
                e.preventDefault();
                if (isBlocked) {
                    showNotification('Ваш аккаунт заблокирован', 'error');
                    return;
                }
                submitPromoCode();
            });
        }
        
        // Другие кнопки
        const cancelTransferButton = document.getElementById('cancelTransferButton');
        if (cancelTransferButton) {
            cancelTransferButton.addEventListener('click', function() {
                if (isBlocked) return;
                showPage(mainPage);
            });
        }
        
        const cancelPromoButton = document.getElementById('cancelPromoButton');
        if (cancelPromoButton) {
            cancelPromoButton.addEventListener('click', function() {
                if (isBlocked) return;
                showPage(mainPage);
            });
        }
        
        // Игра "Угадай число"
        const guessGameButtons = document.querySelectorAll('[data-game="guess-number"]');
        if (guessGameButtons.length > 0) {
            guessGameButtons.forEach(button => {
                button.addEventListener('click', () => {
                    if (isBlocked) {
                        showBlockedMessage();
                        return;
                    }
                    initGuessGame();
                    showPage(guessGamePage);
                });
            });
        }
        
        // Игра "Кубик"
        const diceGameButtons = document.querySelectorAll('[data-game="dice"]');
        if (diceGameButtons.length > 0) {
            diceGameButtons.forEach(button => {
                button.addEventListener('click', () => {
                    if (isBlocked) {
                        showBlockedMessage();
                        return;
                    }
                    initDiceGame();
                    showPage(dicePage);
                });
            });
        }
        
        // Кнопка "Назад" для игры "Угадай число"
        const cancelGuessGameButton = document.getElementById('cancelGuessGameButton');
        if (cancelGuessGameButton) {
            cancelGuessGameButton.addEventListener('click', () => {
                // Возвращаемся на страницу с играми
                showPage(gamesPage);
                
                // Активируем вкладку игр
                const gamesNavButton = document.getElementById('gamesNavButton');
                if (gamesNavButton) {
                    document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
                    gamesNavButton.classList.add('active');
                }
            });
        }
        
        // Кнопка "Назад" для игры "Кубик"
        const cancelDiceButton = document.getElementById('cancelDiceButton');
        if (cancelDiceButton) {
            cancelDiceButton.addEventListener('click', () => {
                // Возвращаемся на страницу с играми
                showPage(gamesPage);
                
                // Активируем вкладку игр
                const gamesNavButton = document.getElementById('gamesNavButton');
                if (gamesNavButton) {
                    document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
                    gamesNavButton.classList.add('active');
                }
            });
        }
        
        // Обработчики для кнопок с числами в игре "Угадай число"
        const numberButtons = document.querySelectorAll('.number-button');
        numberButtons.forEach(button => {
            button.addEventListener('click', () => {
                const number = parseInt(button.getAttribute('data-number'));
                playGuessGame(number);
            });
        });
        
        // Кнопка "Сыграть еще раз"
        const playAgainBtn = document.getElementById('playAgainBtn');
        if (playAgainBtn) {
            playAgainBtn.addEventListener('click', () => {
                resetGuessGameUI();
            });
        }
        
        // Кнопка закрытия блока "Нет попыток"
        const closeNoAttemptsBtn = document.getElementById('closeNoAttemptsBtn');
        if (closeNoAttemptsBtn) {
            closeNoAttemptsBtn.addEventListener('click', () => {
                showPage(mainPage);
            });
        }
        
        // Добавляем поддержку свайпов для iOS-стиля
        setupSwipeNavigation();
    }
    
    function setupSwipeNavigation() {
        let startX, startY;
        let threshold = 100; // минимальное расстояние для считывания свайпа
        let touchStartTime; // время начала касания
        
        document.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            touchStartTime = new Date().getTime();
        }, {passive: true});
        
        document.addEventListener('touchend', function(e) {
            if (!startX || !startY) return;
            
            let endX = e.changedTouches[0].clientX;
            let endY = e.changedTouches[0].clientY;
            
            let diffX = endX - startX;
            let diffY = endY - startY;
            
            // Вычисляем скорость свайпа
            let touchTime = new Date().getTime() - touchStartTime;
            let speed = Math.abs(diffX) / touchTime;
            
            // Если горизонтальное движение больше вертикального и превышает порог
            // или если скорость свайпа достаточно высокая
            if ((Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > threshold) || 
                (Math.abs(diffX) > 50 && speed > 0.5)) {
                
                // Свайп вправо (назад)
                if (diffX > 0 && currentPage !== mainPage) {
                    // Анимация свайпа назад
                    if (backButtons[0]) backButtons[0].click();
                }
                // Свайп влево (для будущего расширения функционала)
                else if (diffX < 0 && currentPage === mainPage) {
                    // Можно добавить переход на другие страницы
                    // Например, на страницу топа
                    if (currentPage === mainPage && topNavButton) {
                        topNavButton.click();
                    }
                }
            }
        }, {passive: true});
    }
    
    function updateUserInfo() {
        if (!currentUser) return;
        
        // Обновляем имя пользователя
        const usernameElement = document.getElementById('username');
        if (usernameElement) {
            usernameElement.textContent = currentUser.username || currentUser.first_name || 'Пользователь';
        }
        
        // Обновляем заголовок с приветствием
        updateGreeting();
        
        // Обновляем баланс с анимацией
        const balanceElement = document.getElementById('balance');
        if (balanceElement) {
            const oldBalance = parseInt(balanceElement.textContent) || 0;
            const newBalance = currentUser.balance;
            
            balanceElement.textContent = `${newBalance}`;
            
            // Добавляем анимацию только если баланс изменился
            if (oldBalance !== newBalance) {
                balanceElement.parentElement.classList.add('updated');
                setTimeout(() => {
                    balanceElement.parentElement.classList.remove('updated');
                }, 500);
            }
        }
        
        // Обновляем статус блокировки
        isBlocked = currentUser.is_blocked === 1;
        if (isBlocked) {
            showBlockedMessage();
        }
        
        // Обновляем видимость элементов в зависимости от статуса блокировки
        const elementsToToggle = document.querySelectorAll('.action-button, .nav-button');
        elementsToToggle.forEach(element => {
            element.style.display = isBlocked ? 'none' : '';
        });
    }
    
    // Функция для обновления приветствия в зависимости от времени суток
    function updateGreeting() {
        const balanceLabel = document.querySelector('.balance-label');
        if (!balanceLabel) return;
        
        const hour = new Date().getHours();
        const username = currentUser.username || currentUser.first_name || 'Пользователь';
        
        let greeting;
        if (hour >= 5 && hour < 12) {
            greeting = `Доброе утро, ${username}`;
        } else if (hour >= 12 && hour < 18) {
            greeting = `Добрый день, ${username}`;
        } else if (hour >= 18 && hour < 23) {
            greeting = `Добрый вечер, ${username}`;
        } else {
            greeting = `Доброй ночи, ${username}`;
        }
        
        balanceLabel.textContent = greeting;
    }
    
    // Транзакции и операции
    async function loadTransactions() {
        try {
            if (!currentUser) {
                throw new Error('Пользователь не авторизован');
            }

            const response = await fetch(`${apiUrl}/transactions/${currentUser.user_id}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Не удалось загрузить транзакции');
            }

            const transactions = await response.json();
            const transactionsList = document.getElementById('transactionsList');
            if (!transactionsList) return;

            transactionsList.innerHTML = '';

            if (transactions.length === 0) {
                transactionsList.innerHTML = `
                    <div class="transaction-card">
                        <div class="transaction-info">
                            <div class="transaction-title">Нет транзакций</div>
                            <div class="transaction-date">-</div>
                        </div>
                        <div class="transaction-amount">-</div>
                    </div>
                `;
                return;
            }

            // Добавляем анимации появления для каждой транзакции
            transactions.forEach((transaction, index) => {
                const transactionElement = document.createElement('div');
                transactionElement.className = 'transaction-card';
                transactionElement.style.opacity = '0';
                transactionElement.style.transform = 'translateY(10px)';
                
                const isIncoming = transaction.receiver_id === currentUser.user_id;
                const amount = isIncoming ? transaction.amount : -transaction.amount;
                const amountClass = isIncoming ? 'positive' : 'negative';
                
                transactionElement.innerHTML = `
                    <div class="transaction-info">
                        <div class="transaction-title">${transaction.description || (isIncoming ? 'Получено' : 'Отправлено')}</div>
                        <div class="transaction-date">${new Date(transaction.created_at).toLocaleString()}</div>
                    </div>
                    <div class="transaction-amount ${amountClass}">${amount > 0 ? '+' : ''}${amount} Ⱡ</div>
                `;
                
                transactionsList.appendChild(transactionElement);
                
                // Анимируем появление с небольшой задержкой для каждой карточки
                setTimeout(() => {
                    transactionElement.style.transition = 'opacity 0.3s ease, transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    transactionElement.style.opacity = '1';
                    transactionElement.style.transform = 'translateY(0)';
                }, 50 + (index * 50)); // Увеличиваем задержку для каждой следующей карточки
            });
        } catch (error) {
            console.error('Ошибка загрузки транзакций:', error);
            showNotification(error.message, 'error');
        }
    }
    
    async function fetchLeaderboard() {
        try {
            const response = await fetch(`${apiUrl}/top`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Не удалось загрузить топ пользователей');
            }

            const data = await response.json();
            leaderboard = data;
            renderLeaderboard();
        } catch (error) {
            console.error('Ошибка загрузки топа:', error);
            showNotification('Не удалось загрузить топ пользователей', 'error');
        }
    }
    
    function renderLeaderboard() {
        const leaderboardList = document.getElementById('topUsersList') || document.querySelector('.leaderboard-list');
        if (!leaderboardList || !leaderboard.length) return;
        
        leaderboardList.innerHTML = '';
        
        // Заполняем список элементами
        leaderboard.forEach((user, index) => {
            const placeClass = index === 0 ? 'first' : index === 1 ? 'second' : index === 2 ? 'third' : '';
            const isCurrentUser = user.user_id === currentUser.user_id;
            
            const card = document.createElement('div');
            card.className = `top-user-card ${placeClass}`;
            
            card.innerHTML = `
                <div class="top-user-left">
                    <div class="place-badge">${index + 1}</div>
                    <div>
                        <div style="display: flex; align-items: center;">
                            <span style="font-weight: 600;">${user.username || `ID: ${user.user_id}`}</span>
                            ${isCurrentUser ? '<span class="current-user-indicator">Вы</span>' : ''}
                        </div>
                        <div style="font-size: 13px; color: var(--system-gray);">${new Intl.NumberFormat('ru-RU').format(user.balance)} Ⱡ</div>
                    </div>
                </div>
            `;
            
            leaderboardList.appendChild(card);
        });
        
        // Добавляем класс для анимации с небольшой задержкой
        setTimeout(() => {
            leaderboardList.classList.add('loaded');
        }, 50);
    }
    
    async function submitTransfer() {
        const recipientInput = document.getElementById('recipient') || document.getElementById('receiverId') || document.getElementById('receiverUsername');
        const amountInput = document.getElementById('amount');
        const reasonInput = document.getElementById('reason') || document.getElementById('description');
        
        if (!recipientInput || !amountInput) {
            showNotification('Ошибка в форме перевода', 'error');
            return;
        }
        
        const recipient = recipientInput.value.trim();
        const amount = parseFloat(amountInput.value);
        const reason = reasonInput ? reasonInput.value.trim() : '';
        
        if (!recipient) {
            showFormError(recipientInput.id, 'Введите ID или имя получателя');
            return;
        }
        
        if (!amount || amount <= 0) {
            showFormError('amount', 'Введите корректную сумму');
            return;
        }
        
        if (amount > currentUser.balance) {
            showFormError('amount', 'Недостаточно средств');
            return;
        }
        
        // Анимация загрузки кнопки
        const submitButton = transferForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        const originalText = submitButton.textContent;
        submitButton.innerHTML = '<div class="loader-circle" style="width: 20px; height: 20px;"></div>';
        
        try {
            // Определяем ID получателя в зависимости от режима
            let receiverId;
            
            if (transferMode === 'username') {
                // Если передаем по юзернейму, сначала делаем запрос для получения ID
                const userResponse = await fetch(`${apiUrl}/find-user-by-username/${recipient}`);
                if (!userResponse.ok) {
                    throw new Error('Пользователь не найден');
                }
                const userData = await userResponse.json();
                receiverId = userData.user_id;
            } else {
                receiverId = parseInt(recipient);
                if (isNaN(receiverId)) {
                    throw new Error('Некорректный ID получателя');
                }
            }
            
            // Создаем FormData для отправки
            const formData = new FormData();
            formData.append('sender_id', currentUser.user_id);
            formData.append('receiver_id', receiverId);
            formData.append('amount', amount);
            if (reason) formData.append('description', reason);
            
            const response = await fetch(`${apiUrl}/transfer`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Не удалось выполнить перевод');
            }
            
            const data = await response.json();
            
            // Обновляем баланс и транзакции
            currentUser = data.user;
            updateUserInfo();
            showNotification('Перевод выполнен успешно!', 'success');
            
            // Сбрасываем форму
            transferForm.reset();
            
            // Добавляем транзакцию в список и обновляем отображение
            await loadTransactions();
        } catch (error) {
            console.error('Ошибка при переводе:', error);
            showNotification(error.message || 'Не удалось выполнить перевод', 'error');
        } finally {
            // Восстанавливаем кнопку
            submitButton.textContent = originalText;
            submitButton.disabled = false;
        }
    }
    
    async function submitPromoCode() {
        const promoInput = document.getElementById('promo-code') || document.getElementById('promoCode');
        
        if (!promoInput) {
            showNotification('Ошибка в форме активации промокода', 'error');
            return;
        }
        
        const promoCode = promoInput.value.trim().toUpperCase();
        
        if (!promoCode) {
            const promoInputContainer = promoInput.closest('.input-container') || promoInput;
            promoInputContainer.classList.add('shake');
            setTimeout(() => promoInputContainer.classList.remove('shake'), 500);
            return;
        }
        
        // Анимация загрузки кнопки
        const submitButton = promoForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        const originalText = submitButton.textContent;
        submitButton.innerHTML = '<div class="loader-circle" style="width: 20px; height: 20px;"></div>';
        
        try {
            // Создаем FormData для отправки
            const formData = new FormData();
            formData.append('user_id', currentUser.user_id);
            formData.append('code', promoCode);
            
            const response = await fetch(`${apiUrl}/promo`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Не удалось активировать промокод');
            }
            
            const data = await response.json();
            
            // Обновляем баланс
            currentUser = data.user;
            updateUserInfo();
            
            // Анимация успешной активации
            const promoInputContainer = promoInput.closest('.input-container') || promoInput;
            promoInputContainer.classList.add('promo-animation', 'success');
            setTimeout(() => promoInputContainer.classList.remove('promo-animation', 'success'), 1000);
            
            showNotification(`Промокод активирован! +${data.amount} Ⱡ`, 'success');
            
            // Сбрасываем форму
            promoForm.reset();
            
            // Обновляем транзакции
            await loadTransactions();
        } catch (error) {
            console.error('Ошибка активации промокода:', error);
            
            const promoInputContainer = promoInput.closest('.input-container') || promoInput;
            promoInputContainer.classList.add('shake');
            setTimeout(() => promoInputContainer.classList.remove('shake'), 500);
            
            showNotification(error.message || 'Не удалось активировать промокод', 'error');
        } finally {
            // Восстанавливаем кнопку
            submitButton.textContent = originalText;
            submitButton.disabled = false;
        }
    }
    
    // UI функции
    function showPage(page) {
        if (!page) {
            console.error('Попытка показать несуществующую страницу');
            return;
        }
        
        if (isBlocked && page !== mainPage) {
            showNotification('Ваш аккаунт заблокирован', 'error');
            return;
        }
        
        // Если анимация уже идет, игнорируем новые запросы
        if (isPageTransitionInProgress) {
            console.log('Анимация переключения страниц уже выполняется');
            return;
        }
        
        console.log('Переключение на страницу:', page.id);
        
        // Если пытаемся перейти на текущую страницу, ничего не делаем
        if (page === currentPage) {
            console.log('Уже на этой странице');
            return;
        }
        
        // Устанавливаем флаг анимации
        isPageTransitionInProgress = true;
        
        // Сохраняем предыдущую страницу
        const prevPage = currentPage;
        
        // Обновляем текущую страницу до вызова анимации
        currentPage = page;
        
        // Предотвращаем прокрутку во время анимации
        document.body.style.overflow = 'hidden';
        
        // Сначала добавляем класс preparing чтобы страница была в DOM, но невидима
        page.classList.add('preparing');
        page.style.display = 'block';
        
        // Даем время браузеру применить класс preparing
        requestAnimationFrame(() => {
            // Форсируем перерисовку для корректной анимации
            void page.offsetWidth;
            
            // Удаляем preparing и добавляем начальное положение для новой страницы
            page.classList.remove('preparing');
            
            // Теперь начинаем анимацию выхода для текущей страницы
            if (prevPage) {
                prevPage.classList.add('slide-left');
            }
            
            // Запускаем анимацию входа для новой страницы с небольшой задержкой
            requestAnimationFrame(() => {
                page.classList.add('active');
                
                // После завершения анимации
                setTimeout(() => {
                    // Если была предыдущая страница, полностью скрываем её
                    if (prevPage) {
                        prevPage.classList.remove('active', 'slide-left');
                        prevPage.style.display = 'none';
                    }
                    
                    // Разрешаем прокрутку снова
                    document.body.style.overflow = 'auto';
                    
                    // Прокручиваем страницу в начало
                    window.scrollTo(0, 0);
                    
                    // Сбрасываем флаг анимации
                    isPageTransitionInProgress = false;
                    
                    console.log('Переключение на страницу завершено:', page.id);
                }, 300); // Время совпадает с длительностью CSS-анимации
            });
        });
    }
    
    function toggleTransferMode(mode) {
        transferMode = mode;
        
        const receiverIdField = document.getElementById('receiverIdField');
        const receiverUsernameField = document.getElementById('receiverUsernameField');
        const recipientInput = document.getElementById('recipient');
        
        // Обновляем UI для старого интерфейса
        if (idSegment && usernameSegment) {
            if (mode === 'id') {
                idSegment.classList.add('active');
                usernameSegment.classList.remove('active');
                
                if (receiverIdField && receiverUsernameField) {
                    // Анимируем переключение полей
                    if (!receiverIdField.classList.contains('hidden')) return;
                    
                    receiverUsernameField.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
                    receiverUsernameField.style.opacity = '0';
                    receiverUsernameField.style.transform = 'translateX(10px)';
                    
                    setTimeout(() => {
                        receiverIdField.classList.remove('hidden');
                        receiverUsernameField.classList.add('hidden');
                        
                        receiverIdField.style.opacity = '0';
                        receiverIdField.style.transform = 'translateX(-10px)';
                        
                        setTimeout(() => {
                            receiverIdField.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                            receiverIdField.style.opacity = '1';
                            receiverIdField.style.transform = 'translateX(0)';
                        }, 10);
                    }, 200);
                }
            } else {
                idSegment.classList.remove('active');
                usernameSegment.classList.add('active');
                
                if (receiverIdField && receiverUsernameField) {
                    // Анимируем переключение полей
                    if (!receiverUsernameField.classList.contains('hidden')) return;
                    
                    receiverIdField.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
                    receiverIdField.style.opacity = '0';
                    receiverIdField.style.transform = 'translateX(-10px)';
                    
                    setTimeout(() => {
                        receiverUsernameField.classList.remove('hidden');
                        receiverIdField.classList.add('hidden');
                        
                        receiverUsernameField.style.opacity = '0';
                        receiverUsernameField.style.transform = 'translateX(10px)';
                        
                        setTimeout(() => {
                            receiverUsernameField.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                            receiverUsernameField.style.opacity = '1';
                            receiverUsernameField.style.transform = 'translateX(0)';
                        }, 10);
                    }, 200);
                }
            }
        }
        
        // Обновляем плейсхолдер для нового интерфейса
        if (recipientInput) {
            recipientInput.placeholder = mode === 'id' ? 'ID получателя' : 'Имя пользователя';
        }
    }
    
    function showFormError(inputId, message) {
        const input = document.getElementById(inputId);
        if (!input) {
            showNotification(message, 'error');
            return;
        }
        
        const container = input.closest('.input-container') || input;
        
        // Анимация ошибки
        container.classList.add('shake');
        setTimeout(() => container.classList.remove('shake'), 500);
        
        // Показываем уведомление
        showNotification(message, 'error');
    }
    
    function showNotification(message, type = 'success') {
        if (!notificationContainer) {
            console.error('Контейнер для уведомлений не найден');
            alert(message);
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Очищаем существующие уведомления того же типа
        const existingNotifications = notificationContainer.querySelectorAll(`.notification.${type}`);
        existingNotifications.forEach(notif => {
            notif.style.opacity = '0';
            setTimeout(() => notif.remove(), 300);
        });
        
        notificationContainer.appendChild(notification);
        
        // Добавляем небольшую задержку перед анимацией для лучшего эффекта
        setTimeout(() => {
            notification.style.animation = 'slideInNotification 0.4s ease-out forwards, fadeOutNotification 0.4s ease-in forwards 3s';
        }, 10);
        
        // Автоматически удаляем уведомление через 3.5 секунды
        setTimeout(() => {
            notification.remove();
        }, 3500);
    }
    
    function hideLoader() {
        const loader = document.querySelector('.loader-container') || document.getElementById('loader');
        if (!loader) {
            console.warn('Предупреждение: не найден элемент загрузчика');
            return;
        }
        
        console.log('Скрытие загрузчика началось');
        loader.classList.add('hidden');
        
        // Добавим таймаут, чтобы предотвратить мерцание
        setTimeout(() => {
            loader.style.display = 'none';
            
            // ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: если ни одна страница не активна, активируем главную
            const anyActive = document.querySelector('.page.active');
            if (!anyActive) {
                console.warn('Ни одна страница не активна после скрытия загрузчика, активируем главную');
                const homePage = document.getElementById('homePage');
                if (homePage) {
                    homePage.style.display = 'block';
                    homePage.classList.add('active');
                }
            }
            
            // Проверяем, что главная страница отображается
            if (mainPage && !mainPage.classList.contains('active')) {
                console.log('Принудительная активация главной страницы');
                mainPage.style.display = 'block';
                mainPage.classList.add('active');
            }
            
            // Убедимся, что содержимое видно
            document.body.style.overflow = 'auto';
            
            // Проверим видимость контента
            const app = document.getElementById('app');
            if (app) {
                app.style.display = 'block';
                app.style.visibility = 'visible';
                app.style.opacity = '1';
            }
            
            console.log('Загрузчик полностью скрыт');
        }, 500);
    }
    
    // Вспомогательные функции
    function getTransactionTitle(transaction, isIncome, isPromo) {
        if (isPromo) {
            return 'Активация промокода';
        } else if (isIncome) {
            return transaction.from_username || `ID: ${transaction.from_id}`;
        } else {
            return transaction.to_username || `ID: ${transaction.to_id}`;
        }
    }
    
    function formatDate(timestamp) {
        const date = new Date(timestamp);
        const options = { 
            day: 'numeric', 
            month: 'short', 
            hour: '2-digit',
            minute: '2-digit'
        };
        return new Intl.DateTimeFormat('ru-RU', options).format(date);
    }
    
    // === Функции игры "Угадай число" === //
    
    // Инициализация игры "Угадай число"
    async function initGuessGame() {
        try {
            const response = await fetch(`${apiUrl}/guess_game/${currentUser.user_id}`);
            if (!response.ok) {
                throw new Error('Ошибка получения статуса игры');
            }
            
            const data = await response.json();
            
            // Обновляем UI с количеством оставшихся попыток
            const attemptsLeftSpan = document.getElementById('attemptsLeft');
            if (attemptsLeftSpan) {
                attemptsLeftSpan.textContent = data.attempts_left;
            }
            
            // Показываем соответствующий блок в зависимости от наличия попыток
            resetGuessGameUI();
            
            if (data.attempts_left <= 0) {
                // Если попыток нет, показываем соответствующее сообщение
                showNoAttemptsBlock();
            }
        } catch (error) {
            console.error('Ошибка инициализации игры:', error);
            showNotification('Не удалось загрузить игру. Попробуйте позже.', 'error');
        }
    }
    
    // Сброс UI игры в начальное состояние
    function resetGuessGameUI() {
        // Скрываем все блоки игры
        document.getElementById('gameResultBlock').classList.add('hidden');
        document.getElementById('gameNoAttemptsBlock').classList.add('hidden');
        
        // Показываем блок выбора числа
        document.getElementById('gameActiveBlock').classList.remove('hidden');
        
        // Сбрасываем состояние результата
        document.getElementById('resultIconSuccess').classList.add('hidden');
        document.getElementById('resultIconFail').classList.add('hidden');
        document.getElementById('revealedNumber').textContent = '?';
        
        // Отключаем кнопку "Играть снова" на время загрузки
        const playAgainBtn = document.getElementById('playAgainBtn');
        if (playAgainBtn) {
            playAgainBtn.disabled = true;
        }
    }
    
    // Показать блок "Нет попыток"
    function showNoAttemptsBlock() {
        document.getElementById('gameActiveBlock').classList.add('hidden');
        document.getElementById('gameResultBlock').classList.add('hidden');
        document.getElementById('gameNoAttemptsBlock').classList.remove('hidden');
    }
    
    // Игровой процесс - отправка выбранного числа
    async function playGuessGame(guess) {
        try {
            // Отключаем все кнопки с числами
            const numberButtons = document.querySelectorAll('.number-button');
            numberButtons.forEach(btn => {
                btn.disabled = true;
                btn.style.opacity = '0.5';
            });
            
            // Подготавливаем данные для отправки
            const formData = new FormData();
            formData.append('user_id', currentUser.user_id);
            formData.append('guess', guess);
            
            const response = await fetch(`${apiUrl}/guess_game/play`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Ошибка при игре');
            }
            
            const result = await response.json();
            
            // Обновляем данные пользователя (баланс)
            if (result.user) {
                currentUser = result.user;
                updateUserInfo();
            }
            
            // Обновляем UI в зависимости от результата
            showGameResult(result);
            
        } catch (error) {
            console.error('Ошибка при игре:', error);
            showNotification('Произошла ошибка. Попробуйте позже.', 'error');
            
            // Возвращаем кнопки в нормальное состояние
            const numberButtons = document.querySelectorAll('.number-button');
            numberButtons.forEach(btn => {
                btn.disabled = false;
                btn.style.opacity = '1';
            });
        }
    }
    
    // Показать результат игры
    function showGameResult(result) {
        // Скрываем блок выбора числа
        document.getElementById('gameActiveBlock').classList.add('hidden');
        
        // Если нет попыток, показываем соответствующий блок
        if (!result.success && result.attempts_left === 0) {
            showNoAttemptsBlock();
            return;
        }
        
        // Показываем блок результата
        const resultBlock = document.getElementById('gameResultBlock');
        resultBlock.classList.remove('hidden');
        
        // Обновляем элементы UI с результатом
        const resultTitle = document.getElementById('resultTitle');
        const resultDescription = document.getElementById('resultDescription');
        const revealedNumber = document.getElementById('revealedNumber');
        const resultIconSuccess = document.getElementById('resultIconSuccess');
        const resultIconFail = document.getElementById('resultIconFail');
        const playAgainBtn = document.getElementById('playAgainBtn');
        
        // Устанавливаем загаданное число
        revealedNumber.textContent = result.random_number;
        
        // Обновляем счетчик попыток
        const attemptsLeftSpan = document.getElementById('attemptsLeft');
        if (attemptsLeftSpan) {
            attemptsLeftSpan.textContent = result.attempts_left;
        }
        
        if (result.correct) {
            // Показываем успешный результат
            resultTitle.textContent = 'Поздравляем!';
            resultDescription.textContent = `Вы угадали число и получили ${result.reward} луков!`;
            resultIconSuccess.classList.remove('hidden');
            resultIconFail.classList.add('hidden');
            
            // Показать уведомление о выигрыше
            showNotification(`Вы выиграли ${result.reward} Ⱡ!`, 'success');
        } else {
            // Показываем неудачный результат
            resultTitle.textContent = 'Не угадали';
            resultDescription.textContent = `К сожалению, вы не угадали число${result.penalty > 0 ? ` и потеряли ${result.penalty} луков` : ''}.`;
            resultIconSuccess.classList.add('hidden');
            resultIconFail.classList.remove('hidden');
            
            if (result.penalty > 0) {
                // Показать уведомление о проигрыше
                showNotification(`Списано ${result.penalty} Ⱡ`, 'error');
            }
        }
        
        // Включаем кнопку "Сыграть еще", если остались попытки
        if (playAgainBtn) {
            playAgainBtn.disabled = result.attempts_left <= 0;
        }
    }
    
    // === Конец функций игры "Угадай число" === //

    // Функции для игры "Кубик"
    async function initDiceGame() {
        try {
            // Получаем информацию о попытках
            const response = await fetch(`${apiUrl}/games/dice/attempts/${currentUser.user_id}`);
            if (!response.ok) {
                throw new Error('Не удалось получить информацию о попытках');
            }
            
            const data = await response.json();
            const attemptsLeft = data.attempts_left || 0;
            
            // Обновляем UI
            const attemptsLeftElement = document.getElementById('diceAttemptsLeft');
            if (attemptsLeftElement) {
                attemptsLeftElement.textContent = attemptsLeft;
            }
            
            // Показываем соответствующий блок в зависимости от наличия попыток
            if (attemptsLeft > 0) {
                resetDiceGameUI();
            } else {
                showDiceNoAttemptsBlock();
            }
            
            // Добавляем обработчики событий
            setupDiceGameEvents();
            
        } catch (error) {
            console.error('Ошибка при инициализации игры "Кубик":', error);
            showNotification('Не удалось загрузить игру "Кубик". Попробуйте позже.', 'error');
        }
    }
    
    function resetDiceGameUI() {
        // Скрываем все блоки
        document.getElementById('diceActiveBlock').classList.remove('hidden');
        document.getElementById('diceResultBlock').classList.add('hidden');
        document.getElementById('diceNoAttemptsBlock').classList.add('hidden');
        
        // Сбрасываем состояние кубика
        const dice = document.getElementById('dice');
        if (dice) {
            dice.classList.remove('rolling');
        }
        
        // Устанавливаем дефолтное изображение кубика
        setDiceFace(0);
    }
    
    function showDiceNoAttemptsBlock() {
        document.getElementById('diceActiveBlock').classList.add('hidden');
        document.getElementById('diceResultBlock').classList.add('hidden');
        document.getElementById('diceNoAttemptsBlock').classList.remove('hidden');
    }
    
    function setupDiceGameEvents() {
        // Кнопка для броска кубика
        const rollDiceBtn = document.getElementById('rollDiceBtn');
        if (rollDiceBtn) {
            rollDiceBtn.addEventListener('click', playDiceGame);
        }
        
        // Кнопка для закрытия результата
        const diceCloseBtn = document.getElementById('diceCloseBtn');
        if (diceCloseBtn) {
            diceCloseBtn.addEventListener('click', () => {
                // Возвращаемся на страницу с играми
                showPage(gamesPage);
                
                // Активируем вкладку игр
                const gamesNavButton = document.getElementById('gamesNavButton');
                if (gamesNavButton) {
                    document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
                    gamesNavButton.classList.add('active');
                }
            });
        }
        
        // Кнопка для закрытия блока "Нет попыток"
        const diceCloseNoAttemptsBtn = document.getElementById('diceCloseNoAttemptsBtn');
        if (diceCloseNoAttemptsBtn) {
            diceCloseNoAttemptsBtn.addEventListener('click', () => {
                // Возвращаемся на страницу с играми
                showPage(gamesPage);
                
                // Активируем вкладку игр
                const gamesNavButton = document.getElementById('gamesNavButton');
                if (gamesNavButton) {
                    document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('active'));
                    gamesNavButton.classList.add('active');
                }
            });
        }
    }
    
    async function playDiceGame() {
        try {
            // Блокируем кнопку на время анимации
            const rollDiceBtn = document.getElementById('rollDiceBtn');
            if (rollDiceBtn) {
                rollDiceBtn.disabled = true;
            }
            
            // Анимация броска кубика
            const dice = document.getElementById('dice');
            if (dice) {
                dice.classList.add('rolling');
            }
            
            // Обращаемся к API для получения результата
            const response = await fetch(`${apiUrl}/games/dice/play/${currentUser.user_id}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Не удалось сыграть в игру');
            }
            
            const result = await response.json();
            
            // Ждем окончания анимации перед показом результата
            setTimeout(() => {
                // Устанавливаем результат на кубике
                setDiceFace(result.value);
                
                // Разблокируем кнопку
                if (rollDiceBtn) {
                    rollDiceBtn.disabled = false;
                }
                
                // Показываем блок с результатом
                setTimeout(() => {
                    showDiceResult(result);
                    
                    // Обновляем баланс
                    if (currentUser) {
                        currentUser.balance = result.new_balance;
                        updateUserInfo();
                    }
                }, 500);
            }, 2000); // Время анимации
            
        } catch (error) {
            console.error('Ошибка при игре в "Кубик":', error);
            showNotification('Не удалось сыграть в игру. Попробуйте позже.', 'error');
            
            // Разблокируем кнопку
            const rollDiceBtn = document.getElementById('rollDiceBtn');
            if (rollDiceBtn) {
                rollDiceBtn.disabled = false;
            }
            
            // Восстанавливаем UI
            resetDiceGameUI();
        }
    }
    
    function showDiceResult(result) {
        // Скрываем блок с игрой
        document.getElementById('diceActiveBlock').classList.add('hidden');
        
        // Отображаем результат
        const diceResultValue = document.getElementById('diceResultValue');
        const diceReward = document.getElementById('diceReward');
        
        if (diceResultValue) {
            diceResultValue.textContent = result.value;
        }
        
        if (diceReward) {
            diceReward.textContent = result.reward;
        }
        
        // Показываем блок с результатом
        document.getElementById('diceResultBlock').classList.remove('hidden');
    }
    
    function setDiceFace(value) {
        const diceFace = document.getElementById('diceFace');
        if (!diceFace) return;
        
        // Устанавливаем SVG для соответствующей грани кубика
        switch (value) {
            case 1:
                diceFace.innerHTML = `
                    <circle cx="12" cy="12" r="3" fill="currentColor" />
                `;
                break;
            case 2:
                diceFace.innerHTML = `
                    <circle cx="9" cy="9" r="2" fill="currentColor" />
                    <circle cx="15" cy="15" r="2" fill="currentColor" />
                `;
                break;
            case 3:
                diceFace.innerHTML = `
                    <circle cx="9" cy="9" r="2" fill="currentColor" />
                    <circle cx="12" cy="12" r="2" fill="currentColor" />
                    <circle cx="15" cy="15" r="2" fill="currentColor" />
                `;
                break;
            case 4:
                diceFace.innerHTML = `
                    <circle cx="9" cy="9" r="2" fill="currentColor" />
                    <circle cx="9" cy="15" r="2" fill="currentColor" />
                    <circle cx="15" cy="9" r="2" fill="currentColor" />
                    <circle cx="15" cy="15" r="2" fill="currentColor" />
                `;
                break;
            case 5:
                diceFace.innerHTML = `
                    <circle cx="9" cy="9" r="2" fill="currentColor" />
                    <circle cx="9" cy="15" r="2" fill="currentColor" />
                    <circle cx="12" cy="12" r="2" fill="currentColor" />
                    <circle cx="15" cy="9" r="2" fill="currentColor" />
                    <circle cx="15" cy="15" r="2" fill="currentColor" />
                `;
                break;
            case 6:
                diceFace.innerHTML = `
                    <circle cx="9" cy="8" r="2" fill="currentColor" />
                    <circle cx="9" cy="12" r="2" fill="currentColor" />
                    <circle cx="9" cy="16" r="2" fill="currentColor" />
                    <circle cx="15" cy="8" r="2" fill="currentColor" />
                    <circle cx="15" cy="12" r="2" fill="currentColor" />
                    <circle cx="15" cy="16" r="2" fill="currentColor" />
                `;
                break;
            default:
                // Значение по умолчанию (кубик без граней)
                diceFace.innerHTML = `
                    <path fill-rule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm3 10.5a.75.75 0 000-1.5H9a.75.75 0 000 1.5h6z" clip-rule="evenodd" />
                `;
                break;
        }
    }
}); 