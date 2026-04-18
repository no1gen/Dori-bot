import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai

# 🔹 Настройка логирования (видно в Railway)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🔹 Загрузка переменных из Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("❌ BOT_TOKEN или GEMINI_API_KEY не найдены в переменных Railway!")

#  Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={"temperature": 0.3, "max_output_tokens": 1500},
)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

DISCLAIMER = "\n⚠️ **ESLATMA:** Bu ma'lumotlar faqat tanishuv uchun. Dori qabul qilishdan oldin shifokor yoki farmatsevt bilan maslahatlashing. O'z-o'zingizni davolamang."

def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💊 Dori nomi bo'yicha qidirish", callback_data="search_name")],
        [InlineKeyboardButton(text=" Suratdan dori tahlili", callback_data="search_photo")],
        [InlineKeyboardButton(text="🔄 Dori o'zaro ta'siri", callback_data="check_interaction")],
        [InlineKeyboardButton(text="🤒 Belgilarni tekshirish", callback_data="check_symptoms")],
        [InlineKeyboardButton(text="📞 Shoshilinch yordam", callback_data="emergency")]
    ])

async def get_ai_response(prompt: str, image_bytes: bytes = None):
    try:
        parts = [{"text": prompt}]
        if image_bytes:
            parts.append({"mime_type": "image/jpeg", "data": image_bytes})
        response = await asyncio.to_thread(model.generate_content, parts)
        return response.text.strip() + DISCLAIMER
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        return "❌ Server xatosi. Iltimos, qayta urinib ko'ring." + DISCLAIMER

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        " Assalomu alaykum! Men **Dori haqida** botman.\n\n"
        "💊 Dori haqida ma'lumot, suratdan tahlil, dori mosligi va belgilarni tekshirish uchun tugmalardan foydalaning.",
        reply_markup=get_main_keyboard(), parse_mode="Markdown"
    )

@dp.callback_query(F.data == "search_name")
async def cb_search_name(callback: types.CallbackQuery):
    await callback.message.answer(" Dori nomini yozing (masalan: Paratsetamol, Ibuprofen...)")
    await callback.answer()

@dp.callback_query(F.data == "search_photo")
async def cb_search_photo(callback: types.CallbackQuery):
    await callback.message.answer(" Dori qutisi yoki tabletkasining aniq suratini yuboring.")
    await callback.answer()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        photo = message.photo[-1]
        file = await bot.download(photo.file_id)
        image_bytes = file.read()
        prompt = "Bu suratdagi dori vositasini aniqla va to'liq ma'lumot ber: nomi, tarkibi, qo'llanilishi, dozasi, nojo'ya ta'sirlari, kontrendikatsiyalari va muqobillari."
        response = await get_ai_response(prompt, image_bytes)
        await message.answer(response, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Photo error: {e}")
        await message.answer("❌ Suratni tahlil qilishda xatolik. Iltimos, aniqroq rasm yuboring." + DISCLAIMER)

@dp.message(F.text & ~F.photo)
async def handle_text(message: types.Message):
    if message.text.startswith("/"): return
    await bot.send_chat_action(message.chat.id, "typing")

    # Автоматическое определение типа запроса
    if "," in message.text and len(message.text.split(",")) >= 2:
        prompt = f"Dorilar birgalikda qo'llanilsa nima bo'ladi? Xavf, nojo'ya ta'sirlar, ehtiyot choralari: {message.text}"
    elif any(word in message.text.lower() for word in ["belgi", "og'riq", "harorat", "yo'tal", "alomat", "kasallik"]):
        prompt = f"Belgilar: {message.text}. Mumkin bo'lgan holatlar, qachon shifokorga borish kerak, o'z-o'zini davolashdan ogohlantirish."
    else:
        prompt = f"Foydalanuvchi '{message.text}' haqida so'ramoqda. Dori sifatida tahlil qiling va batafsil ma'lumot bering."

    response = await get_ai_response(prompt)
    await message.answer(response, parse_mode="Markdown")

@dp.callback_query(F.data == "check_interaction")
async def cb_interaction(callback: types.CallbackQuery):
    await callback.message.answer("🔄 2 yoki undan ortiq dori nomini vergul bilan yozing:\n`Aspirin, Ibuprofen`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "check_symptoms")
async def cb_symptoms(callback: types.CallbackQuery):
    await callback.message.answer("🤒 Belgilaringizni yozing:\n`32 yosh, bosh og'rig'i, harorat 38`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "emergency")
async def cb_emergency(callback: types.CallbackQuery):
    await callback.message.answer(
        "🚑 **Shoshilinch raqamlar (O'zbekiston):**\n📞 103 – Tez yordam\n 112 – Yagona qutqaruv\n\n⚠️ Og'ir holatda darhol shifoxonaga boring!",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.errors()
async def error_handler(event: types.ErrorEvent):
    logging.exception(f"Bot xatosi: {event.exception}")

async def main():
    print("✅ Dori haqida bot ishga tushdi...")
    logging.info("✅ Bot started successfully! Waiting for messages...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
