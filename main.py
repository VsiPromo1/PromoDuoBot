from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler
import sqlite3

# === Налаштування ===
TOKEN = '7851351005:AAED62F63BRh20of2RBXxFfBR82JV44wclQ'
CHANNELS = ['@Vsi_PROMO', '@uaclub_casinoman']
REWARD_PER_REF = 4
WITHDRAW_LIMIT = 100
admin_id = 7262164512

# === База даних ===
conn = sqlite3.connect('promo_duo.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    invited_by INTEGER,
    balance INTEGER DEFAULT 0
)
""")
conn.commit()

# === Меню кнопок ===
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("👥 Запросити друзів")],
        [KeyboardButton("💰 Баланс"), KeyboardButton("📤 Вивід")]
    ],
    resize_keyboard=True
)

# === Перевірка підписки ===
def check_subscriptions(user_id, context):
    for channel in CHANNELS:
        member = context.bot.get_chat_member(channel, user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            return False
    return True

# === /start ===
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = user.id
    args = context.args

    if not check_subscriptions(user_id, context):
        buttons = [[InlineKeyboardButton("Підписатись на канал", url=ch)] for ch in CHANNELS]
        update.message.reply_text(
            "Підпишись на всі канали, щоб користуватись ботом:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if args:
        inviter_id = int(args[0])
        if inviter_id != user_id:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (user_id, invited_by, balance) VALUES (?, ?, 0)", (user_id, inviter_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (REWARD_PER_REF, inviter_id))
                conn.commit()
    else:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

    context.bot.send_message(
        chat_id=user_id,
        text=(
            f"Привіт, {user.first_name}!"
            
            f"Запрошуй друзів та отримуй по {REWARD_PER_REF} грн за кожного!"
            
            f"Твоє посилання: https://t.me/PromoDuoBot?start={user_id}"
        ),
        reply_markup=main_menu
    )

# === Баланс ===
def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    bal = row[0] if row else 0
    msg = f"Ваш баланс: {bal} грн"
    
    if bal >= WITHDRAW_LIMIT:
        msg += "✅ Ви можете вивести кошти. Натисніть '📤 Вивід'"
    else:
        msg += f"🔒 Вивід доступний при {WITHDRAW_LIMIT} грн"
    update.message.reply_text(msg, reply_markup=main_menu)

# === Вивід ===
def withdraw(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    bal = row[0] if row else 0
    if bal < WITHDRAW_LIMIT:
        update.message.reply_text("🔒 Виведення доступне при 100 грн", reply_markup=main_menu)
        return
    update.message.reply_text("💳 Введіть номер картки або платіжної системи для виплати", reply_markup=main_menu)

# === Повідомлення з реквізитами ===
def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "👥 Запросити друзів":
        link = f"https://t.me/PromoDuoBot?start={user_id}"
        update.message.reply_text(f"Ваше реферальне посилання:
{link}", reply_markup=main_menu)
        return
    elif text == "💰 Баланс":
        balance(update, context)
        return
    elif text == "📤 Вивід":
        withdraw(update, context)
        return

    # Інакше - обробка реквізитів
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] >= WITHDRAW_LIMIT:
        context.bot.send_message(
            admin_id,
            f"🔔 Запит на виведення"
            
            f"👤 @{update.effective_user.username}"
            
            f"ID: {user_id}"
            
            f"💰 Сума: {row[0]} грн"
            
            f"📤 Реквізити: {text}"
        )
        update.message.reply_text("✅ Заявка на виплату надіслана адміну. Очікуйте підтвердження!", reply_markup=main_menu)

# === Основний запуск ===
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("withdraw", withdraw))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
