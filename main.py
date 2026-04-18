import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("❌ BOT_TOKEN или GEMINI_API_KEY не найдены!")

# ✅ Убраны устаревшие настройки безопасности, которые ломали бот
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={"temperature": 0.3, "max_output_tokens": 1500}
)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
DISCLAIMER = "\n⚠️ **ESLATMA:** Bu ma'lumotlar faqat tanishuv uchun. Dori qabul qilishdan oldin shifokor yoki farmatsevt bilan maslahatlashing."

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
        if image_bytes:
            from google.generativeai.types import Part
            image_part = Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            response = await asyncio.to_thread(model.generate_content, [image_part, prompt])
        else:
            response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip() + DISCLAIMER
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        return f"️ AI xizmati vaqtincha ishlamayapti.\n\n{str(e)[:100]}" + DISCLAIMER

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Assalomu alaykum! Men **Dori haqida** botman.\n\n💊 Tugmalardan foydalaning.", reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "search_name")
async def cb_search_name(callback: types.CallbackQuery):
    await callback.message.answer("💊 Dori nomini yozing (masalan: Paratsetamol, Ibuprofen...)")
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
        await message.answer("❌ Suratni tahlil qilishda xatolik." + DISCLAIMER)

@dp.message(F.text & ~F.photo)
async def handle_text(message: types.Message):
    if message.text.startswith("/"): return
    await bot.send_chat_action(message.chat.id, "typing")
    if "," in message.text and len(message.text.split(",")) >= 2:
        prompt = f"Dorilar birgalikda qo'llanilsa nima bo'ladi? Xavf, nojo'ya ta'sirlar, ehtiyot choralari: {message.text}"
    elif any(w in message.text.lower() for w in ["belgi", "og'riq", "harorat", "yo'tal", "alomat"]):
        prompt = f"Belgilar: {message.text}. Mumkin bo'lgan holatlar, qachon shifokorga borish kerak."
    else:
        prompt = f"'{message.text}' haqida to'liq ma'lumot ber: tarkibi, qo'llanilishi, dozasi, nojo'ya ta'sirlari, kontrendikatsiyalari."
    response = await get_ai_response(prompt)
    await message.answer(response, parse_mode="Markdown")

@dp.callback_query(F.data.in_({"check_interaction", "check_symptoms"}))
async def cb_input(callback: types.CallbackQuery):
    txt = "🔄 2 yoki undan ortiq dori nomini vergul bilan yozing:\n`Aspirin, Ibuprofen`" if callback.data == "check_interaction" else "🤒 Belgilaringizni yozing:\n`32 yosh, bosh og'rig'i, harorat 38`"
    await callback.message.answer(txt, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "emergency")
async def cb_emergency(callback: types.CallbackQuery):
    await callback.message.answer("🚑 **Shoshilinch raqamlar (O'zbekiston):**\n📞 103 – Tez yordam\n 112 – Yagona qutqaruv\n\n⚠️ Og'ir holatda darhol shifoxonaga boring!", parse_mode="Markdown")
    await callback.answer()

@dp.errors()
async def error_handler(event: types.ErrorEvent):
    logging.exception(f"Bot xatosi: {event.exception}")

async def main():
    print("✅ Dori haqida bot ishga tushdi...")
    logging.info("✅ Bot started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
