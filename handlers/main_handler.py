from aiogram import types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import InputFile
from aiogram.fsm.context import FSMContext
from bs4 import BeautifulSoup
from keyboards.keyboards import *
from config.config import CBR_URL, EXCHANGERATE_API
import aiohttp

router = Router() 

async def fetch_cbr_rates():
    """Получение курсов валют с ЦБ РФ с полной обработкой ошибок"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CBR_URL, timeout=10) as response:
                if response.status != 200:
                    print(f"HTTP error: {response.status}")
                    return None
                
                xml = await response.text()
                if not xml:
                    print("Empty response from CBR")
                    return None

                try:
                    soup = BeautifulSoup(xml, 'lxml-xml')
                    if not soup:
                        print("Failed to parse XML")
                        return None
                except Exception as e:
                    print(f"XML parsing error: {e}")
                    return None

                valutes = soup.find_all('Valute')
                if not valutes:
                    print("No valutes found in XML")
                    return None

                rates = {}
                date = None
                
                # Получаем дату курсов
                val_curs = soup.find('ValCurs')
                if val_curs and hasattr(val_curs, 'attrs'):
                    date = val_curs.attrs.get('Date', 'неизвестная дата')

                for valute in valutes:
                    try:
                        # Безопасное извлечение данных
                        charcode_elem = valute.find('CharCode')
                        value_elem = valute.find('Value')
                        nominal_elem = valute.find('Nominal')

                        if not all([charcode_elem, value_elem, nominal_elem]):
                            continue

                        charcode = charcode_elem.text.strip() if charcode_elem.text else None
                        value_text = value_elem.text.replace(',', '.') if value_elem.text else None
                        nominal_text = nominal_elem.text.strip() if nominal_elem.text else None

                        if not all([charcode, value_text, nominal_text]):
                            continue

                        try:
                            value = float(value_text)
                            nominal = int(nominal_text)
                            if nominal == 0:
                                continue  # избегаем деления на 0
                            rates[charcode] = value / nominal
                        except (ValueError, TypeError) as e:
                            print(f"Conversion error for {charcode}: {e}")
                            continue

                    except Exception as e:
                        print(f"Error processing valute: {e}")
                        continue

                if not rates:
                    print("No valid currency rates found")
                    return None

                return {'date': date, 'rates': rates}

    except aiohttp.ClientError as e:
        print(f"Network error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return None

async def fetch_crypto_rates():
    """Получение курсов криптовалют"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd,rub"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'BTC': {'USD': data['bitcoin']['usd'], 'RUB': data['bitcoin']['rub']},
                    'ETH': {'USD': data['ethereum']['usd'], 'RUB': data['ethereum']['rub']}
                }
            return None

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для отслеживания курсов валют.\n"
        "Выбери валюту или нажми /help для списка команд.",
        reply_markup=main_keyboard
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "Доступные команды:\n"
        "/start - начать работу\n"
        "/help - эта справка\n"
        "/usd - курс доллара\n"
        "/eur - курс евро\n"
        "/all - все курсы ЦБ\n"
        "/crypto - курсы криптовалют\n"
        "Или используйте кнопки на клавиатуре"
    )
    await message.answer(help_text)

@router.message(Command("usd"))
@router.message(F.text.lower() == "usd")
@router.message(F.text.lower() == "доллар")
async def cmd_usd(message: types.Message):
    rates_data = await fetch_cbr_rates()
    if rates_data:
        usd_rate = rates_data['rates'].get('USD')
        await message.answer(
            f"Курс USD на {rates_data['date']}:\n"
            f"1 USD = {usd_rate:.2f} RUB"
        )
    else:
        await message.answer("Не удалось получить курс. Попробуйте позже.")

@router.message(Command("eur"))
@router.message(F.text.lower() == "eur")
@router.message(F.text.lower() == "евро")
async def cmd_eur(message: types.Message):
    rates_data = await fetch_cbr_rates()
    if rates_data:
        eur_rate = rates_data['rates'].get('EUR')
        await message.answer(
            f"Курс EUR на {rates_data['date']}:\n"
            f"1 EUR = {eur_rate:.2f} RUB"
        )
    else:
        await message.answer("Не удалось получить курс. Попробуйте позже.")


@router.message(Command("all"))
@router.message(F.text.lower() == "все курсы")
@router.message(F.text.lower() == "курсы")
async def cmd_all(message: types.Message):
    rates_data = await fetch_cbr_rates()
    if rates_data:
        response = [f"Курсы валют ЦБ РФ на {rates_data['date']}:"]
        for code, rate in rates_data['rates'].items():
            response.append(f"{code}: {rate:.4f} RUB")
        
        for i in range(0, len(response), 5):
            await message.answer("\n".join(response[i:i+5]))
    else:
        await message.answer("Не удалось получить курсы. Попробуйте позже.")

@router.message(Command("crypto"))
@router.message(F.text.lower() == "криптовалюты")
@router.message(F.text.lower() == "crypto")
async def cmd_crypto(message: types.Message):
    crypto_data = await fetch_crypto_rates()
    if crypto_data:
        response = [
            "Курсы криптовалют:",
            f"BTC: {crypto_data['BTC']['USD']} USD / {crypto_data['BTC']['RUB']} RUB",
            f"ETH: {crypto_data['ETH']['USD']} USD / {crypto_data['ETH']['RUB']} RUB",
            "Данные предоставлены CoinGecko"
        ]
        await message.answer("\n".join(response))
    else:
        await message.answer("Не удалось получить курсы криптовалют. Попробуйте позже.")