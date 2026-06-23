from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    selecting_language = State()
    waiting_coupon = State()
    waiting_receipt = State()
    ticket_subject = State()
    ticket_message = State()
    wallet_topup_amount = State()
    wallet_topup_receipt = State()
    apple_id = State()
    apple_password = State()
    apple_birthday = State()
    apple_security = State()
    apple_photo_imei = State()
    apple_photo_about = State()
    apple_photo_box = State()
    apple_payment_receipt = State()


class AddAccountStates(StatesGroup):
    username = State()
    password = State()
    note = State()
    plan = State()


class EditAccountStates(StatesGroup):
    username = State()
    password = State()
    note = State()


class AddPlanStates(StatesGroup):
    name = State()
    price = State()
    days = State()


class EditPlanStates(StatesGroup):
    name = State()
    price = State()
    days = State()


class AddCouponStates(StatesGroup):
    code = State()
    discount = State()
    limit = State()


class EditCouponStates(StatesGroup):
    code = State()
    discount = State()
    limit = State()


class AddTutorialStates(StatesGroup):
    platform = State()
    title = State()
    content = State()


class EditTutorialStates(StatesGroup):
    platform = State()
    title = State()
    content = State()


class AdminStates(StatesGroup):
    new_admin_id = State()
    setting_value = State()
    broadcast_text = State()
    ticket_reply = State()
    account_search = State()
    editing_terms = State()
    send_message_to_user = State()
    edit_message_key = State()
    apple_set_price = State()
    apple_set_time = State()