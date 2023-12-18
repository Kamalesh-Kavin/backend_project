from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from models import User,Song,Artist,Album,Genre,Playlist,Rating,create_tables,pwd_context
from pydantic import BaseModel
from connection import db
from authentication import auth_router
from song_routes import song_router
from user_routes import user_router
from playlists_routes import playlist_router
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI()

#other APIs
app.include_router(auth_router, prefix="/auth")
app.include_router(song_router, prefix="/songs")
app.include_router(user_router, prefix="/user")
app.include_router(playlist_router, prefix="/playlists")

@app.get("/")
def read_root():
    return {"message": "Setup done! Welcome to the music app!"}
