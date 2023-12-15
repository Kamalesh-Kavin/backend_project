from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from elasticsearch import Elasticsearch
from sqlalchemy.orm import sessionmaker
from models import User,Song,Artist,Album,Genre,Playlist,Recommendation,Rating,create_tables,pwd_context
from pydantic import BaseModel
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt import PyJWTError

app = FastAPI()

#DB connectivity
DATABASE_URL = "postgresql://postgres:root@localhost:5432/music_appln"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

#ES connectivity
ELASTICSEARCH_URL = "https://localhost:9200"
es = Elasticsearch(hosts=ELASTICSEARCH_URL,basic_auth=("elastic", "1_W28jlMre-sx005bcoB"), verify_certs=False)

SECRET_KEY = "test"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class UserCreate(BaseModel):
    username: str
    password: str
    
@app.get("/")
def read_root():
    create_tables(engine)
    return {"message": "Setup done! Welcome to the music app!"}

@app.post("/register/")
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

@app.get("/login")
def login(user_data: UserCreate):
    user = authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    current_user = curr_user(access_token)
    return {"message":f"Successfully logged in as '{current_user}'"}
#    return {"message":f"your access token is '{access_token}'"}

@app.get("/current-user")
def curr_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"username": username}
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
