from aiogram.fsm.state import State, StatesGroup

class ProfileCreation(StatesGroup):
    entering_name = State()
    entering_description = State()
    entering_prompt = State()

class ProfileEditing(StatesGroup):
    selecting_profile = State()
    selecting_field = State()
    entering_new_value = State()
