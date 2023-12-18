from fastapi import APIRouter, Depends, HTTPException
from models import Playlist, Song
from connection import db, es
from authentication import curr_user
from pydantic import BaseModel
from typing import List
from user_routes import upload_data_into_es

playlist_router = APIRouter()

class CreatePlaylistInput(BaseModel):
    playlist_name: str
    songs: List[str] 
    playlist_type:str
    
class CreateAutoPlaylistInput(BaseModel):
    playlist_name: str
    playlist_type:str
    attr: List[str]  
    desired: List[str]
    
class AutoPlaylistInput(BaseModel):
    playlist_name: str
    playlist_type:str
    artist: List[str]  
    genre: List[str]
    
class EditPlaylistInput(BaseModel):
    playlist_name: str
    action: str
    songs_to_modify: List[str]
    
class DeletePlaylist(BaseModel):
    playlist_name: str
    
@playlist_router.post("/create-playlist/")
def create_playlist(playlist_data: CreatePlaylistInput,user = Depends(curr_user)):
    try:
        playlist = (
            db.query(Playlist).filter(
                Playlist.playlist_name == playlist_data.playlist_name,
                Playlist.user_id == user).first()
        )
        result = 1 if playlist_data.playlist_type == "private"  else 0
        song_names = playlist_data.songs  
        songs = db.query(Song).filter(Song.title.in_(song_names)).all()
        songs_to_add = [song.song_id for song in songs]
        if  playlist:
            playlist.playlist_name =  playlist_data.playlist_name
            playlist.song_ids = songs_to_add
            playlist.private = result
        if not playlist:
            playlist = (
                Playlist(playlist_name=playlist_data.playlist_name, user_id=user, song_ids=songs_to_add, private=result)
            )
            db.add(playlist)
        db.commit()
        upload_data_into_es()
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
        result = 1 if playlist_data.playlist_type == "private"  else 0
        pair=[]
        song_ids=[]
        for i in range(len(playlist_data.artist)):
            for j in range(len(playlist_data.genre)):
                pair.append((playlist_data.artist[i],playlist_data.genre[j]))
        for i in range(len(pair)):
            query = {
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
        if  playlist:
            playlist.playlist_name =  playlist_data.playlist_name
            playlist.song_ids = song_ids
            playlist.private = result
        if not playlist:
            playlist = (
                Playlist(playlist_name=playlist_data.playlist_name, user_id=user, song_ids=song_ids, private=result)
            )
            db.add(playlist)
        db.commit()
        upload_data_into_es()
        return {"message": f"Playlist '{playlist_data.playlist_name}' created successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create/update the playlist: {str(e)}")

# def create_auto_playlist(playlist_data: CreateAutoPlaylistInput,user = Depends(curr_user)):
#     try:
#         playlist = (
#             db.query(Playlist).filter(
#                 Playlist.playlist_name == playlist_data.playlist_name,
#                 Playlist.user_id == user).first()
#         )
#         result = 1 if playlist_data.playlist_type == "private"  else 0
#         pair=[]
#         for i,data in playlist_data.attr:
#             pair.append(data)
#         query = {
#             "query": {
#                 "bool": {
#                     "must": [
#                         {"match": {playlist_data.attr[data]: playlist_data.desired[data]}}
#                             for data in range(len(playlist_data.attr))  
#                     ]
#                 }
#             }
#         }
#         search_results = es.search(index="songs_", body=query)
#         retrieved_documents = search_results["hits"]["hits"]
#         song_ids = [doc["_source"]["song_id"] for doc in retrieved_documents if "_source" in doc and "song_id" in doc["_source"]]
#         if  playlist:
#             playlist.playlist_name =  playlist_data.playlist_name
#             playlist.song_ids = song_ids
#             playlist.private = result
#         if not playlist:
#             playlist = (
#                 Playlist(playlist_name=playlist_data.playlist_name, user_id=user, song_ids=song_ids, private=result)
#             )
#             db.add(playlist)
#         db.commit()
#         upload_data_into_es()
#         return {"message": f"Playlist '{playlist_data.playlist_name}' created successfully"}
        
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Failed to create/update the playlist: {str(e)}")

@playlist_router.put("/edit-playlist/")
def edit_playlist(playlist_data: EditPlaylistInput,user = Depends(curr_user)):
    try:
        playlist = (
            db.query(Playlist).filter(
                Playlist.playlist_name == playlist_data.playlist_name,
                Playlist.user_id == user).first()
        )
        if playlist:
            act=1 if playlist_data.action == "add"  else 0
            if act==1:
                song_names = playlist_data.songs_to_modify 
                songs = db.query(Song).filter(Song.title.in_(song_names)).all()
                curr_songs=playlist.song_ids.copy()
                for song in songs:
                    if song.song_id not in curr_songs:
                        curr_songs.append(song.song_id)
                playlist.song_ids = curr_songs
                
            else:
                song_names = playlist_data.songs_to_modify  
                songs = db.query(Song).filter(Song.title.in_(song_names)).all()
                curr_songs=playlist.song_ids.copy()
                for song in songs:
                    if song.song_id in curr_songs:
                        curr_songs.remove(song.song_id)
                    else:
                        return {"message":f"song {song.title} does not exist in the playlist"}
                playlist.song_ids = curr_songs
            db.commit()
            upload_data_into_es()
            return {"message":f"Playlist '{playlist_data.playlist_name} edited successfully"}
        else:
            return {"message":f"Playlist '{playlist_data.playlist_name} does not exist"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create/update the playlist: {str(e)}")

@playlist_router.delete("/delete-playlist/")
def edit_playlist(playlist_data: DeletePlaylist,user = Depends(curr_user)):
    try:
        playlist = (
            db.query(Playlist).filter(
                Playlist.playlist_name == playlist_data.playlist_name,
                Playlist.user_id == user).first()
        )
        if playlist:
            db.delete(playlist)
            db.commit()
            upload_data_into_es()
            return {"message":f"playlist {playlist_data.playlist_name} deleted successfully"}
        else:
            return {"message":f"playlist {playlist_data.playlist_name} doesn't exist"} 
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create/update the playlist: {str(e)}")
