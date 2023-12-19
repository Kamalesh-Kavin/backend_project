from fastapi import APIRouter, Depends, HTTPException
from models import Playlist, Song
from connection import db, es
from authentication import curr_user
from pydantic import BaseModel
from typing import List
from user_routes import upload_data_into_es,update_user_in_es
from enum import Enum

playlist_router = APIRouter()

class CreatePlaylistInput(BaseModel):
    playlist_name: str
    songs: List[int] 
    
class AutoPlaylistInput(BaseModel):
    playlist_name: str
    artist: List[str]  
    genre: List[str]
    size: int
    
class ActionType(str, Enum):
    delete = 'delete'
    add = 'add'
    
class EditPlaylistInput(BaseModel):
    playlist_id: int
    action: ActionType
    songs_to_modify: List[int]
    
class DeletePlaylist(BaseModel):
    playlist_id: int
    
@playlist_router.post("/create-playlist/")
def create_playlist(playlist_data: CreatePlaylistInput,user = Depends(curr_user)):
    try:
        playlist = (
            db.query(Playlist).filter(
                Playlist.playlist_name == playlist_data.playlist_name,
                Playlist.user_id == user).first()
        )
        if  playlist:
            playlist.playlist_name =  playlist_data.playlist_name
            playlist.song_ids = playlist_data.songs
        if not playlist:
            playlist = (
                Playlist(playlist_name=playlist_data.playlist_name, user_id=user, song_ids=playlist_data.songs)
            )
            db.add(playlist)
        db.commit()
        db.refresh(playlist)
        update_user_in_es(user)
        return {"message": f"Playlist '{playlist_data.playlist_name}' created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create/update the playlist: {str(e)}")

@playlist_router.post("/create-auto-playlist/")
def create_auto_playlist(playlist_data: AutoPlaylistInput,user = Depends(curr_user)):
    try:
        playlist = (
            db.query(Playlist).filter(
                Playlist.playlist_name == playlist_data.playlist_name,
                Playlist.user_id == user).first()
        )
        pair=[]
        song_ids=[]
        for i in range(len(playlist_data.artist)):
            for j in range(len(playlist_data.genre)):
                pair.append((playlist_data.artist[i],playlist_data.genre[j]))
        for i in range(len(pair)):
            query = {
                "_source":"song_id",
                "size":playlist_data.size,
                "query": {
                    "bool": {
                        "must": [{"match": {"artist_name": pair[i][0]}}, 
                                 {"match": {"genre_name": pair[i][1]}}]
                    }
                }
            }
            search_results = es.search(index="songs_", body=query)
            retrieved_documents = search_results["hits"]["hits"]
            for doc in retrieved_documents:
                if "_source" in doc and "song_id" in doc["_source"]:
                    if doc["_source"]["song_id"] not in song_ids:
                        song_ids.append(doc["_source"]["song_id"])
        if len(song_ids)==0:
            return {"message":"no data for your requested artist and genre"}
        if  playlist:
            playlist.playlist_name =  playlist_data.playlist_name
            playlist.song_ids = song_ids
        if not playlist:
            playlist = (
                Playlist(playlist_name=playlist_data.playlist_name, user_id=user, song_ids=song_ids)
            )
            db.add(playlist)
        db.commit()
        db.refresh(playlist)
        update_user_in_es(user)
        return {"message": f"Playlist '{playlist_data.playlist_name}' created successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create/update the playlist: {str(e)}")

@playlist_router.put("/edit-playlist/")
def edit_playlist(playlist_data: EditPlaylistInput,user = Depends(curr_user)):
    try:
        playlist = (
            db.query(Playlist).filter(
                Playlist.playlist_id == playlist_data.playlist_id,
                Playlist.user_id == user).first()
        )
        if playlist:
            if playlist_data.action == "add":
                curr_songs=playlist.song_ids.copy()
                for data in playlist_data.songs_to_modify:
                    if data not in curr_songs:
                        curr_songs.append(data)
                playlist.song_ids = curr_songs
            else:
                curr_songs=playlist.song_ids.copy()
                for song in playlist_data.songs_to_modify:
                    if song in curr_songs:
                        curr_songs.remove(song)
                    else:
                        return {"message":f"song {song.title} does not exist in the playlist"}
                playlist.song_ids = curr_songs
            db.commit()
            db.refresh(playlist)
            update_user_in_es(user)
            return {"message":f"Playlist '{playlist.playlist_name} edited successfully"}
        else:
            return {"message":f"Playlist '{playlist.playlist_name} does not exist"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create/update the playlist: {str(e)}")

@playlist_router.delete("/delete-playlist/")
def del_playlist(playlist_data: DeletePlaylist,user = Depends(curr_user)):
    try:
        playlist = (
            db.query(Playlist).filter(
                Playlist.playlist_name == playlist_data.playlist_id,
                Playlist.user_id == user).first()
        )
        if playlist:
            playlist_name = playlist.playlist_name
            db.delete(playlist)
            db.commit()
            db.refresh()
            update_user_in_es(user)
            return {"message":f"{playlist_name} deleted successfully"}
        else:
            return {"message":f"playlist {playlist_name} doesn't exist"} 
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create/update the playlist: {str(e)}")
