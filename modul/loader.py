from aiogram.client.session.aiohttp import AiohttpSession
from aiogram import Router, Bot, Dispatcher

bot_session = AiohttpSession()
# from shazamio import Shazam

main_bot = Bot(token="6463653390:AAFCmUhro2O-FpGcTwlAlUIu_R3_Pq24WJ0", session=bot_session)
dp = Dispatcher()

client_bot_router = Router()
main_bot_router = Router()

# shazam = Shazam()/
