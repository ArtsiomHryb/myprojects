"""FSM-состояния."""

from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_password = State()
