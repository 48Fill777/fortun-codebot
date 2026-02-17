import telebot
from telebot import types
import openpyxl
from openpyxl import Workbook, load_workbook
from datetime import datetime
import os
import json
import time
import re

# ====== ДАННЫЕ САЛОНА ======
BOT_TOKEN = '8518012585:AAHeQiyFUyhj-BC8Su59yrmAuvU-Eek4AHM'
ADMIN_ID = 896372173
SALON_NAME = "Студия красоты “KİVİ”"
SALON_PHONE = "+7 (985) 699-17-77"
SALON_ADDRESS = "м. Пятницкое шоссе, Ангелов переулок, дом 2"
SALON_HOURS = "Без выходных с 10:00 до 22:00"
SALON_BOOKING_URL = "https://n1610700.yclients.com"
SALON_TELEGRAM = "@kivi_mitino"
WEB_APP_URL = "https://48fill777.github.io/wheel-of-fortune/"
# =============================

bot = telebot.TeleBot(BOT_TOKEN)

# Сбрасываем вебхук (важно для polling)
bot.remove_webhook()
time.sleep(1)

EXCEL_FILE = 'clients_data.xlsx'

# Инициализация Excel
def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws_clients = wb.active
        ws_clients.title = "Клиенты"
        headers = ["telegram_id", "username", "full_name", "phone", "prize", "win_date", "is_used"]
        ws_clients.append(headers)
        wb.save(EXCEL_FILE)

init_excel()

def has_user_spun(telegram_id):
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Клиенты"]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is not None and int(row[0]) == telegram_id:
            return True
    return False

def add_spin_record(telegram_id, username, full_name, prize):
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Клиенты"]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is not None and int(row[0]) == telegram_id:
            return False
    ws.append([telegram_id, username, full_name, "", prize, datetime.now().isoformat(), 0])
    wb.save(EXCEL_FILE)
    return True

def update_phone(telegram_id, phone):
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Клиенты"]
    for i, row in enumerate(ws.iter_rows(min_row=2), start=2):
        cell_value = row[0].value
        if cell_value is not None and int(cell_value) == telegram_id:
            ws.cell(row=i, column=4).value = phone
            wb.save(EXCEL_FILE)
            return True
    return False

def get_user_record(telegram_id):
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Клиенты"]
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row[0] is not None and int(row[0]) == telegram_id:
            return i, row
    return None, None

def validate_phone(phone):
    phone = re.sub(r'\D', '', phone)
    return len(phone) in (10, 11)

def format_phone(phone):
    phone = re.sub(r'\D', '', phone)
    if len(phone) == 11:
        phone = phone[1:]
    return f"+7 ({phone[:3]}) {phone[3:6]}-{phone[6:8]}-{phone[8:]}"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    spun = has_user_spun(user_id)
    url = WEB_APP_URL + ("?already_spun=1" if spun else "")
    print(f"[DEBUG] /start для {user_id}, spun={spun}")

    # Reply-кнопка для открытия колеса
    markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_button = types.KeyboardButton(
        text="🎡 Крутить колесо!",
        web_app=types.WebAppInfo(url=url)
    )
    markup_reply.add(web_app_button)

    # Приветственное сообщение
    bot.send_message(
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
        f"Подарок действителен в течение 30 дней.",
        reply_markup=markup_reply
    )

    # Inline-кнопки (контакты, запись, мой выигрыш)
    markup_inline = types.InlineKeyboardMarkup(row_width=2)
    btn_contacts = types.InlineKeyboardButton('📞 Контакты', callback_data='contacts')
    btn_booking = types.InlineKeyboardButton('📅 Записаться онлайн', url=SALON_BOOKING_URL)
    btn_prize = types.InlineKeyboardButton('🎁 Мой выигрыш', callback_data='my_prize')
    markup_inline.add(btn_contacts, btn_booking, btn_prize)

    bot.send_message(
        message.chat.id,
        "Наши контакты и запись:",
        reply_markup=markup_inline
    )

@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    print(f"✅ ПОЛУЧЕНЫ WEB_APP_DATA: {message.web_app_data.data}")
    try:
        data = json.loads(message.web_app_data.data)
        prize_name = data['prize']
        user_id = message.from_user.id
        username = message.from_user.username or ""
        full_name = message.from_user.full_name

        if has_user_spun(user_id):
            bot.send_message(message.chat.id, "❌ Вы уже участвовали.")
            return

        if add_spin_record(user_id, username, full_name, prize_name):
            bot.send_message(ADMIN_ID, f"🎉 Новый выигрыш: {prize_name} от {full_name} (@{username})")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('📱 Оставить номер', callback_data='enter_phone'))
            bot.send_message(
                message.chat.id,
                f"🎉 Вы выиграли: {prize_name}!\n\nНажмите кнопку, чтобы оставить номер.",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "❌ Ошибка сохранения.")
    except Exception as e:
        print(f"[ERROR] {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'enter_phone')
def phone_request(call):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton('📱 Отправить номер', request_contact=True))
    bot.send_message(call.message.chat.id, "📱 Отправьте номер телефона:", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number
    formatted = format_phone(phone)
    if update_phone(message.from_user.id, formatted):
        _, record = get_user_record(message.from_user.id)
        prize = record[4] if record else "приз"
        bot.send_message(ADMIN_ID, f"📞 Получен номер: {formatted} (приз: {prize})")
        bot.send_message(
            message.chat.id,
            f"✅ Спасибо! Ваш номер {formatted} сохранён. Администратор свяжется с вами.",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        bot.send_message(message.chat.id, "❌ Ошибка. Начните заново /start")

@bot.message_handler(func=lambda m: m.text and m.text[0].isdigit())
def manual_phone(message):
    phone = message.text.strip()
    if validate_phone(phone):
        formatted = format_phone(phone)
        if update_phone(message.from_user.id, formatted):
            _, record = get_user_record(message.from_user.id)
            prize = record[4] if record else "приз"
            bot.send_message(ADMIN_ID, f"📞 Получен номер (вручную): {formatted} (приз: {prize})")
            bot.send_message(message.chat.id, f"✅ Спасибо! Номер {formatted} сохранён.")
        else:
            bot.send_message(message.chat.id, "❌ Сначала нужно выиграть приз. /start")
    else:
        bot.send_message(message.chat.id, "❌ Неверный формат. Пример: +79991234567")

@bot.message_handler(commands=['my_prize'])
def my_prize_command(message):
    user_id = message.from_user.id
    _, record = get_user_record(user_id)
    print(f"[DEBUG] my_prize для {user_id}, record={record}")
    if record:
        status = "✅ Активирован" if record[6] == 1 else "⏳ Ожидает"
        bot.send_message(
            message.chat.id,
            f"🎁 Ваш приз: {record[4]}\nСтатус: {status}"
        )
    else:
        bot.send_message(message.chat.id, "❌ Вы ещё не участвовали.")

@bot.callback_query_handler(func=lambda call: call.data == 'my_prize')
def my_prize_callback(call):
    my_prize_command(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'contacts')
def show_contacts(call):
    text = f"""
📞 Контакты студии “KİVİ”

📍 Адрес: {SALON_ADDRESS}
🕐 Режим работы: {SALON_HOURS}
📱 Телефон: {SALON_PHONE}
💬 Telegram: {SALON_TELEGRAM}
    """
    # Без parse_mode, чтобы избежать ошибок форматирования
    bot.send_message(call.message.chat.id, text)
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
        types.InlineKeyboardButton('📋 Все клиенты', callback_data='admin_all')
    )
    bot.send_message(message.chat.id, "🔧 АДМИН-ПАНЕЛЬ", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_stats')
def admin_stats(call):
    if call.from_user.id != ADMIN_ID:
        return
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Клиенты"]
    total = ws.max_row - 1
    with_phone = 0
    used = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[3]:
            with_phone += 1
        if row[6] == 1:
            used += 1
    text = f"""
📊 СТАТИСТИКА

👥 Всего участников: {total}
📞 Оставили номер: {with_phone}
✅ Обслужено: {used}
    """
    bot.send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_no_phone')
def admin_no_phone(call):
    if call.from_user.id != ADMIN_ID:
        return
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Клиенты"]
    text = "⏳ ОЖИДАЮТ НОМЕР ТЕЛЕФОНА:\n\n"
    found = False
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[3]:
            found = True
            text += f"👤 {row[2]} (@{row[1]})\n🆔 {row[0]}\n🎁 {row[4]}\n📅 {row[5][:16]}\n\n"
    if not found:
        text = "✅ Все клиенты оставили номер."
    bot.send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_pending')
def admin_pending(call):
    if call.from_user.id != ADMIN_ID:
        return
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Клиенты"]
    text = "⏳ ОЖИДАЮТ СВЯЗИ (есть номер, не обслужены):\n\n"
    found = False
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[3] and row[6] == 0:
            found = True
            text += f"👤 {row[2]} (@{row[1]})\n📞 {row[3]}\n🎁 {row[4]}\n📅 {row[5][:16]}\n\n"
    if not found:
        text = "✅ Нет ожидающих связи."
    bot.send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_all')
def admin_all(call):
    if call.from_user.id != ADMIN_ID:
        return
    wb = load_workbook(EXCEL_FILE)
    ws = wb["Клиенты"]
    text = "📋 ВСЕ КЛИЕНТЫ:\n\n"
    for row in ws.iter_rows(min_row=2, values_only=True):
        phone = row[3] if row[3] else "не указан"
        status = "✅" if row[6] == 1 else "⏳"
        text += f"{status} {row[2]} (@{row[1]}) 📞 {phone}\n🎁 {row[4]}\n\n"
    if ws.max_row == 1:
        text = "Пока нет клиентов."
    bot.send_message(call.message.chat.id, text)
    bot.answer_callback_query(call.id)

# Обработчик для обращений к админу
@bot.message_handler(commands=['call_admin'])
def call_admin(message):
    bot.send_message(ADMIN_ID, f"🔔 Клиент {message.from_user.full_name} (@{message.from_user.username}) просит помощи!")
    bot.send_message(message.chat.id, "✅ Запрос отправлен администратору.")

# Запуск бота с авто-перезапуском
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