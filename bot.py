import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# конфиг / config
BOT_NAME = "BrokerBot"
ADMIN_IDS = [8245959926, 5785618204]  #ID админиов / admins ID
JSON_USERS_FILE = "users.json"
JSON_STAFF_FILE = "staff.json"
JSON_WITHDRAWALS_FILE = "withdrawals.json"
JSON_DEPOSITS_FILE = "deposits.json"
JSON_VERIFICATIONS_FILE = "verifications.json"

#состояния для конечного автомата / states for a fsm 
(
    START,
    REGISTRATION_NAME,
    REGISTRATION_PASSPORT,
    PERSONAL_CABINET,
    DEPOSIT,
    WITHDRAWAL,
    VERIFICATION,
    ADMIN_MENU,
    ADMIN_USERS,
    ADMIN_USER_DETAIL,
    ADMIN_CHANGE_NAME,
    ADMIN_CHANGE_PASSPORT,  
    ADMIN_WITHDRAWAL_DETAIL,
    ADMIN_DEPOSITS,
    ADMIN_DEPOSIT_DETAIL,
    ADMIN_VERIFICATIONS,
    ADMIN_VERIFICATION_DETAIL,
    ADMIN_ADD_STAFF,
    ADMIN_APPROVED_REQUESTS,
    ADMIN_REJECTED_REQUESTS,
    ADMIN_APPROVED_WITHDRAWALS,
    ADMIN_REJECTED_WITHDRAWALS,
    ADMIN_APPROVED_DEPOSITS,
    ADMIN_REJECTED_DEPOSITS,
    ADMIN_ADD_BALANCE,
    ADMIN_REDUCE_BALANCE,
    CHANGE_LANGUAGE,
) = range(27)  

class User:
    def __init__(self, user_id, full_name=None, passport=None, balance=0, on_hold=0, verified=False, language='ru'):
        self.user_id = user_id
        self.full_name = full_name
        self.passport = passport
        self.balance = balance
        self.on_hold = on_hold
        self.verified = verified
        self.language = language
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'full_name': self.full_name,
            'passport': self.passport,
            'balance': self.balance,
            'on_hold': self.on_hold,
            'verified': self.verified,
            'language': self.language
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data['user_id'],
            full_name=data['full_name'],
            passport=data.get('passport'),
            balance=data.get('balance', 0),
            on_hold=data.get('on_hold', 0),
            verified=data.get('verified', False),
            language=data.get('language', 'ru')
        )

class WithdrawalRequest:
    def __init__(self, request_id, user_id, amount, details):
        self.request_id = request_id
        self.user_id = user_id
        self.amount = amount
        self.details = details
        self.status = "pending"
    
    def to_dict(self):
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'details': self.details,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data):
        request = cls(
            request_id=data['request_id'],
            user_id=data['user_id'],
            amount=data['amount'],
            details=data['details']
        )
        request.status = data.get('status', 'pending')
        return request

class DepositRequest:
    def __init__(self, request_id, user_id, amount):
        self.request_id = request_id
        self.user_id = user_id
        self.amount = amount
        self.status = "pending"
    
    def to_dict(self):
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data):
        request = cls(
            request_id=data['request_id'],
            user_id=data['user_id'],
            amount=data['amount']
        )
        request.status = data.get('status', 'pending')
        return request

class VerificationRequest:
    def __init__(self, request_id, user_id, photo_file_id):
        self.request_id = request_id
        self.user_id = user_id
        self.photo_file_id = photo_file_id
        self.status = "pending"
    
    def to_dict(self):
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'photo_file_id': self.photo_file_id,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data):
        request = cls(
            request_id=data['request_id'],
            user_id=data['user_id'],
            photo_file_id=data['photo_file_id']
        )
        request.status = data.get('status', 'pending')
        return request

#работа с JSON / working with JSON
def init_json_files():
    # создаем файлы / create file
    for file_path in [JSON_USERS_FILE, JSON_STAFF_FILE, JSON_WITHDRAWALS_FILE, JSON_DEPOSITS_FILE, JSON_VERIFICATIONS_FILE]:
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

def save_user_to_json(user: User):
    users = load_users_from_json()
    
    #поиск юзера для обновления / searching for a user to update
    user_found = False
    for i, u in enumerate(users):
        if u.user_id == user.user_id:
            users[i] = user
            user_found = True
            break
    
    #если не находит, добавляем ноового / if it doesn't find it, add a new one
    if not user_found:
        users.append(user)
    
    #сохраняем JSON / save JSON
    with open(JSON_USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump([u.to_dict() for u in users], f, ensure_ascii=False, indent=2)

def load_users_from_json():
    try:
        with open(JSON_USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [User.from_dict(user_data) for user_data in data]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_user_from_json(user_id):
    users = load_users_from_json()
    for user in users:
        if user.user_id == user_id:
            return user
    return None

def get_all_users():
    return load_users_from_json()

def save_withdrawal_request(request: WithdrawalRequest):
    requests = load_withdrawal_requests_from_json()
    requests.append(request)
    
    with open(JSON_WITHDRAWALS_FILE, 'w', encoding='utf-8') as f:
        json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)

def load_withdrawal_requests_from_json():
    try:
        with open(JSON_WITHDRAWALS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [WithdrawalRequest.from_dict(req_data) for req_data in data]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_withdrawal_requests(status=None):
    requests = load_withdrawal_requests_from_json()
    if status is None:
        return requests
    return [r for r in requests if r.status == status]

def delete_withdrawal_request(request_id):
    requests = load_withdrawal_requests_from_json()
    original_count = len(requests)
    
    #фильтр запросов, остаются только те у которых ID не совпадает / query filter, only those with an ID that does not match are left
    requests = [r for r in requests if r.request_id != request_id]
    
    if len(requests) < original_count:
        #сохранение обновленного списка / saving an updated list
        with open(JSON_WITHDRAWALS_FILE, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)
        return True
    return False

def save_deposit_request(request: DepositRequest):
    requests = load_deposit_requests_from_json()
    requests.append(request)
    
    with open(JSON_DEPOSITS_FILE, 'w', encoding='utf-8') as f:
        json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)

def load_deposit_requests_from_json():
    try:
        with open(JSON_DEPOSITS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [DepositRequest.from_dict(req_data) for req_data in data]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_deposit_requests(status=None):
    requests = load_deposit_requests_from_json()
    if status is None:
        return requests
    return [r for r in requests if r.status == status]

def delete_deposit_request(request_id):
    requests = load_deposit_requests_from_json()
    original_count = len(requests)
    
    requests = [r for r in requests if r.request_id != request_id]
    
    if len(requests) < original_count:
        with open(JSON_DEPOSITS_FILE, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)
        return True
    return False

def save_verification_request(request: VerificationRequest):
    requests = load_verification_requests_from_json()
    requests.append(request)
    
    with open(JSON_VERIFICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)

def load_verification_requests_from_json():
    try:
        with open(JSON_VERIFICATIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [VerificationRequest.from_dict(req_data) for req_data in data]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def get_verification_requests(status=None):
    requests = load_verification_requests_from_json()
    if status is None:
        return requests
    return [r for r in requests if r.status == status]

def delete_verification_request(request_id):
    requests = load_verification_requests_from_json()
    original_count = len(requests)
    
    requests = [r for r in requests if r.request_id != request_id]
    
    if len(requests) < original_count:
        with open(JSON_VERIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)
        return True
    return False

def is_staff(user_id):
    if user_id in ADMIN_IDS:
        return True
    
    try:
        with open(JSON_STAFF_FILE, 'r', encoding='utf-8') as f:
            staff_data = json.load(f)
            return any(staff['user_id'] == user_id for staff in staff_data)
    except (FileNotFoundError, json.JSONDecodeError):
        return False

def add_staff_to_json(user_id, full_name):
    try:
        with open(JSON_STAFF_FILE, 'r', encoding='utf-8') as f:
            staff_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        staff_data = []
    
    # Проверяем, нет ли уже такого сотрудника
    if not any(staff['user_id'] == user_id for staff in staff_data):
        staff_data.append({'user_id': user_id, 'full_name': full_name})
        
        with open(JSON_STAFF_FILE, 'w', encoding='utf-8') as f:
            json.dump(staff_data, f, ensure_ascii=False, indent=2)


TEXTS = {
    'ru': {
        'start': '👋 *Добро пожаловать в "{BOT_NAME}"*\n\n📋 *Краткая информация о боте:*\nВаш надежный брокерский помощник\n\n⚠️ *Перед использованием бота нужно пройти регистрацию.*',
        'personal_cabinet': '👤 *Добро пожаловать в личный кабинет*\n\n📝 *ФИО:* {full_name}\n📋 *Паспорт:* {passport}\n\n💰 *Баланс:* {balance} ₽\n⏳ *На выводе:* {on_hold} ₽\n\n🛡️ *Верификация:* {verification_status}\n\n🆔 *ID:* `{user_id}`\n_Нажмите на ID, чтобы скопировать_',
        'deposit': '💰 *Пополнение баланса*\n\n💳 *Введите сумму для пополнения:*\nПример: `1500`',
        'withdraw': '💸 *Вывод средств*\n\n💳 *Введите ниже свои реквизиты, а также сумму для вывода*\n💰 *Доступно к выводу:* {balance} ₽\n\n📋 *Пример:*\n`2000 1000 3000 2000, 150`\n\n⚠️ *В случае если вы напишите только реквизиты, заявка на вывод будет отклонена.*\nСпасибо за понимание',
        'verify': '🛡️ *Верификация аккаунта*\n\n📷 *Для прохождения верификации отправьте основной разворот паспорта*\n\n⏳ После отправки ожидайте одобрение заявки',
        'registration_name': '📝 *Введите свое ФИО:*',
        'registration_passport': '📋 *Введите серию и номер паспорта:*\n\n*Пример:* `1234 567890`',
        'change_language': '🌐 *Смена языка*\n\nВыберите язык интерфейса:',
        'language_changed': '✅ *Язык успешно изменен на английский!*',
        'verification_status_changed': '✅ *Статус верификации изменен!*\n\n🛡️ *Новый статус:* {status}',
        'profile_updated': '✅ *Данные профиля обновлены!*',
        'balance_management': '💰 *Управление балансом*\n\n📝 *Выберите действие:*',
        'add_balance': '💳 *Пополнение баланса*\n\n💰 *Текущий баланс пользователя:* {balance} ₽\n\n💵 *Введите сумму для пополнения:*',
        'reduce_balance': '💸 *Уменьшение баланса*\n\n💰 *Текущий баланс пользователя:* {balance} ₽\n\n💵 *Введите сумму для уменьшения:*',
        'balance_added': '✅ *Баланс пользователя пополнен!*\n\n💰 *Новый баланс:* {new_balance} ₽\n💵 *Добавлено:* {amount} ₽',
        'balance_reduced': '✅ *Баланс пользователя уменьшен!*\n\n💰 *Новый баланс:* {new_balance} ₽\n💵 *Уменьшено:* {amount} ₽',
        'insufficient_balance': '❌ *Недостаточно средств для уменьшения!*\n\n💰 *Текущий баланс:* {balance} ₽\n💵 *Запрошено:* {amount} ₽',
        'invalid_amount': '❌ *Неверная сумма!*\n\n💡 *Введите положительное число:*'
    },
    'en': {
        'start': '👋 *Welcome to "{BOT_NAME}"*\n\n📋 *About the bot:*\nYour reliable brokerage assistant\n\n⚠️ *You need to register before using the bot.*',
        'personal_cabinet': '👤 *Welcome to Personal Cabinet*\n\n📝 *Full Name:* {full_name}\n📋 *Passport:* {passport}\n\n💰 *Balance:* {balance} ₽\n⏳ *On Hold:* {on_hold} ₽\n\n🛡️ *Verification:* {verification_status}\n\n🆔 *ID:* `{user_id}`\n_Click on ID to copy_',
        'deposit': '💰 *Deposit Funds*\n\n💳 *Enter the deposit amount:*\nExample: `1500`',
        'withdraw': '💸 *Withdraw Funds*\n\n💳 *Enter your details and withdrawal amount below*\n💰 *Available for withdrawal:* {balance} ₽\n\n📋 *Example:*\n`2000 1000 3000 2000, 150`\n\n⚠️ *If you only provide details without amount, the withdrawal request will be rejected.*\nThank you for understanding',
        'verify': '🛡️ *Account Verification*\n\n📷 *To complete verification, send the main page of your passport*\n\n⏳ Please wait for approval after submission',
        'registration_name': '📝 *Enter your Full Name:*',
        'registration_passport': '📋 *Enter passport series and number:*\n\n*Example:* `1234 567890`',
        'change_language': '🌐 *Language Settings*\n\nChoose interface language:',
        'language_changed': '✅ *Language successfully changed to English!*',
        'verification_status_changed': '✅ *Verification status changed!*\n\n🛡️ *New status:* {status}',
        'profile_updated': '✅ *Profile data updated!*',
        'balance_management': '💰 *Balance Management*\n\n📝 *Choose action:*',
        'add_balance': '💳 *Add Balance*\n\n💰 *Current user balance:* {balance} ₽\n\n💵 *Enter amount to add:*',
        'reduce_balance': '💸 *Reduce Balance*\n\n💰 *Current user balance:* {balance} ₽\n\n💵 *Enter amount to reduce:*',
        'balance_added': '✅ *User balance increased!*\n\n💰 *New balance:* {new_balance} ₽\n💵 *Added:* {amount} ₽',
        'balance_reduced': '✅ *User balance decreased!*\n\n💰 *New balance:* {new_balance} ₽\n💵 *Reduced:* {amount} ₽',
        'insufficient_balance': '❌ *Insufficient funds to reduce!*\n\n💰 *Current balance:* {balance} ₽\n💵 *Requested:* {amount} ₽',
        'invalid_amount': '❌ *Invalid amount!*\n\n💡 *Enter a positive number:*'
    }
}

#клавиатуры / keyboards
def get_start_keyboard(language='ru'):
    texts = TEXTS[language]
    keyboard = [
        [InlineKeyboardButton("📝 Зарегистрироваться" if language == 'ru' else "📝 Register", callback_data="register")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard(target_state, language='ru'):
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад" if language == 'ru' else "⬅️ Back", callback_data=f"back_to_{target_state}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_personal_cabinet_keyboard(user: User):
    language = user.language
    keyboard = [
        [
            InlineKeyboardButton("💰 Пополнить" if language == 'ru' else "💰 Deposit", callback_data="deposit"),
            InlineKeyboardButton("💳 Вывести" if language == 'ru' else "💳 Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("🔄 Обновить" if language == 'ru' else "🔄 Refresh", callback_data="refresh_profile")]
    ]
    
    if not user.verified:
        keyboard.append([InlineKeyboardButton("🛡️ Пройти верификацию" if language == 'ru' else "🛡️ Verify Account", callback_data="verify")])
    
    keyboard.append([InlineKeyboardButton("🌐 Сменить язык" if language == 'ru' else "🌐 Change Language", callback_data="change_language")])
    
    return InlineKeyboardMarkup(keyboard)

def get_language_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="set_language_ru"),
            InlineKeyboardButton("🇺🇸 English", callback_data="set_language_en")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_personal_cabinet")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu_keyboard(is_admin=True, language='ru'):
    keyboard = [
        [InlineKeyboardButton("👥 Управление всеми пользователями" if language == 'ru' else "👥 Manage All Users", callback_data="admin_users")],
        [InlineKeyboardButton("💸 Все заявки на вывод" if language == 'ru' else "💸 All Withdrawal Requests", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("💰 Все заявки на пополнение" if language == 'ru' else "💰 All Deposit Requests", callback_data="admin_deposits")],
        [InlineKeyboardButton("🛡️ Заявки на верификацию" if language == 'ru' else "🛡️ Verification Requests", callback_data="admin_verifications")],
        [InlineKeyboardButton("✅ Все одобренные заявки" if language == 'ru' else "✅ All Approved Requests", callback_data="admin_approved_requests")],
        [InlineKeyboardButton("❌ Все отклоненные заявки" if language == 'ru' else "❌ All Rejected Requests", callback_data="admin_rejected_requests")],
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("➕ Добавить работника" if language == 'ru' else "➕ Add Employee", callback_data="admin_add_staff")])
    
    return InlineKeyboardMarkup(keyboard)

def get_admin_user_management_keyboard(language='ru'):
    keyboard = [
        [InlineKeyboardButton("✏️ Сменить ФИО" if language == 'ru' else "✏️ Change Name", callback_data="admin_change_name")],
        [InlineKeyboardButton("📋 Сменить паспорт" if language == 'ru' else "📋 Change Passport", callback_data="admin_change_passport")],  # ДОБАВЛЕНА НОВАЯ КНОПКА
        [InlineKeyboardButton("💰 Пополнить баланс" if language == 'ru' else "💰 Add Balance", callback_data="admin_add_balance")],
        [InlineKeyboardButton("💸 Уменьшить баланс" if language == 'ru' else "💸 Reduce Balance", callback_data="admin_reduce_balance")],
        [InlineKeyboardButton("🛡️ Изменить статус верификации" if language == 'ru' else "🛡️ Change Verification", callback_data="admin_toggle_verification")],
        [InlineKeyboardButton("⬅️ Назад" if language == 'ru' else "⬅️ Back", callback_data="admin_back_to_users")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_withdrawal_management_keyboard(request_id, language='ru'):
    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить заявку" if language == 'ru' else "✅ Approve Request", callback_data=f"approve_withdrawal_{request_id}"),
            InlineKeyboardButton("❌ Отклонить заявку" if language == 'ru' else "❌ Reject Request", callback_data=f"reject_withdrawal_{request_id}")
        ],
        [InlineKeyboardButton("📞 Связаться с пользователем" if language == 'ru' else "📞 Contact User", callback_data=f"contact_user_{request_id}")],
        [InlineKeyboardButton("⬅️ Назад" if language == 'ru' else "⬅️ Back", callback_data="admin_back_to_withdrawals")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_deposit_management_keyboard(request_id, language='ru'):
    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить заявку" if language == 'ru' else "✅ Approve Request", callback_data=f"approve_deposit_{request_id}"),
            InlineKeyboardButton("❌ Отклонить заявку" if language == 'ru' else "❌ Reject Request", callback_data=f"reject_deposit_{request_id}")
        ],
        [InlineKeyboardButton("📞 Связаться с пользователем" if language == 'ru' else "📞 Contact User", callback_data=f"contact_user_{request_id}")],
        [InlineKeyboardButton("⬅️ Назад" if language == 'ru' else "⬅️ Back", callback_data="admin_back_to_deposits")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_verification_management_keyboard(request_id, language='ru'):
    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить заявку" if language == 'ru' else "✅ Approve Request", callback_data=f"approve_verification_{request_id}"),
            InlineKeyboardButton("❌ Отклонить заявку" if language == 'ru' else "❌ Reject Request", callback_data=f"reject_verification_{request_id}")
        ],
        [InlineKeyboardButton("📞 Связаться с пользователем" if language == 'ru' else "📞 Contact User", callback_data=f"contact_user_{request_id}")],
        [InlineKeyboardButton("⬅️ Назад" if language == 'ru' else "⬅️ Back", callback_data="admin_back_to_verifications")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_approved_requests_keyboard(language='ru'):
    keyboard = [
        [InlineKeyboardButton("💸 На вывод" if language == 'ru' else "💸 Withdrawals", callback_data="admin_approved_withdrawals")],
        [InlineKeyboardButton("💰 На пополнение" if language == 'ru' else "💰 Deposits", callback_data="admin_approved_deposits")],
        [InlineKeyboardButton("⬅️ Назад" if language == 'ru' else "⬅️ Back", callback_data="admin_back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_rejected_requests_keyboard(language='ru'):
    keyboard = [
        [InlineKeyboardButton("💸 На вывод" if language == 'ru' else "💸 Withdrawals", callback_data="admin_rejected_withdrawals")],
        [InlineKeyboardButton("💰 На пополнение" if language == 'ru' else "💰 Deposits", callback_data="admin_rejected_deposits")],
        [InlineKeyboardButton("⬅️ Назад" if language == 'ru' else "⬅️ Back", callback_data="admin_back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

#вспомогательные функции для обновления списков заявок / auxiliary functions for updating application lists
async def show_admin_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['state'] = ADMIN_WITHDRAWAL_DETAIL
    requests = get_withdrawal_requests("pending")
    
    keyboard = []
    for i, req in enumerate(requests):
        user = get_user_from_json(req.user_id)
        if user:
            keyboard.append([InlineKeyboardButton(f"💸 Заявка {i+1} от {user.full_name}", callback_data=f"admin_withdrawal_{req.request_id}")])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("📭 Нет заявок", callback_data="no_actions")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_menu")])
    
    await query.edit_message_text(
        "💸 *Заявки на вывод*\n\n📋 *Ниже представлен список всех заявок на вывод:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_admin_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['state'] = ADMIN_DEPOSITS
    requests = get_deposit_requests("pending")
    
    keyboard = []
    for i, req in enumerate(requests):
        user = get_user_from_json(req.user_id)
        if user:
            keyboard.append([InlineKeyboardButton(f"💰 Заявка {i+1} от {user.full_name}", callback_data=f"admin_deposit_{req.request_id}")])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("📭 Нет заявок", callback_data="no_actions")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_menu")])
    
    await query.edit_message_text(
        "💰 *Заявки на пополнение*\n\n📋 *Ниже представлен список всех заявок на пополнение:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_admin_verifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['state'] = ADMIN_VERIFICATIONS
    requests = get_verification_requests("pending")
    
    keyboard = []
    for i, req in enumerate(requests):
        user = get_user_from_json(req.user_id)
        if user:
            keyboard.append([InlineKeyboardButton(f"🛡️ Заявка {i+1} от {user.full_name}", callback_data=f"admin_verification_{req.request_id}")])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("📭 Нет заявок", callback_data="no_actions")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_menu")])
    
    await query.edit_message_text(
        "🛡️ *Заявки на верификацию*\n\n📋 *Ниже представлен список всех заявок на верификацию:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_admin_approved_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['state'] = ADMIN_APPROVED_WITHDRAWALS
    requests = get_withdrawal_requests("approved")
    
    keyboard = []
    for i, req in enumerate(requests):
        user = get_user_from_json(req.user_id)
        if user:
            keyboard.append([InlineKeyboardButton(f"✅ Заявка {i+1} от {user.full_name}", callback_data=f"admin_approved_withdrawal_{req.request_id}")])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("📭 Нет одобренных заявок", callback_data="no_actions")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_approved")])
    
    await query.edit_message_text(
        "✅ *Одобренные заявки на вывод*\n\n📋 *Ниже представлен список всех одобренных заявок на вывод:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_admin_approved_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['state'] = ADMIN_APPROVED_DEPOSITS
    requests = get_deposit_requests("approved")
    
    keyboard = []
    for i, req in enumerate(requests):
        user = get_user_from_json(req.user_id)
        if user:
            keyboard.append([InlineKeyboardButton(f"✅ Заявка {i+1} от {user.full_name}", callback_data=f"admin_approved_deposit_{req.request_id}")])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("📭 Нет одобренных заявок", callback_data="no_actions")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_approved")])
    
    await query.edit_message_text(
        "✅ *Одобренные заявки на пополнение*\n\n📋 *Ниже представлен список всех одобренных заявок на пополнение:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_admin_rejected_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['state'] = ADMIN_REJECTED_WITHDRAWALS
    requests = get_withdrawal_requests("rejected")
    
    keyboard = []
    for i, req in enumerate(requests):
        user = get_user_from_json(req.user_id)
        if user:
            keyboard.append([InlineKeyboardButton(f"❌ Заявка {i+1} от {user.full_name}", callback_data=f"admin_rejected_withdrawal_{req.request_id}")])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("📭 Нет отклоненных заявок", callback_data="no_actions")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_rejected")])
    
    await query.edit_message_text(
        "❌ *Отклоненные заявки на вывод*\n\n📋 *Ниже представлен список всех отклоненных заявок на вывод:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_admin_rejected_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['state'] = ADMIN_REJECTED_DEPOSITS
    requests = get_deposit_requests("rejected")
    
    keyboard = []
    for i, req in enumerate(requests):
        user = get_user_from_json(req.user_id)
        if user:
            keyboard.append([InlineKeyboardButton(f"❌ Заявка {i+1} от {user.full_name}", callback_data=f"admin_rejected_deposit_{req.request_id}")])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("📭 Нет отклоненных заявок", callback_data="no_actions")])
        
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_rejected")])
    
    await query.edit_message_text(
        "❌ *Отклоненные заявки на пополнение*\n\n📋 *Ниже представлен список всех отклоненных заявок на пополнение:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_staff(user_id):
        #показывает меню администратора/работника / shows the admin/employee menu
        context.user_data['state'] = ADMIN_MENU
        user = get_user_from_json(user_id)
        language = user.language if user else 'ru'
        message = "👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:" if language == 'ru' else "👨‍💼 *Welcome to Management Menu*\n\nChoose the action you want to perform:"
        await update.message.reply_text(message, reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS, language), parse_mode='Markdown')
    else:
        user = get_user_from_json(user_id)
        if user and user.full_name and user.passport:
            #зарегистрированный юзер / registered user
            context.user_data['state'] = PERSONAL_CABINET
            context.user_data['user'] = user
            await show_personal_cabinet(update, context)
        else:
            #новый юзер / new user
            context.user_data['state'] = START
            language = user.language if user else 'ru'
            texts = TEXTS[language]
            message = texts['start'].format(BOT_NAME=BOT_NAME)
            await update.message.reply_text(message, reply_markup=get_start_keyboard(language), parse_mode='Markdown')

async def show_personal_cabinet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = context.user_data.get('user')
    if not user:
        user_id = update.effective_user.id
        user = get_user_from_json(user_id)
        if not user:
            await start(update, context)
            return
    
    #обновление данных юзера из бд перед показом / updating user data from the database before displaying it
    user = get_user_from_json(user.user_id)
    if user:
        context.user_data['user'] = user
    
    language = user.language
    texts = TEXTS[language]
    verification_status = '✅ Verified' if user.verified else '❌ Not Verified'
    if language == 'ru':
        verification_status = '✅ Верифицирован' if user.verified else '❌ Не верифицирован'
    
    message = texts['personal_cabinet'].format(
        full_name=user.full_name,
        passport=user.passport or 'Не указан',
        balance=user.balance,
        on_hold=user.on_hold,
        verification_status=verification_status,
        user_id=user.user_id
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message, 
            reply_markup=get_personal_cabinet_keyboard(user),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message, 
            reply_markup=get_personal_cabinet_keyboard(user),
            parse_mode='Markdown'
        )

#callback запросы / callback requets 
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    user = get_user_from_json(user_id)
    language = user.language if user else 'ru'
    
    if data == "register":
        context.user_data['state'] = REGISTRATION_NAME
        texts = TEXTS[language]
        await query.edit_message_text(
            texts['registration_name'],
            reply_markup=get_back_keyboard("start", language),
            parse_mode='Markdown'
        )
    
    elif data == "back_to_start":
        context.user_data['state'] = START
        texts = TEXTS[language]
        message = texts['start'].format(BOT_NAME=BOT_NAME)
        await query.edit_message_text(message, reply_markup=get_start_keyboard(language), parse_mode='Markdown')
    
    elif data == "back_to_personal_cabinet":
        context.user_data['state'] = PERSONAL_CABINET
        await show_personal_cabinet(update, context)
    
    elif data == "back_to_admin_user_detail":
        context.user_data['state'] = ADMIN_USER_DETAIL
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            verification_status = '✅ Верифицирован' if managed_user.verified else '❌ Не верифицирован'
            
            message = (
                f"👤 *Личный кабинет пользователя:*\n\n"
                f"📝 *ФИО:* {managed_user.full_name}\n"
                f"📋 *Паспорт:* {managed_user.passport or 'Не указан'}\n"
                f"💰 *Баланс:* {managed_user.balance} ₽\n"
                f"⏳ *На выводе:* {managed_user.on_hold} ₽\n"
                f"🛡️ *Верификация:* {verification_status}\n"
                f"🆔 *ID:* {managed_user.user_id}"
            )
            
            await query.edit_message_text(
                message, 
                reply_markup=get_admin_user_management_keyboard(),
                parse_mode='Markdown'
            )
    
    elif data == "deposit":
        context.user_data['state'] = DEPOSIT
        texts = TEXTS[language]
        message = texts['deposit']
        await query.edit_message_text(
            message, 
            reply_markup=get_back_keyboard("personal_cabinet", language),
            parse_mode='Markdown'
        )
    
    elif data == "withdraw":
        user_obj = context.user_data.get('user', get_user_from_json(user_id))
        context.user_data['state'] = WITHDRAWAL
        texts = TEXTS[language]
        message = texts['withdraw'].format(balance=user_obj.balance)
        await query.edit_message_text(
            message, 
            reply_markup=get_back_keyboard("personal_cabinet", language),
            parse_mode='Markdown'
        )
    
    elif data == "verify":
        context.user_data['state'] = VERIFICATION
        texts = TEXTS[language]
        message = texts['verify']
        await query.edit_message_text(
            message, 
            reply_markup=get_back_keyboard("personal_cabinet", language),
            parse_mode='Markdown'
        )
    
    elif data == "change_language":
        context.user_data['state'] = CHANGE_LANGUAGE
        texts = TEXTS[language]
        await query.edit_message_text(
            texts['change_language'],
            reply_markup=get_language_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "refresh_profile":
        #обновление профиля / update profile
        user = get_user_from_json(user_id)
        if user:
            context.user_data['user'] = user
            texts = TEXTS[user.language]
            
            #сообщение об успешном обновлении / message about succeful update
            await query.answer(texts['profile_updated'], show_alert=False)
            
            #обновление данных в личном кабинете / updating data in your profile
            await show_personal_cabinet(update, context)
    
    elif data.startswith("set_language_"):
        new_language = data.split("_")[2]  #ru или en / ru or en language
        user = get_user_from_json(user_id)
        if user:
            user.language = new_language
            save_user_to_json(user)
            context.user_data['user'] = user
        
        texts = TEXTS[new_language]
        await query.edit_message_text(
            texts['language_changed'],
            parse_mode='Markdown'
        )
        context.user_data['state'] = PERSONAL_CABINET
        await show_personal_cabinet(update, context)
    
    elif data == "no_actions":
        await query.answer("Нет доступных действий", show_alert=True)
    
    #админ обработчики / admin handlers
    elif data == "admin_users":
        context.user_data['state'] = ADMIN_USERS
        users = get_all_users()
        keyboard = []
        for user in users:
            keyboard.append([InlineKeyboardButton(f"👤 {user.full_name}", callback_data=f"admin_user_{user.user_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_menu")])
        
        await query.edit_message_text(
            "👥 *Управление пользователями*\n\n📋 *Выберите пользователя из списка или введите id пользователя:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith("admin_user_"):
        user_id_to_manage = int(data.split("_")[2])
        user_to_manage = get_user_from_json(user_id_to_manage)
        context.user_data['managed_user'] = user_to_manage
        context.user_data['state'] = ADMIN_USER_DETAIL
        
        verification_status = '✅ Верифицирован' if user_to_manage.verified else '❌ Не верифицирован'
        
        message = (
            f"👤 *Личный кабинет пользователя:*\n\n"
            f"📝 *ФИО:* {user_to_manage.full_name}\n"
            f"📋 *Паспорт:* {user_to_manage.passport or 'Не указан'}\n"
            f"💰 *Баланс:* {user_to_manage.balance} ₽\n"
            f"⏳ *На выводе:* {user_to_manage.on_hold} ₽\n"
            f"🛡️ *Верификация:* {verification_status}\n"
            f"🆔 *ID:* {user_to_manage.user_id}"
        )
        
        await query.edit_message_text(
            message, 
            reply_markup=get_admin_user_management_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "admin_change_name":
        context.user_data['state'] = ADMIN_CHANGE_NAME
        await query.edit_message_text(
            "✏️ *Смена ФИО пользователя*\n\n📝 *Напишите ниже новое ФИО для пользователя:*",
            reply_markup=get_back_keyboard("admin_user_detail"),
            parse_mode='Markdown'
        )
    
    elif data == "admin_change_passport":  
        context.user_data['state'] = ADMIN_CHANGE_PASSPORT
        await query.edit_message_text(
            "📋 *Смена паспортных данных пользователя*\n\n📝 *Напишите ниже новые паспортные данные для пользователя:*\n\n*Пример:* `1234 567890`",
            reply_markup=get_back_keyboard("admin_user_detail"),
            parse_mode='Markdown'
        )
    
    elif data == "admin_add_balance":
        context.user_data['state'] = ADMIN_ADD_BALANCE
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            texts = TEXTS[language]
            await query.edit_message_text(
                texts['add_balance'].format(balance=managed_user.balance),
                reply_markup=get_back_keyboard("admin_user_detail", language),
                parse_mode='Markdown'
            )
    
    elif data == "admin_reduce_balance":
        context.user_data['state'] = ADMIN_REDUCE_BALANCE
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            texts = TEXTS[language]
            await query.edit_message_text(
                texts['reduce_balance'].format(balance=managed_user.balance),
                reply_markup=get_back_keyboard("admin_user_detail", language),
                parse_mode='Markdown'
            )
    
    elif data == "admin_toggle_verification":
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            #смена статуса верификации на противоположный / changing the verification status to the opposite
            managed_user.verified = not managed_user.verified
            save_user_to_json(managed_user)
            
            #определение нового статуса для сообщения / defining a new status for a message
            new_status = '✅ Верифицирован' if managed_user.verified else '❌ Не верифицирован'
            
            #уведомление юзеру о смене статуса / notification to the user about the status change
            try:
                user_language = managed_user.language
                if user_language == 'ru':
                    notification_text = f"🛡️ *Ваш статус верификации изменен!*\n\n*Новый статус:* {new_status}"
                else:
                    notification_text = f"🛡️ *Your verification status has been changed!*\n\n*New status:* {'✅ Verified' if managed_user.verified else '❌ Not Verified'}"
                
                await context.bot.send_message(
                    chat_id=managed_user.user_id,
                    text=notification_text,
                    parse_mode='Markdown'
                )
            except:
                pass
            
            #показ обновленных данных пользователя / showing updated user data
            message = (
                f"👤 *Личный кабинет пользователя:*\n\n"
                f"📝 *ФИО:* {managed_user.full_name}\n"
                f"📋 *Паспорт:* {managed_user.passport or 'Не указан'}\n"
                f"💰 *Баланс:* {managed_user.balance} ₽\n"
                f"⏳ *На выводе:* {managed_user.on_hold} ₽\n"
                f"🛡️ *Верификация:* {new_status}\n"
                f"🆔 *ID:* {managed_user.user_id}"
            )
            
            await query.edit_message_text(
                message, 
                reply_markup=get_admin_user_management_keyboard(),
                parse_mode='Markdown'
            )
    
    elif data == "admin_back_to_users":
        context.user_data['state'] = ADMIN_USERS
        users = get_all_users()
        keyboard = []
        for user in users:
            keyboard.append([InlineKeyboardButton(f"👤 {user.full_name}", callback_data=f"admin_user_{user.user_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_to_menu")])
        
        await query.edit_message_text(
            "👥 *Управление пользователями*\n\n📋 *Выберите пользователя из списка или введите id пользователя:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "admin_back_to_user_detail":
        context.user_data['state'] = ADMIN_USER_DETAIL
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            verification_status = '✅ Верифицирован' if managed_user.verified else '❌ Не верифицирован'
            
            message = (
                f"👤 *Личный кабинет пользователя:*\n\n"
                f"📝 *ФИО:* {managed_user.full_name}\n"
                f"📋 *Паспорт:* {managed_user.passport or 'Не указан'}\n"
                f"💰 *Баланс:* {managed_user.balance} ₽\n"
                f"⏳ *На выводе:* {managed_user.on_hold} ₽\n"
                f"🛡️ *Верификация:* {verification_status}\n"
                f"🆔 *ID:* {managed_user.user_id}"
            )
            
            await query.edit_message_text(
                message, 
                reply_markup=get_admin_user_management_keyboard(),
                parse_mode='Markdown'
            )
    
    elif data == "admin_withdrawals":
        await show_admin_withdrawals(update, context)
    
    elif data.startswith("admin_withdrawal_"):
        request_id = int(data.split("_")[2])
        requests = get_withdrawal_requests()
        request = next((r for r in requests if r.request_id == request_id), None)
        
        if request:
            user = get_user_from_json(request.user_id)
            context.user_data['current_withdrawal_request'] = request
            context.user_data['state'] = ADMIN_WITHDRAWAL_DETAIL
            
            message = (
                f"💸 *Заявка на вывод*\n\n"
                f"👤 *От:* {user.full_name if user else 'Неизвестный пользователь'}\n"
                f"💰 *Сумма вывода:* {request.amount} ₽\n"
                f"📋 *Реквизиты:* {request.details}"
            )
            
            await query.edit_message_text(
                message, 
                reply_markup=get_withdrawal_management_keyboard(request_id),
                parse_mode='Markdown'
            )
    
    elif data.startswith("approve_withdrawal_"):
        request_id = int(data.split("_")[2])
        request = context.user_data.get('current_withdrawal_request')
        
        if request and request.request_id == request_id:
            user = get_user_from_json(request.user_id)
            if user:

                user.on_hold -= request.amount
                save_user_to_json(user)
            

            requests = get_withdrawal_requests()
            for req in requests:
                if req.request_id == request_id:
                    req.status = "approved"
                    break
            

            with open(JSON_WITHDRAWALS_FILE, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)
            
            #удаление заявки из context.user_data / removing an application from context.user_data
            if 'current_withdrawal_request' in context.user_data:
                del context.user_data['current_withdrawal_request']
            

            try:
                await context.bot.send_message(
                    chat_id=request.user_id,
                    text=f"✅ *Ваша заявка на вывод {request.amount} ₽ одобрена!*",
                    parse_mode='Markdown'
                )
            except:
                pass
            
            #возврат в меню управления / return to the control menu
            context.user_data['state'] = ADMIN_MENU
            await query.message.reply_text(
                "👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:",
                reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS),
                parse_mode='Markdown'
            )
    
    elif data.startswith("reject_withdrawal_"):
        request_id = int(data.split("_")[2])
        request = context.user_data.get('current_withdrawal_request')
        
        if request and request.request_id == request_id:
            user = get_user_from_json(request.user_id)
            if user:
                user.on_hold -= request.amount
                user.balance += request.amount  #возврат денег на баланс / refund of money to the balance
                save_user_to_json(user)
            

            requests = get_withdrawal_requests()
            for req in requests:
                if req.request_id == request_id:
                    req.status = "rejected"
                    break
            

            with open(JSON_WITHDRAWALS_FILE, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)
            
            #удаление заявки из context.user_data / removing an application from context.user_data
            if 'current_withdrawal_request' in context.user_data:
                del context.user_data['current_withdrawal_request']
            
            #уведомление юзеру / notification to the user
            try:
                await context.bot.send_message(
                    chat_id=request.user_id,
                    text=f"❌ *Ваша заявка на вывод {request.amount} ₽ отклонена.*\n\n💰 *Средства возвращены на баланс.*",
                    parse_mode='Markdown'
                )
            except:
                pass
            

            context.user_data['state'] = ADMIN_MENU
            await query.message.reply_text(
                "👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:",
                reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS),
                parse_mode='Markdown'
            )
    
    elif data == "admin_deposits":
        await show_admin_deposits(update, context)
    
    elif data.startswith("admin_deposit_"):
        request_id = int(data.split("_")[2])
        requests = get_deposit_requests()
        request = next((r for r in requests if r.request_id == request_id), None)
        
        if request:
            user = get_user_from_json(request.user_id)
            context.user_data['current_deposit_request'] = request
            context.user_data['state'] = ADMIN_DEPOSIT_DETAIL
            
            message = (
                f"💰 *Заявка на пополнение*\n\n"
                f"👤 *От:* {user.full_name if user else 'Неизвестный пользователь'}\n"
                f"💳 *Сумма пополнения:* {request.amount} ₽"
            )
            
            await query.edit_message_text(
                message, 
                reply_markup=get_deposit_management_keyboard(request_id),
                parse_mode='Markdown'
            )
    
    elif data.startswith("approve_deposit_"):
        request_id = int(data.split("_")[2])
        request = context.user_data.get('current_deposit_request')
        
        if request and request.request_id == request_id:
            user = get_user_from_json(request.user_id)
            if user:
                user.balance += request.amount
                save_user_to_json(user)
            

            requests = get_deposit_requests()
            for req in requests:
                if req.request_id == request_id:
                    req.status = "approved"
                    break
            

            with open(JSON_DEPOSITS_FILE, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)
            

            if 'current_deposit_request' in context.user_data:
                del context.user_data['current_deposit_request']
            

            try:
                await context.bot.send_message(
                    chat_id=request.user_id,
                    text=f"✅ *Ваша заявка на пополнение {request.amount} ₽ одобрена!*\n\n💰 *Баланс пополнен.*",
                    parse_mode='Markdown'
                )
            except:
                pass
            

            context.user_data['state'] = ADMIN_MENU
            await query.message.reply_text(
                "👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:",
                reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS),
                parse_mode='Markdown'
            )
    
    elif data.startswith("reject_deposit_"):
        request_id = int(data.split("_")[2])
        request = context.user_data.get('current_deposit_request')
        
        if request and request.request_id == request_id:

            requests = get_deposit_requests()
            for req in requests:
                if req.request_id == request_id:
                    req.status = "rejected"
                    break
            

            with open(JSON_DEPOSITS_FILE, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in requests], f, ensure_ascii=False, indent=2)
            

            if 'current_deposit_request' in context.user_data:
                del context.user_data['current_deposit_request']
            

            try:
                await context.bot.send_message(
                    chat_id=request.user_id,
                    text=f"❌ *Ваша заявка на пополнение {request.amount} ₽ отклонена.*",
                    parse_mode='Markdown'
                )
            except:
                pass
            

            context.user_data['state'] = ADMIN_MENU
            await query.message.reply_text(
                "👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:",
                reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS),
                parse_mode='Markdown'
            )
    
    elif data == "admin_verifications":
        await show_admin_verifications(update, context)
    
    elif data.startswith("admin_verification_"):
        request_id = int(data.split("_")[2])
        requests = get_verification_requests()
        request = next((r for r in requests if r.request_id == request_id), None)
        
        if request:
            user = get_user_from_json(request.user_id)
            context.user_data['current_verification_request'] = request
            context.user_data['state'] = ADMIN_VERIFICATION_DETAIL
            
            message = (
                f"🛡️ *Заявка на верификацию*\n\n"
                f"👤 *От:* {user.full_name if user else 'Неизвестный пользователь'}\n"
                f"📷 *Фото паспорта:*"
            )
            
            #удаление исходного сообщение и отправка нового с фото / deleting the original message and sending a new one with a photo
            await query.delete_message()
            
            #отправка фото с текстом и клавиатурой / sending photos with text and keyboard
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=request.photo_file_id,
                caption=message,
                reply_markup=get_verification_management_keyboard(request_id),
                parse_mode='Markdown'
            )
    
    elif data.startswith("approve_verification_"):
        request_id = int(data.split("_")[2])
        request = context.user_data.get('current_verification_request')
        
        if request and request.request_id == request_id:
            user = get_user_from_json(request.user_id)
            if user:
                user.verified = True
                save_user_to_json(user)
            

            delete_verification_request(request_id)
            

            if 'current_verification_request' in context.user_data:
                del context.user_data['current_verification_request']
            

            try:
                await context.bot.send_message(
                    chat_id=request.user_id,
                    text="✅ *Ваша верификация одобрена!*\n\n🛡️ *Теперь вы верифицированный пользователь.*",
                    parse_mode='Markdown'
                )
            except:
                pass
            

            context.user_data['state'] = ADMIN_MENU
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:",
                reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS),
                parse_mode='Markdown'
            )
    
    elif data.startswith("reject_verification_"):
        request_id = int(data.split("_")[2])
        request = context.user_data.get('current_verification_request')
        
        if request and request.request_id == request_id:

            delete_verification_request(request_id)
            

            if 'current_verification_request' in context.user_data:
                del context.user_data['current_verification_request']
            

            try:
                await context.bot.send_message(
                    chat_id=request.user_id,
                    text="❌ *Ваша заявка на верификацию отклонена.*\n\n🛡️ *Вы можете подать заявку повторно.*",
                    parse_mode='Markdown'
                )
            except:
                pass
            

            context.user_data['state'] = ADMIN_MENU
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:",
                reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS),
                parse_mode='Markdown'
            )
    
    elif data == "admin_add_staff":
        context.user_data['state'] = ADMIN_ADD_STAFF
        await query.edit_message_text(
            "➕ *Добавление работника*\n\n📝 *Введите следующие данные работника:*\nФИО, id телеграмм (через запятую)\n\n*Пример:*\n`Иванов Иван Иванович, 123456789`",
            reply_markup=get_back_keyboard("admin_menu"),
            parse_mode='Markdown'
        )
    
    #обработчики для одобренных и отклоненных заявок / handlers for approved and rejected applications
    elif data == "admin_approved_requests":
        context.user_data['state'] = ADMIN_APPROVED_REQUESTS
        await query.edit_message_text(
            "✅ *Одобренные заявки*\n\n📋 *Выберите тип заявок для просмотра:*",
            reply_markup=get_approved_requests_keyboard(language),
            parse_mode='Markdown'
        )
    
    elif data == "admin_rejected_requests":
        context.user_data['state'] = ADMIN_REJECTED_REQUESTS
        await query.edit_message_text(
            "❌ *Отклоненные заявки*\n\n📋 *Выберите тип заявок для просмотра:*",
            reply_markup=get_rejected_requests_keyboard(language),
            parse_mode='Markdown'
        )
    
    elif data == "admin_approved_withdrawals":
        await show_admin_approved_withdrawals(update, context)
    
    elif data == "admin_approved_deposits":
        await show_admin_approved_deposits(update, context)
    
    elif data == "admin_rejected_withdrawals":
        await show_admin_rejected_withdrawals(update, context)
    
    elif data == "admin_rejected_deposits":
        await show_admin_rejected_deposits(update, context)
    
    elif data == "admin_back_to_approved":
        context.user_data['state'] = ADMIN_APPROVED_REQUESTS
        await query.edit_message_text(
            "✅ *Одобренные заявки*\n\n📋 *Выберите тип заявок для просмотра:*",
            reply_markup=get_approved_requests_keyboard(language),
            parse_mode='Markdown'
        )
    
    elif data == "admin_back_to_rejected":
        context.user_data['state'] = ADMIN_REJECTED_REQUESTS
        await query.edit_message_text(
            "❌ *Отклоненные заявки*\n\n📋 *Выберите тип заявок для просмотра:*",
            reply_markup=get_rejected_requests_keyboard(language),
            parse_mode='Markdown'
        )
    
    elif data == "admin_back_to_menu":
        #чистка всех временных данных о заявках / cleaning of all temporary application data
        for key in ['current_withdrawal_request', 'current_deposit_request', 'current_verification_request', 'managed_user']:
            if key in context.user_data:
                del context.user_data[key]
        
        context.user_data['state'] = ADMIN_MENU
        await query.edit_message_text(
            "👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:",
            reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS),
            parse_mode='Markdown'
        )
    
    elif data == "admin_back_to_withdrawals":
        await show_admin_withdrawals(update, context)
    
    elif data == "admin_back_to_deposits":
        await show_admin_deposits(update, context)
    
    elif data == "admin_back_to_verifications":
        await show_admin_verifications(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state', START)
    user_id = update.effective_user.id
    user = get_user_from_json(user_id)
    language = user.language if user else 'ru'
    text = update.message.text if update.message.text else ""
    
    if state == REGISTRATION_NAME:
        #сохранение ФИО и запрос паспорта / saving your full name and requesting your passport
        full_name = text
        context.user_data['registration_full_name'] = full_name
        context.user_data['state'] = REGISTRATION_PASSPORT
        
        texts = TEXTS[language]
        await update.message.reply_text(
            texts['registration_passport'],
            reply_markup=get_back_keyboard("start", language),
            parse_mode='Markdown'
        )
    
    elif state == REGISTRATION_PASSPORT:
        #завершение регистрации с паспортом / completing registration with a passport
        passport = text
        full_name = context.user_data.get('registration_full_name')
        
        user = User(user_id, full_name, passport, language=language)
        save_user_to_json(user)
        context.user_data['user'] = user
        context.user_data['state'] = PERSONAL_CABINET
        
        #чистка временных данных регистрации / cleaning temporary registration data
        if 'registration_full_name' in context.user_data:
            del context.user_data['registration_full_name']
        
        success_text = "✅ *Регистрация завершена!*" if language == 'ru' else "✅ *Registration completed!*"
        await update.message.reply_text(success_text, parse_mode='Markdown')
        await show_personal_cabinet(update, context)
    
    elif state == DEPOSIT:
        #обработка пополнения / deposit processing
        try:
            amount = float(text.strip())
            
            if amount <= 0:
                error_text = "❌ *Сумма должна быть положительной*" if language == 'ru' else "❌ *Amount must be positive*"
                await update.message.reply_text(error_text, parse_mode='Markdown')
                return
            
            #заявка на пополнение / request for replenishment
            requests = get_deposit_requests()
            request_id = len(requests) + 1
            request = DepositRequest(request_id, user_id, amount)
            save_deposit_request(request)
            
            success_text = "✅ *Заявка успешно отправлена!*" if language == 'ru' else "✅ *Request successfully sent!*"
            await update.message.reply_text(success_text, parse_mode='Markdown')
            context.user_data['state'] = PERSONAL_CABINET
            await show_personal_cabinet(update, context)
            
        except ValueError:
            error_text = "❌ *Неверный формат суммы.*\n\n💡 *Введите число, например:* `1500`" if language == 'ru' else "❌ *Invalid amount format.*\n\n💡 *Enter a number, for example:* `1500`"
            await update.message.reply_text(error_text, parse_mode='Markdown')
    
    elif state == WITHDRAWAL:
        #обработка вывода / output processing
        try:
            parts = text.split(',')
            if len(parts) < 2:
                error_text = "❌ *Пожалуйста, укажите реквизиты и сумму через запятую*" if language == 'ru' else "❌ *Please provide details and amount separated by comma*"
                await update.message.reply_text(error_text, parse_mode='Markdown')
                return
            
            details = parts[0].strip()
            amount = float(parts[1].strip())
            
            user_obj = context.user_data.get('user', get_user_from_json(user_id))
            
            if amount <= 0:
                error_text = "❌ *Сумма должна быть положительной*" if language == 'ru' else "❌ *Amount must be positive*"
                await update.message.reply_text(error_text, parse_mode='Markdown')
                return
            
            if amount > user_obj.balance:
                error_text = "❌ *Недостаточно средств на балансе*" if language == 'ru' else "❌ *Insufficient balance*"
                await update.message.reply_text(error_text, parse_mode='Markdown')
                return
            

            user_obj.balance -= amount
            user_obj.on_hold += amount
            save_user_to_json(user_obj)
            
            requests = get_withdrawal_requests()
            request_id = len(requests) + 1
            request = WithdrawalRequest(request_id, user_id, amount, details)
            save_withdrawal_request(request)
            
            success_text = "✅ *Заявка успешно отправлена!*" if language == 'ru' else "✅ *Request successfully sent!*"
            await update.message.reply_text(success_text, parse_mode='Markdown')
            context.user_data['state'] = PERSONAL_CABINET
            await show_personal_cabinet(update, context)
            
        except ValueError:
            error_text = "❌ *Неверный формат.*\n\n💡 *Пожалуйста, используйте формат:* `реквизиты, сумма`" if language == 'ru' else "❌ *Invalid format.*\n\n💡 *Please use format:* `details, amount`"
            await update.message.reply_text(error_text, parse_mode='Markdown')
    
    elif state == VERIFICATION:
        #верификация / verefication 
        if update.message.photo:
            #отправка фото паспорта / sending a passport photo
            photo_file_id = update.message.photo[-1].file_id
            user_obj = context.user_data.get('user', get_user_from_json(user_id))
            

            requests = get_verification_requests()
            request_id = len(requests) + 1
            request = VerificationRequest(request_id, user_id, photo_file_id)
            save_verification_request(request)
            
            success_text = "✅ *Заявка на верификацию отправлена!*\n\n⏳ *Ожидайте одобрения.*" if language == 'ru' else "✅ *Verification request sent!*\n\n⏳ *Please wait for approval.*"
            await update.message.reply_text(success_text, parse_mode='Markdown')
            context.user_data['state'] = PERSONAL_CABINET
            await show_personal_cabinet(update, context)
        else:
            error_text = "❌ *Пожалуйста, отправьте фото паспорта*" if language == 'ru' else "❌ *Please send passport photo*"
            await update.message.reply_text(error_text, parse_mode='Markdown')
    
    elif state == ADMIN_CHANGE_NAME:
        #смена ФИО юзера админом / changing the user's full name by the admin
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            new_full_name = text
            managed_user.full_name = new_full_name
            save_user_to_json(managed_user)
            
            await update.message.reply_text(f"✅ *ФИО пользователя изменено на:* {new_full_name}", parse_mode='Markdown')
            context.user_data['state'] = ADMIN_USER_DETAIL
            
            verification_status = '✅ Верифицирован' if managed_user.verified else '❌ Не верифицирован'
            
            message = (
                f"👤 *Личный кабинет пользователя:*\n\n"
                f"📝 *ФИО:* {managed_user.full_name}\n"
                f"📋 *Паспорт:* {managed_user.passport or 'Не указан'}\n"
                f"💰 *Баланс:* {managed_user.balance} ₽\n"
                f"⏳ *На выводе:* {managed_user.on_hold} ₽\n"
                f"🛡️ *Верификация:* {verification_status}\n"
                f"🆔 *ID:* {managed_user.user_id}"
            )
            
            await update.message.reply_text(
                message, 
                reply_markup=get_admin_user_management_keyboard(),
                parse_mode='Markdown'
            )
    
    elif state == ADMIN_CHANGE_PASSPORT: 
        #cмена номера паспорта юзера админом / changing the user's passport number by the admin
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            new_passport = text
            managed_user.passport = new_passport
            save_user_to_json(managed_user)
            
            await update.message.reply_text(f"✅ *Паспортные данные пользователя изменены на:* {new_passport}", parse_mode='Markdown')
            context.user_data['state'] = ADMIN_USER_DETAIL
            
            verification_status = '✅ Верифицирован' if managed_user.verified else '❌ Не верифицирован'
            
            message = (
                f"👤 *Личный кабинет пользователя:*\n\n"
                f"📝 *ФИО:* {managed_user.full_name}\n"
                f"📋 *Паспорт:* {managed_user.passport or 'Не указан'}\n"
                f"💰 *Баланс:* {managed_user.balance} ₽\n"
                f"⏳ *На выводе:* {managed_user.on_hold} ₽\n"
                f"🛡️ *Верификация:* {verification_status}\n"
                f"🆔 *ID:* {managed_user.user_id}"
            )
            
            await update.message.reply_text(
                message, 
                reply_markup=get_admin_user_management_keyboard(),
                parse_mode='Markdown'
            )
    
    elif state == ADMIN_ADD_BALANCE:
        #пополнение баланса админом / adding funds to the account by the admin
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            try:
                amount = float(text.strip())
                
                if amount <= 0:
                    error_text = TEXTS[language]['invalid_amount']
                    await update.message.reply_text(error_text, parse_mode='Markdown')
                    return
                

                old_balance = managed_user.balance
                managed_user.balance += amount
                save_user_to_json(managed_user)
                

                try:
                    user_language = managed_user.language
                    notification_text = TEXTS[user_language]['balance_added'].format(
                        new_balance=managed_user.balance,
                        amount=amount
                    )
                    
                    await context.bot.send_message(
                        chat_id=managed_user.user_id,
                        text=notification_text,
                        parse_mode='Markdown'
                    )
                except:
                    pass
                

                success_text = TEXTS[language]['balance_added'].format(
                    new_balance=managed_user.balance,
                    amount=amount
                )
                await update.message.reply_text(success_text, parse_mode='Markdown')
                

                context.user_data['state'] = ADMIN_USER_DETAIL
                
                verification_status = '✅ Верифицирован' if managed_user.verified else '❌ Не верифицирован'
                
                message = (
                    f"👤 *Личный кабинет пользователя:*\n\n"
                    f"📝 *ФИО:* {managed_user.full_name}\n"
                    f"📋 *Паспорт:* {managed_user.passport or 'Не указан'}\n"
                    f"💰 *Баланс:* {managed_user.balance} ₽\n"
                    f"⏳ *На выводе:* {managed_user.on_hold} ₽\n"
                    f"🛡️ *Верификация:* {verification_status}\n"
                    f"🆔 *ID:* {managed_user.user_id}"
                )
                
                await update.message.reply_text(
                    message, 
                    reply_markup=get_admin_user_management_keyboard(),
                    parse_mode='Markdown'
                )
                
            except ValueError:
                error_text = TEXTS[language]['invalid_amount']
                await update.message.reply_text(error_text, parse_mode='Markdown')
    
    elif state == ADMIN_REDUCE_BALANCE:
        #уменьшение баланса админом / reducing the balance by the admin
        managed_user = context.user_data.get('managed_user')
        if managed_user:
            try:
                amount = float(text.strip())
                
                if amount <= 0:
                    error_text = TEXTS[language]['invalid_amount']
                    await update.message.reply_text(error_text, parse_mode='Markdown')
                    return
                
                if amount > managed_user.balance:
                    error_text = TEXTS[language]['insufficient_balance'].format(
                        balance=managed_user.balance,
                        amount=amount
                    )
                    await update.message.reply_text(error_text, parse_mode='Markdown')
                    return
                

                old_balance = managed_user.balance
                managed_user.balance -= amount
                save_user_to_json(managed_user)
                

                try:
                    user_language = managed_user.language
                    notification_text = TEXTS[user_language]['balance_reduced'].format(
                        new_balance=managed_user.balance,
                        amount=amount
                    )
                    
                    await context.bot.send_message(
                        chat_id=managed_user.user_id,
                        text=notification_text,
                        parse_mode='Markdown'
                    )
                except:
                    pass
                

                success_text = TEXTS[language]['balance_reduced'].format(
                    new_balance=managed_user.balance,
                    amount=amount
                )
                await update.message.reply_text(success_text, parse_mode='Markdown')
                

                context.user_data['state'] = ADMIN_USER_DETAIL
                
                verification_status = '✅ Верифицирован' if managed_user.verified else '❌ Не верифицирован'
                
                message = (
                    f"👤 *Личный кабинет пользователя:*\n\n"
                    f"📝 *ФИО:* {managed_user.full_name}\n"
                    f"📋 *Паспорт:* {managed_user.passport or 'Не указан'}\n"
                    f"💰 *Баланс:* {managed_user.balance} ₽\n"
                    f"⏳ *На выводе:* {managed_user.on_hold} ₽\n"
                    f"🛡️ *Верификация:* {verification_status}\n"
                    f"🆔 *ID:* {managed_user.user_id}"
                )
                
                await update.message.reply_text(
                    message, 
                    reply_markup=get_admin_user_management_keyboard(),
                    parse_mode='Markdown'
                )
                
            except ValueError:
                error_text = TEXTS[language]['invalid_amount']
                await update.message.reply_text(error_text, parse_mode='Markdown')
    
    elif state == ADMIN_ADD_STAFF:
        #добавление работника / adding an employee
        try:
            parts = text.split(',')
            if len(parts) < 2:
                await update.message.reply_text("❌ *Пожалуйста, укажите ФИО и ID через запятую*", parse_mode='Markdown')
                return
            
            full_name = parts[0].strip()
            staff_id = int(parts[1].strip())
            
            add_staff_to_json(staff_id, full_name)
            await update.message.reply_text(f"✅ *Работник {full_name} (ID: {staff_id}) успешно добавлен!*", parse_mode='Markdown')
            context.user_data['state'] = ADMIN_MENU
            
            await update.message.reply_text(
                "👨‍💼 *Добро пожаловать в меню управления*\n\nВыберите действие которое хотите выполнить:",
                reply_markup=get_admin_menu_keyboard(user_id in ADMIN_IDS),
                parse_mode='Markdown'
            )
            
        except ValueError:
            await update.message.reply_text("❌ *Неверный формат.*\n\n💡 *Пожалуйста, используйте формат:* `ФИО, ID`", parse_mode='Markdown')

def main():

    init_json_files()
    

    application = Application.builder().token("YOUR TOKEN HERE").build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    print("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()