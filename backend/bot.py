import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ВСТАВЬ СЮДА НОВЫЙ ТОКЕН ОТ BOTFATHER
BOT_TOKEN = "PASTE_NEW_TOKEN_HERE"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
LINKS_FILE = os.path.join(BASE_DIR, "telegram_links.json")

# Код привязки пациента к боту
PATIENT_CODES = {
    "ABC123": 1
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": [], "patients": [], "iol_calculations": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_links():
    if not os.path.exists(LINKS_FILE):
        return {}
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_links(links):
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


def find_patient(patient_id: int):
    data = load_data()
    for patient in data.get("patients", []):
        if patient.get("id") == patient_id:
            return patient
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if not args:
        await update.message.reply_text(
            "Здравствуйте! Я бот Oculus MD.\n"
            "Чтобы привязать пациента, отправьте:\n"
            "/start ABC123"
        )
        return

    code = args[0].strip()
    patient_id = PATIENT_CODES.get(code)

    if not patient_id:
        await update.message.reply_text("Код не найден.")
        return

    patient = find_patient(patient_id)
    if not patient:
        await update.message.reply_text("Пациент не найден в системе.")
        return

    links = load_links()
    links[str(update.effective_chat.id)] = patient_id
    save_links(links)

    await update.message.reply_text(
        f"Пациент {patient['full_name']} успешно привязан.\n"
        "Теперь доступны команды:\n"
        "/status\n"
        "/remind"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links = load_links()
    patient_id = links.get(str(update.effective_chat.id))

    if not patient_id:
        await update.message.reply_text("Сначала привяжите пациента через /start ABC123")
        return

    patient = find_patient(int(patient_id))
    if not patient:
        await update.message.reply_text("Пациент не найден.")
        return

    status_map = {
        "red": "Требуется консультация хирурга",
        "yellow": "Идет подготовка",
        "green": "Пациент готов к операции"
    }

    patient_status = patient.get("status", "yellow")
    status_text = status_map.get(patient_status, "Идет подготовка")

    await update.message.reply_text(
        f"Пациент: {patient['full_name']}\n"
        f"Статус: {status_text}\n"
        f"Диагноз: {patient.get('diagnosis_icd10', '-')}\n\n"
        f"Этап 1: Анализы — завершено\n"
        f"Этап 2: Проверка хирургом — ожидание\n"
        f"Этап 3: Операция — не назначена"
    )


async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    links = load_links()
    patient_id = links.get(str(update.effective_chat.id))

    if not patient_id:
        await update.message.reply_text("Сначала привяжите пациента через /start ABC123")
        return

    await update.message.reply_text(
        "Напоминание: завтра сдайте кровь натощак."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("remind", remind))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()