# from aiogram import Bot, Dispatcher
# import asyncio
# from modul.clientbot.handlers.refs.handlers.bot import bot_router
# from modul.clientbot.handlers.refs.handlers.admin import admin_router
# from database import Base, engine
# # TODO токен
# bot = Bot(token="TOKEN")
# dp = Dispatcher()
# Base.metadata.create_all(bind=engine)
# from database.otherservice import *
#
# # TODO это нужно убрать после теста

#
# async def main():
#     dp.include_router(bot_router)
#     dp.include_router(admin_router)
#     await dp.start_polling(bot)
#
#
# if __name__ == '__main__':
#     asyncio.run(main())