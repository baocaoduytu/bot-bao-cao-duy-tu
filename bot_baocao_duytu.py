import os
import pickle
import datetime
import asyncio
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_NHOM = int(os.getenv("CHAT_ID_NHOM"))
CHAT_ID_CANHAN = int(os.getenv("CHAT_ID_CANHAN"))

STATE_FILE = "state.pkl"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "rb") as f:
            return pickle.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "wb") as f:
        pickle.dump(state, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot duy tu đã sẵn sàng.")

def upload_to_drive(file_path, folder_name):
    creds = Credentials.from_authorized_user_file('token_drive.pickle', ['https://www.googleapis.com/auth/drive'])
    drive_service = build('drive', 'v3', credentials=creds)

    folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    folder_id = folder.get('id')

    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"Uploaded file {file_path} to Google Drive in folder {folder_name}.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != CHAT_ID_NHOM:
        return

    text = update.message.text.lower().strip() if update.message.text else ""
    photo = update.message.photo[-1] if update.message.photo else None
    video = update.message.video if update.message.video else None

    state = load_state()
    user_id = update.message.from_user.id

    is_bat_dau = "bat dau" in text or "bắt đầu" in text
    is_ket_thuc = "ket thuc" in text or "kết thúc" in text

    now = datetime.datetime.now().strftime("%Hh%M_%d-%m-%Y")

    if is_bat_dau:
        state[user_id] = {
            "bat_dau": text,
            "photo_file_id": photo.file_id if photo else None,
            "video_file_id": video.file_id if video else None
        }
        save_state(state)

        await context.bot.forward_message(chat_id=CHAT_ID_CANHAN, from_chat_id=CHAT_ID_NHOM, message_id=update.message.message_id)
        await context.bot.send_message(chat_id=CHAT_ID_CANHAN, text="📌 Đã forward tin nhắn bắt đầu.")

        if photo:
            file = await photo.get_file()
            path = f"{now}_batdau.jpg"
            await file.download_to_drive(path)
            upload_to_drive(path, folder_name=f"DuyTu_{now}")
            os.remove(path)

        if video:
            file = await video.get_file()
            path = f"{now}_batdau.mp4"
            await file.download_to_drive(path)
            upload_to_drive(path, folder_name=f"DuyTu_{now}")
            os.remove(path)

    elif is_ket_thuc and user_id in state:
        bat_dau_text = state[user_id]["bat_dau"]
        ket_thuc_text = text

        combined_text = f"{bat_dau_text}\n{ket_thuc_text}"
        await context.bot.send_message(chat_id=CHAT_ID_CANHAN, text=f"📋 Tổng hợp:\n{combined_text}")

        if photo:
            file = await photo.get_file()
            path = f"{now}_ketthuc.jpg"
            await file.download_to_drive(path)
            upload_to_drive(path, folder_name=f"DuyTu_{now}")
            os.remove(path)

        if video:
            file = await video.get_file()
            path = f"{now}_ketthuc.mp4"
            await file.download_to_drive(path)
            upload_to_drive(path, folder_name=f"DuyTu_{now}")
            os.remove(path)

        del state[user_id]
        save_state(state)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("✅ Bot báo cáo duy tu Railway đang chạy...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
