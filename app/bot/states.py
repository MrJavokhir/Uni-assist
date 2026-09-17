from aiogram.fsm.state import State, StatesGroup


class ProfileForm(StatesGroup):
    choosing_degree_level = State()
    entering_major = State()
    choosing_gpa_scale = State()
    entering_gpa_value = State()
    choosing_lang_cert_type = State()
    entering_lang_cert_score = State()
    choosing_countries = State()
    entering_budget = State()
    entering_age = State()


class GpaStandaloneForm(StatesGroup):
    choosing_scale = State()
    entering_value = State()
