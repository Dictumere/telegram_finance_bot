from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import os
from sheets import get_sheet, add_expense, get_summary
from dotenv import load_dotenv
load_dotenv()


API_TELEGRAM_TOKEN = os.environ['API_TELEGRAM_TOKEN']
SELECT_GROUP, SELECT_CATEGORY, ENTER_AMOUNT, ENTER_DAY = range(4)
CATEGORIES = {
    "Обязательные расходы": [
        "Городской транспорт",
        "Продукты питания",
        "Мобильная связь и интернет",
        "Здоровье",
        "Подписки",
        "Английский",
        "Обучение-БА"
    ],
    "Отдых и развлечение": [
        "Спорт",
        "Такси",
        "Еда (фастфуд, сладости и тд)",
        "Прочее"
    ],
    "Накопление и кредиты": [
        "Ноутбук",
        "Обучение-SMM",
        "Долг",
        "Копилка"
    ]
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! Я бот учёта финансов 💸\n\n"
        "Доступные команды:\n"
        "/start — приветствие\n"
        "/help — список команд\n"
        "/add — добавить трату\n"
        "/test — проверить подключение к таблице"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Команды: /start /help /add /test")


# 🔹 Вот эта функция — проверка Google Sheets
async def test_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet("Финансы")  # Укажи точное название таблицы!
        await update.message.reply_text("✅ Успешно подключено к таблице!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        ["Обязательные расходы"],
        ["Отдых и развлечение"],
        ["Накопление и кредиты"]
    ]
    await update.message.reply_text(
        "Выбери группу расходов:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_GROUP


async def select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group = update.message.text
    context.user_data["group"] = group

    categories = CATEGORIES.get(group)
    if not categories:
        await update.message.reply_text("Что-то пошло не так. Попробуй снова.")
        return ConversationHandler.END

    reply_keyboard = [[cat] for cat in categories]  # делаем кнопки по одной в строке
    await update.message.reply_text(
        "Теперь выбери категорию:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SELECT_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    context.user_data["category"] = category

    await update.message.reply_text(
        f"Отлично, теперь введи сумму траты (в рублях):",
        reply_markup=ReplyKeyboardRemove()
    )
    return ENTER_AMOUNT


async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", "."))  # поддержка запятых
        context.user_data["amount"] = amount
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи число. Попробуй ещё раз.")
        return ENTER_AMOUNT

    await update.message.reply_text("Теперь введи число месяца (от 26 до 25):")
    return ENTER_DAY


async def enter_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    day = update.message.text
    context.user_data["day"] = day

    # Выводим всё, что собрали
    text = (
        f"✅ Добавим запись:\n"
        f"Группа: {context.user_data['group']}\n"
        f"Категория: {context.user_data['category']}\n"
        f"Сумма: {context.user_data['amount']}₽\n"
        f"Число месяца: {context.user_data['day']}"
    )
    await update.message.reply_text(text)
    await update.message.reply_text("Записываю данные в таблицу...")

    try:
        add_expense(
            sheet_title="Финансы",           # Название Google Sheets
            month_sheet="Апрель",            # Название листа
            category=context.user_data["category"],
            day=day,
            amount=context.user_data["amount"]
        )
        await update.message.reply_text("✅ Успешно записано в таблицу!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при записи: {e}")
    try:
        total, group_rest, daily = get_summary(
            sheet_title="Финансы",
            month_sheet="Апрель",
            group=context.user_data["group"],
            day=day
        )

        await update.message.reply_text(
            f"✅ Трата добавлена в категорию {context.user_data['category']} за {day} число.\n\n"
            f"💰 Общий остаток: {total}₽\n"
            f"📦 Остаток по группе: {group_rest}₽\n"
            f"📅 Потрачено за день: {daily}₽"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Запись прошла, но не удалось получить статистику: {e}")

    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token(API_TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("test", test_sheet))  # добавляем обработчик

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            SELECT_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_group)],
            SELECT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_category)],
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            ENTER_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_day)],

            # остальные шаги добавим позже
        },
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    app.run_polling()


if __name__ == "__main__":
    main()
