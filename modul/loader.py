from aiogram.client.session.aiohttp import AiohttpSession
from aiogram import Router, Bot, Dispatcher

bot_session = AiohttpSession()
# from shazamio import Shazam

main_bot = Bot(token="6746881064:AAFeVCH1odRrxqqHLkBKvW39wABT3PO37-w", session=bot_session)
dp = Dispatcher()

client_bot_router = Router()
main_bot_router = Router()

dp.include_router(client_bot_router)
dp.include_router(main_bot_router)
# shazam = Shazam()/
