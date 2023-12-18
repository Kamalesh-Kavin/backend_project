from fastapi import APIRouter, Depends, HTTPException
from typing import List, Union
from pydantic import BaseModel
from authentication import curr_user
from connection import db, es
from models import Playlist, Song, User, Album, Artist, Genre
from sqlalchemy.orm import joinedload

user_router = APIRouter()

class PlaylistSongDetails(BaseModel):
    song_id: int
    song_name: str
    genre_name: str
    artist_name: str
    album_title: str

class PlaylistDetails(BaseModel):
    playlist_id: int
    playlist_name: str
    private: int
    songs: List[PlaylistSongDetails]

class UserDetails(BaseModel):
    username: str
    password: str
    user_id: int
    playlists: List[PlaylistDetails]

class userSchema(BaseModel):
    username: str
    password: str
    
class CreatePlaylistInput(BaseModel):
    playlist_name: str
    songs: List[str] 
    playlist_type:str
    
class CreateAutoPlaylistInput(BaseModel):
    playlist_name: str
    playlist_type:str
    attr: List[str]  
    desired: List[str]

class userData(BaseModel):
    attr: List[str]  
    desired: Union[List[str], List[int]]
    
def upload_data_into_es():
    user_details = db.query(User).options(
        joinedload(User.playlists)  # Use joinedload to eagerly load playlists
    ).all()
    users_data = []
    for user in user_details:
        playlists_data = []
        for playlist in user.playlists:
            song_details = []
            for song_id in playlist.song_ids:
                song = db.query(Song).filter_by(song_id=song_id).first()
                if song:
                    artist = db.query(Artist).filter_by(artist_id=song.artist_id).first()
                    album = db.query(Album).filter_by(album_id=song.album_id).first()
                    genre = db.query(Genre).filter_by(genre_id=song.genre_id).first()
                    if artist and album and genre:
                        song_model = {
                            "song_id": song.song_id,
                            "song_name": song.title,
                            "genre_name": genre.genre_name,
                            "artist_name": artist.artist_name,
                            "album_title": album.album_title
                        }
                        song_details.append(song_model)
            
            playlist_model = {
                "playlist_id": playlist.playlist_id,
                "playlist_name": playlist.playlist_name,
                "private": playlist.private,
                "songs": song_details
            }
            playlists_data.append(playlist_model)
        
        user_model = {
            "username": user.username,
            "password": user.password,
            "user_id": user.user_id,
            "playlists": playlists_data
        }
        users_data.append(user_model)
        es.index(index="users_",id=user.user_id,body=user_model)
    return {"message":"user data stored successfully"}

@user_router.get("/user-details/")
def search_user_details(user_data: userData):
    retrieved_documents=[]
    playlists = ["playlist", "private"]
    songs = ["song", "genre", "artist", "album"]
    for i,data in enumerate(user_data.attr):
        playlist = [prefix for prefix in playlists if data.startswith(prefix)]
        song = [prefix for prefix in songs if data.startswith(prefix)]
        if song:
            data = "playlists.songs."+data
        elif playlist:
            data = "playlists."+data
        query = {
            "query": {
                "match": {
                    data: user_data.desired[i]
                }
            }
        }
        search_results = es.search(index="users_", body=query)
        retrieved_documents.append(search_results["hits"]["hits"])
    return retrieved_documents

@user_router.get("/recommend-songs/")
def recommend_song(user = Depends(curr_user)):
    user_playlists_query = {
        "query": {
            "match": {"user_id": user}  
            }
        }
    user_playlists = es.search(index="users_", body=user_playlists_query)["hits"]["hits"]
  
    songs_in_user_playlists = []
    for playlist in user_playlists:
        playlist_info = playlist["_source"]["playlists"]
        for song_detail in playlist_info:
            songs_info=song_detail["songs"]
            for song in songs_info:
                songs_in_user_playlists.append({
                    "_index":"songs_",
                    "_id":song["song_id"]
                })
    mlt_query = {
        "query": {
            "more_like_this": {
                "fields": ["title","artist_name","album_title","genre_name"],  
                "like": songs_in_user_playlists,  
                "min_term_freq": 1, 
                "max_query_terms": 4,
                "min_doc_freq": 1,
            }
        }
    }
    mlt_search_results = es.search(index="songs_", body=mlt_query)
    recommended_songs = mlt_search_results["hits"]["hits"]
    recommend_song = []
    for song in recommended_songs:
        recommend_song.append(song["_source"])
    return recommend_song