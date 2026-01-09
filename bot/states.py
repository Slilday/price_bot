from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    waiting_for_link_to_add = State()
    waiting_for_link_to_delete = State()
    waiting_for_link_history = State()
    waiting_for_new_name = State() 
    waiting_for_target_price = State()