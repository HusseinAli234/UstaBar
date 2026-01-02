from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.security.password import verify_password

async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    result = await session.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if not user:
        return None

    if not verify_password(password, user.password):
        print("Invalid Password")
        return None



    return user