import os
import telebot
from telebot import types
from datetime import datetime
import json
import time
import re
import csv
from telebot.apihelper import ApiTelegramException
import xlsxwriter
from io import BytesIO

# ====== СЕКРЕТНЫЕ ДАННЫЕ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ======
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в переменных окружения!")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не задан в переменных окружения!")
# =====================================================

# ====== ПУБЛИЧНЫЕ ДАННЫЕ САЛОНА ======
SALON_NAME = "Студия красоты “KİVİ”"
SALON_PHONE = "+7 (985) 699-17-77"
SALON_ADDRESS = "м. Пятницкое шоссе, Ангелов переулок, дом 2"
SALON_HOURS = "Без выходных с 10:00 до 22:00"
SALON_BOOKING_URL = "https://n1610700.yclients.com"
SALON_TELEGRAM = "@kivi_mitino"
WEB_APP_URL = "https://48fill777.github.io/wheel-of-fortune/"
# Ссылки на документы
RULES_URL = "https://disk.yandex.ru/i/TJ4ayDJPKidNxA"
PRIVACY_URL = "https://dcdb62b0-570c-474e-a103-d4e125b05553.selstorage.ru/%D0%9F%D0%BE%D0%BB%D0%B8%D1%82%D0%B8%D0%BA%D0%B0%20%D0%BE%D0%B1%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%BA%D0%B8%20%D0%BF%D0%B5%D1%80%20%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85.pdf"
# ======================================

bot = telebot.TeleBot(BOT_TOKEN)

# Функция безопасной отправки сообщений (обрабатывает блокировку бота пользователем)
def safe_send_message(chat_id, text, **kwargs):
    try:
        bot.send_message(chat_id, text, **kwargs)
    except ApiTelegramException as e:
        if e.error_code == 403:
            print(f"⚠️ Пользователь {chat_id} заблокировал бота, сообщение не отправлено")
        else:
            print(f"⚠️ Ошибка Telegram API при отправке {chat_id}: {e}")
    except Exception as e:
        print(f"❌ Критическая ошибка при отправке {chat_id}: {e}")
        raise

# Сбрасываем вебхук (важно для polling)
bot.remove_webhook()
time.sleep(1)

# ====== РАБОТА С CSV-ФАЙЛОМ ======
CSV_FILE = 'clients_data.csv'  # При необходимости измените путь (например, '/app/data/clients_data.csv')
CSV_HEADERS = ["telegram_id", "username", "full_name", "phone", "prize", "win_date", "is_used", "agreed"]

# Создаём файл с заголовками, если его нет
def init_csv():
    try:
        with open(CSV_FILE, 'x', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
    except FileExistsError:
        pass  # файл уже есть - ничего не делаем

init_csv()

# Проверяем, крутил ли пользователь колесо
def has_user_spun(telegram_id):
    with open(CSV_FILE, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['telegram_id'] and int(row['telegram_id']) == telegram_id:
                return True
    return False

# Проверяем, дал ли пользователь согласие
def has_user_agreed(telegram_id):
    try:
        with open(CSV_FILE, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['telegram_id'] and int(row['telegram_id']) == telegram_id:
                    return row.get('agreed') == '1'
    except FileNotFoundError:
        pass
    return False

# Создаёт запись о согласии (если её ещё нет)
def create_agreement_record(telegram_id, username, full_name):
    if has_user_agreed(telegram_id):
        return True
    with open(CSV_FILE, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([telegram_id, username, full_name, "", "", "", 0, 1])
    return True

# Обновляет запись после выигрыша (добавляет приз и дату)
def add_spin_record(telegram_id, username, full_name, prize):
    # Проверяем, не крутил ли уже
    if has_user_spun(telegram_id):
        return False

    rows = []
    updated = False
    with open(CSV_FILE, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if row and int(row[0]) == telegram_id:
                # Это запись о согласии – обновляем, добавляя приз
                while len(row) < 8:
                    row.append('')
                row[4] = prize
                row[5] = datetime.now().isoformat()
                # row[7] (agreed) уже должен быть 1, но на всякий случай
                row[7] = '1'
                updated = True
            rows.append(row)

    if updated:
        with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        return True
    else:
        # Если записи о согласии не было (маловероятно) – создаём новую
        with open(CSV_FILE, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([telegram_id, username, full_name, "", prize, datetime.now().isoformat(), 0, 1])
        return True

# Обновляем номер телефона пользователя
def update_phone(telegram_id, phone):
    rows = []
    updated = False
    with open(CSV_FILE, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if row and int(row[0]) == telegram_id:
                while len(row) < 8:
                    row.append('')
                row[3] = phone
                updated = True
            rows.append(row)
    if updated:
        with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
    return updated

# Получаем запись пользователя по его ID (возвращает номер строки и список)
def get_user_record(telegram_id):
    try:
        with open(CSV_FILE, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            next(reader)  # пропускаем заголовки
            for i, row in enumerate(reader, start=2):
                if not row:
                    continue
                try:
                    if int(row[0]) == telegram_id:
                        # Дополняем строку до 8 элементов, если нужно
                        while len(row) < 8:
                            row.append('')
                        return i, row
                except (ValueError, IndexError):
                    continue
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[ERROR] в get_user_record: {e}")
    return None, None

# Получаем все записи из CSV (для админки и экспорта)
def get_all_records():
    with open(CSV_FILE, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        records = list(reader)
        # Дополняем каждую запись недостающими ключами (на случай старого файла)
        for r in records:
            for h in CSV_HEADERS:
                if h not in r:
                    r[h] = ''
        return records

# Проверка формата телефона
def validate_phone(phone):
    phone = re.sub(r'\D', '', phone)
    return len(phone) in (10, 11)

# Форматирование телефона в красивый вид
def format_phone(phone):
    phone = re.sub(r'\D', '', phone)
    if len(phone) == 11:
        phone = phone[1:]
    return f"+7 ({phone[:3]}) {phone[3:6]}-{phone[6:8]}-{phone[8:]}"

# ====== ОБРАБОТЧИКИ КОМАНД ======

# Команда /start (теперь с проверкой согласия)
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name

    # Если пользователь ещё не дал согласие
    if not has_user_agreed(user_id):
        text = (
            f"🌟 Добро пожаловать в Студию красоты “KİVİ”! 🌟\n\n"
            f"Перед участием обязательно ознакомьтесь с [правилами акции]({RULES_URL}) "
            f"и [Политикой обработки персональных данных]({PRIVACY_URL}).\n\n"
            f"После ознакомления нажмите кнопку ниже, чтобы подтвердить согласие и получить доступ к колесу фортуны."
        )
        markup = types.InlineKeyboardMarkup()
        agree_button = types.InlineKeyboardButton('✅ Ознакомлен и согласен', callback_data='agree')
        markup.add(agree_button)
        safe_send_message(
            message.chat.id,
            text,
            reply_markup=markup,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        return

    # Если согласие уже есть – показываем полное приветствие с кнопкой колеса
    spun = has_user_spun(user_id)
    url = WEB_APP_URL + ("?already_spun=1" if spun else "")
    print(f"[DEBUG] /start для {user_id}, spun={spun}, agreed=True")

    # Reply-кнопка для открытия колеса
    markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_button = types.KeyboardButton(
        text="🎡 Крутить колесо!",
        web_app=types.WebAppInfo(url=url)
    )
    markup_reply.add(web_app_button)

    # Полное приветствие
    safe_send_message(
        message.chat.id,
        f"🌟 Добро пожаловать в Студию красоты “KİVİ”! 🌟\n\n"
        f"Мы дарим подарки каждому новому клиенту!\n"
        f"Крутите колесо фортуны и выигрывайте:\n\n"
        f"💅 Дизайн ногтей\n"
        f"🧴 СПА для рук/ног\n"
        f"💰 Скидка 10%\n"
        f"💆 Массаж воротниковой зоны\n"
        f"💎 Депозит 1 000 руб.\n"
        f"👑 Депозит 10 000 руб.\n\n"
        f"🎯 Для активации подарка потребуется номер телефона.\n"
        f"Обратите внимание: участвовать можно только один раз!\n"
        f"Подарок действителен в течение 30 дней.\n\n"
        f"Нажимая кнопку ниже, вы подтверждаете, что ознакомились с [правилами акции]({RULES_URL}) и [политикой обработки данных]({PRIVACY_URL}).",
        reply_markup=markup_reply,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

    # Inline-кнопки (контакты, запись, мой выигрыш)
    markup_inline = types.InlineKeyboardMarkup(row_width=2)
    btn_contacts = types.InlineKeyboardButton('📞 Контакты', callback_data='contacts')
    btn_booking = types.InlineKeyboardButton('📅 Записаться онлайн', url=SALON_BOOKING_URL)
    btn_prize = types.InlineKeyboardButton('🎁 Мой выигрыш', callback_data='my_prize')
    markup_inline.add(btn_contacts, btn_booking, btn_prize)

    safe_send_message(
        message.chat.id,
        "Наши контакты и запись:",
        reply_markup=markup_inline
    )

# Обработчик кнопки "Ознакомлен и согласен"
@bot.callback_query_handler(func=lambda call: call.data == 'agree')
def agree_callback(call):
    user_id = call.from_user.id
    username = call.from_user.username or ""
    full_name = call.from_user.full_name

    if create_agreement_record(user_id, username, full_name):
        bot.answer_callback_query(call.id, "✅ Спасибо! Теперь вы можете крутить колесо.", show_alert=False)
        # Перенаправляем на /start, чтобы показать полное меню
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка. Попробуйте позже.", show_alert=True)

# Обработка данных из веб-приложения (колесо)
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    print(f"✅ ПОЛУЧЕНЫ WEB_APP_DATA: {message.web_app_data.data}")
    try:
        data = json.loads(message.web_app_data.data)
        prize_name = data['prize']
        user_id = message.from_user.id
        username = message.from_user.username or ""
        full_name = message.from_user.full_name

        # Проверяем согласие (на всякий случай)
        if not has_user_agreed(user_id):
            safe_send_message(message.chat.id, "❌ Сначала нужно принять условия в /start")
            return

        if has_user_spun(user_id):
            safe_send_message(message.chat.id, "❌ Вы уже участвовали.")
            return

        if add_spin_record(user_id, username, full_name, prize_name):
            safe_send_message(ADMIN_ID, f"🎉 Новый выигрыш: {prize_name} от {full_name} (@{username})")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('📱 Оставить номер', callback_data='enter_phone'))
            safe_send_message(
                message.chat.id,
                f"🎉 Вы выиграли: {prize_name}!\n\nНажмите кнопку, чтобы оставить номер.",
                reply_markup=markup
            )
        else:
            safe_send_message(message.chat.id, "❌ Ошибка сохранения.")
    except Exception as e:
        print(f"[ERROR] {e}")

# Кнопка "Оставить номер"
@bot.callback_query_handler(func=lambda call: call.data == 'enter_phone')
def phone_request(call):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton('📱 Отправить номер', request_contact=True))
    safe_send_message(call.message.chat.id, "📱 Отправьте номер телефона:", reply_markup=markup)
    bot.answer_callback_query(call.id)

# Обработка полученного контакта
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number
    formatted = format_phone(phone)
    if update_phone(message.from_user.id, formatted):
        _, record = get_user_record(message.from_user.id)
        prize = record[4] if record else "приз"
        safe_send_message(ADMIN_ID, f"📞 Получен номер: {formatted} (приз: {prize})")
        safe_send_message(
            message.chat.id,
            f"✅ Спасибо! Ваш номер {formatted} сохранён. Администратор свяжется с вами.",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        safe_send_message(message.chat.id, "❌ Ошибка. Начните заново /start")

# Ручной ввод телефона
@bot.message_handler(func=lambda m: m.text and m.text[0].isdigit())
def manual_phone(message):
    phone = message.text.strip()
    if validate_phone(phone):
        formatted = format_phone(phone)
        if update_phone(message.from_user.id, formatted):
            _, record = get_user_record(message.from_user.id)
            prize = record[4] if record else "приз"
            safe_send_message(ADMIN_ID, f"📞 Получен номер (вручную): {formatted} (приз: {prize})")
            safe_send_message(message.chat.id, f"✅ Спасибо! Номер {formatted} сохранён.")
        else:
            safe_send_message(message.chat.id, "❌ Сначала нужно выиграть приз. /start")
    else:
        safe_send_message(message.chat.id, "❌ Неверный формат. Пример: +79991234567")

# Команда /my_prize (текстовая)
@bot.message_handler(commands=['my_prize'])
def my_prize_command(message):
    user_id = message.from_user.id
    print(f"[DEBUG] my_prize для {user_id}")

    row_num, record = get_user_record(user_id)
    print(f"[DEBUG] row_num={row_num}, record={record}")

    if record:
        status = "✅ Активирован" if record[6] == '1' else "⏳ Ожидает"
        safe_send_message(
            message.chat.id,
            f"🎁 Ваш приз: {record[4]}\nСтатус: {status}"
        )
    else:
        safe_send_message(message.chat.id, "❌ Вы ещё не участвовали.")

# Кнопка "Мой выигрыш" (инлайн)
@bot.callback_query_handler(func=lambda call: call.data == 'my_prize')
def my_prize_callback(call):
    my_prize_command(call.message)
    bot.answer_callback_query(call.id)

# Кнопка "Контакты"
@bot.callback_query_handler(func=lambda call: call.data == 'contacts')
def show_contacts(call):
    text = f"""
📞 Контакты студии “KİVİ”

📍 Адрес: {SALON_ADDRESS}
🕐 Режим работы: {SALON_HOURS}
📱 Телефон: {SALON_PHONE}
💬 Telegram: {SALON_TELEGRAM}
    """
    safe_send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

# Админ-панель (команда /admin)
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('📊 Статистика', callback_data='admin_stats'),
        types.InlineKeyboardButton('⏳ Ожидают номера', callback_data='admin_no_phone'),
        types.InlineKeyboardButton('📞 Ожидают связи', callback_data='admin_pending'),
        types.InlineKeyboardButton('📋 Все клиенты', callback_data='admin_all'),
        types.InlineKeyboardButton('📥 Экспорт в Excel', callback_data='admin_export')
    )
    safe_send_message(message.chat.id, "🔧 АДМИН-ПАНЕЛЬ", reply_markup=markup)

# Статистика (админ)
@bot.callback_query_handler(func=lambda call: call.data == 'admin_stats')
def admin_stats(call):
    if call.from_user.id != ADMIN_ID:
        return
    records = get_all_records()
    total = len(records)
    with_phone = sum(1 for r in records if r['phone'])
    used = sum(1 for r in records if r['is_used'] == '1')
    agreed = sum(1 for r in records if r.get('agreed') == '1')
    text = f"""
📊 СТАТИСТИКА

👥 Всего участников: {total}
📞 Оставили номер: {with_phone}
✅ Обслужено: {used}
👍 Дали согласие: {agreed}
    """
    safe_send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

# Ожидают номер (админ)
@bot.callback_query_handler(func=lambda call: call.data == 'admin_no_phone')
def admin_no_phone(call):
    if call.from_user.id != ADMIN_ID:
        return
    records = get_all_records()
    text = "⏳ ОЖИДАЮТ НОМЕР ТЕЛЕФОНА:\n\n"
    found = False
    for r in records:
        if not r['phone']:
            found = True
            text += f"👤 {r['full_name']} (@{r['username']})\n🆔 {r['telegram_id']}\n🎁 {r['prize']}\n📅 {r['win_date'][:16]}\n\n"
    if not found:
        text = "✅ Все клиенты оставили номер."
    safe_send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

# Ожидают связи (админ)
@bot.callback_query_handler(func=lambda call: call.data == 'admin_pending')
def admin_pending(call):
    if call.from_user.id != ADMIN_ID:
        return
    records = get_all_records()
    text = "⏳ ОЖИДАЮТ СВЯЗИ (есть номер, не обслужены):\n\n"
    found = False
    for r in records:
        if r['phone'] and r['is_used'] == '0':
            found = True
            text += f"👤 {r['full_name']} (@{r['username']})\n📞 {r['phone']}\n🎁 {r['prize']}\n📅 {r['win_date'][:16]}\n\n"
    if not found:
        text = "✅ Нет ожидающих связи."
    safe_send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

# Все клиенты (админ)
@bot.callback_query_handler(func=lambda call: call.data == 'admin_all')
def admin_all(call):
    if call.from_user.id != ADMIN_ID:
        return
    records = get_all_records()
    text = "📋 ВСЕ КЛИЕНТЫ:\n\n"
    for r in records:
        phone = r['phone'] if r['phone'] else "не указан"
        status = "✅" if r['is_used'] == '1' else "⏳"
        agreed = "✅" if r.get('agreed') == '1' else "❌"
        text += f"{status} {r['full_name']} (@{r['username']}) 📞 {phone}\n🎁 {r['prize']} | Согласие: {agreed}\n\n"
    if not records:
        text = "Пока нет клиентов."
    safe_send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

# Обработчик для экспорта (кнопка)
@bot.callback_query_handler(func=lambda call: call.data == 'admin_export')
def admin_export_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав администратора", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    send_export(call.message.chat.id)

# Команда для обращения к админу
@bot.message_handler(commands=['call_admin'])
def call_admin(message):
    safe_send_message(ADMIN_ID, f"🔔 Клиент {message.from_user.full_name} (@{message.from_user.username}) просит помощи!")
    safe_send_message(message.chat.id, "✅ Запрос отправлен администратору.")

# ====== ФУНКЦИЯ ЭКСПОРТА В EXCEL ======
def send_export(chat_id):
    try:
        records = get_all_records()
        if not records:
            safe_send_message(chat_id, "Нет данных для экспорта.")
            return

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Клиенты')

        # Заголовки с учётом нового столбца
        headers = ['ID', 'Username', 'Имя', 'Телефон', 'Приз', 'Дата выигрыша', 'Использовано', 'Согласие']
        for col, h in enumerate(headers):
            worksheet.write(0, col, h)

        for row_idx, r in enumerate(records, start=1):
            worksheet.write(row_idx, 0, int(r['telegram_id']) if r['telegram_id'] else '')
            worksheet.write(row_idx, 1, r['username'])
            worksheet.write(row_idx, 2, r['full_name'])
            worksheet.write(row_idx, 3, r['phone'])
            worksheet.write(row_idx, 4, r['prize'])
            worksheet.write(row_idx, 5, r['win_date'])
            worksheet.write(row_idx, 6, 'Да' if r['is_used'] == '1' else 'Нет')
            worksheet.write(row_idx, 7, 'Да' if r.get('agreed') == '1' else 'Нет')

        workbook.close()
        output.seek(0)

        bot.send_document(
            chat_id,
            output,
            visible_file_name='clients_data.xlsx',
            caption='📊 Экспорт данных клиентов'
        )
    except Exception as e:
        safe_send_message(chat_id, f"❌ Ошибка при создании Excel: {e}")

# ====== КОМАНДА ЭКСПОРТА ======
@bot.message_handler(commands=['export'])
def export_to_excel(message):
    if message.from_user.id != ADMIN_ID:
        return
    send_export(message.chat.id)

# ====== ТЕСТОВАЯ КОМАНДА ДЛЯ CSV ======
@bot.message_handler(commands=['testcsv'])
def test_csv(message):
    try:
        with open('test.csv', 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Привет мир', 'Клиент: Тест Тестов'])
        bot.reply_to(message, "✅ Файл test.csv создан. Скачайте и откройте в Excel.")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ====== ОТЛАДОЧНАЯ КОМАНДА (ПОКАЗЫВАЕТ СОДЕРЖИМОЕ CSV) ======
@bot.message_handler(commands=['debug_csv'])
def debug_csv(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        if len(content) > 1500:
            content = content[:1500] + "\n... (обрезано)"
        safe_send_message(message.chat.id, f"```\n{content}\n```", parse_mode='Markdown')
    except Exception as e:
        safe_send_message(message.chat.id, f"Ошибка: {e}")

# ====== ЗАПУСК БОТА ======
if __name__ == '__main__':
    print(f"🚀 Бот для салона '{SALON_NAME}' запущен!")
    print(f"👤 Администратор ID: {ADMIN_ID}")
    print(f"📞 Телефон: {SALON_PHONE}")
    print(f"📍 Адрес: {SALON_ADDRESS}")
    print("Ожидание данных...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=30)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}, перезапуск через 5 сек...")
            time.sleep(5)
