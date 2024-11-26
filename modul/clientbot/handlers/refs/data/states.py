from aiogram.fsm.state import State, StatesGroup


class PaymentState(StatesGroup):
    get_card = State()
    get_bank = State()


class ChangeAdminInfo(StatesGroup):
    get_amount = State()
    get_min = State()
    get_channel_id = State()
    get_channel_url = State()
    delete_channel = State()
    mailing = State()
    imp = State()
    change_balance = State()
    add_balance = State()
    change_refs = State()
