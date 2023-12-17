from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from connection import db
from models import User,pwd_context
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt import PyJWTError
from datetime import datetime, timedelta

auth_router = APIRouter()

SECRET_KEY = "test"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class UserCreate(BaseModel):
    username: str
    password: str
    
@auth_router.post("/register/")
def register_user(user: UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    new_user = User(username=user.username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message":"regn successful"}

# Function to create access token using JWT
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.password):
        return None
    return user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@auth_router.get("/login")
def login(user_data: UserCreate):
    user = authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    current_user=curr_user(token)
    return {"token":token}

@auth_router.get("/current-user")
def curr_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user_id = db.query(User).filter(User.username == username).first()
        return user_id.user_id
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    