from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.database import Session
from database.models import User
from datetime import datetime

class UserMiddleware(BaseMiddleware):
    """Middleware to ensure user exists in database"""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:

        user_data = event.from_user
        session = Session()

        try:
            # Check if user exists
            user = session.query(User).filter_by(id=user_data.id).first()

            if not user:
                # Create new user
                user = User(
                    id=user_data.id,
                    username=user_data.username,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name
                )
                session.add(user)
                session.commit()
            else:
                # Update last activity
                user.last_activity = datetime.utcnow()
                session.commit()

            # Add user to handler data
            data['db_user'] = user

        finally:
            session.close()

        return await handler(event, data)
