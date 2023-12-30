from fastapi import FastAPI
from models import create_tables
from connection import create_index,engine
from authentication import auth_router
from song_routes import song_router
from user_routes import user_router
from playlists_routes import playlist_router

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI()

#All APIs
app.include_router(auth_router, prefix="/auth")
app.include_router(song_router, prefix="/songs")
app.include_router(user_router, prefix="/users")
app.include_router(playlist_router, prefix="/playlists")

create_index()
create_tables(engine)

@app.get("/") #setup for all required tables in postgresql and es
def setup():
    return {"message": "Setup done! Welcome to the music app!"}
