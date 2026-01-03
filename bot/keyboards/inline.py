from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Profile

def get_profiles_keyboard(profiles: list[Profile], page: int = 0, page_size: int = 5):
    """Build inline keyboard for profile selection with pagination"""
    keyboard = []

    # Calculate pagination
    start_idx = page * page_size
    end_idx = start_idx + page_size
    page_profiles = profiles[start_idx:end_idx]

    # Add profile buttons
    for profile in page_profiles:
        icon = "⭐" if profile.is_default else "✏️"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} {profile.name}",
                callback_data=f"select_profile:{profile.id}"
            )
        ])

    # Add pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"profiles_page:{page-1}")
        )
    if end_idx < len(profiles):
        nav_buttons.append(
            InlineKeyboardButton(text="➡️ Далее", callback_data=f"profiles_page:{page+1}")
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Add "Create new profile" button
    keyboard.append([
        InlineKeyboardButton(text="➕ Создать свой профиль", callback_data="create_profile")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_profile_management_keyboard(profile_id: int, is_default: bool = False, is_copy: bool = False):
    """Keyboard for managing a specific profile"""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_profile:{profile_id}")],
    ]

    if is_copy:
        keyboard.append([InlineKeyboardButton(
            text="🔄 Сбросить к оригиналу",
            callback_data=f"reset_profile:{profile_id}"
        )])
    elif not is_default:
        keyboard.append([InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"delete_profile:{profile_id}"
        )])

    keyboard.append([InlineKeyboardButton(
        text="📤 Экспортировать",
        callback_data=f"export_profile:{profile_id}"
    )])
    keyboard.append([InlineKeyboardButton(
        text="« Назад к списку",
        callback_data="back_to_profiles"
    )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_edit_field_keyboard(profile_id: int):
    """Keyboard for selecting which field to edit"""
    keyboard = [
        [InlineKeyboardButton(text="📝 Название", callback_data=f"edit_field:{profile_id}:name")],
        [InlineKeyboardButton(text="📋 Описание", callback_data=f"edit_field:{profile_id}:description")],
        [InlineKeyboardButton(text="🤖 Промпт", callback_data=f"edit_field:{profile_id}:prompt")],
        [InlineKeyboardButton(text="« Отмена", callback_data=f"cancel_edit:{profile_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
