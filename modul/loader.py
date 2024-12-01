from aiogram.client.session.aiohttp import AiohttpSession
from aiogram import Router, Bot, Dispatcher

bot_session = AiohttpSession()
# from shazamio import Shazam

main_bot = Bot(token="7400666200:AAE0q92yJUwJ-FVdAq88HK2HBjo7vOqX3_0", session=bot_session)
dp = Dispatcher()

client_bot_router = Router()
main_bot_router = Router()

# shazam = Shazam()/
