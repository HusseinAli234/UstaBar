from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.core.database import get_async_session
from app.security.auth import authenticate_user
from app.security.jwt import create_access_token  

router = APIRouter(prefix="/auth", tags=["auth"])


from app.schemas.user import UserCreate, UserResponse
from app.security.password import hash_password # Ваша функция хеширования
from app.models.user import User
from sqlalchemy import select

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate, 
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    new_user = User(
        username=user_data.username,
        password=hash_password(user_data.password),
        email=user_data.email
    )
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@router.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_async_session)
):
    user = await authenticate_user(session, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    
    return {"access_token": access_token, "token_type": "bearer"}