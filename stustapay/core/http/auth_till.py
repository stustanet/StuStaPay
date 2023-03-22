from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/register_terminal")


async def get_auth_token(token: str = Depends(oauth2_scheme)) -> str:
    return token
