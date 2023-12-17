from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
import pandas as pd
import io
from models import Genre, Artist, Album, Song, Rating
from connection import db, es
from pydantic import BaseModel
from authentication import curr_user
from typing import List
song_router = APIRouter()

# @song_router.get("/upload-songs")
def upload_data_into_es():
    songs_details = (
        db.query(
            Song.song_id,
            Song.title,
            Artist.artist_name,
            Album.album_title,
            Genre.genre_name
        )
        .join(Artist, Artist.artist_id == Song.artist_id)
        .join(Album, Album.album_id == Song.album_id)
        .join(Genre, Genre.genre_id == Song.genre_id)
        .all()
    )
    for song in songs_details:
        song_data = {
            "song_id": song.song_id,
            "title": song.title,
            "artist_name": song.artist_name,
            "album_title": song.album_title,
            "genre_name": song.genre_name
        }
        es.index(index="songs_", id=song.song_id,body=song_data)
    return {"message":"song data stored successfully"}

@song_router.post("/save-data/")
async def save_data_from_csv(csv_file: UploadFile = File(...)):
    try:
        if not csv_file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Uploaded file is not a CSV")
        contents = await csv_file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))   
        df['genre'].fillna("Classic", inplace=True)
        df['artist'].fillna("Weekend", inplace=True)
        df['album'].fillna("Scorpion", inplace=True)
        df['song_name'].fillna("Sacrifice", inplace=True)    
        for row in range(len(df)):
            print(row)
            genre = (
                db.query(Genre).filter_by(genre_name=df.iloc[row].to_dict()["genre"]).first()
            )
            if not genre:
                genre = Genre(genre_name=df.iloc[row].to_dict()["genre"])
                db.add(genre)
            artist = (
                db.query(Artist).filter_by(artist_name=df.iloc[row].to_dict()["artist"]).first()
            )
            if not artist:
                artist =Artist(artist_name=df.iloc[row].to_dict()["artist"])
                db.add(artist)
            album = (
                db.query(Album).filter_by(album_title=df.iloc[row].to_dict()["album"]).first()
            )
            if not album:
                album = Album(
                    album_title=df.iloc[row].to_dict()["album"], artist_id=artist.artist_id
                )
                db.add(album)
            db.commit()
            song = (
                db.query(Song).filter_by(title=df.iloc[row].to_dict()["song_name"]).first()
            )
            if not song:
                song = Song(
                    title=df.iloc[row].to_dict()["song_name"],
                    artist_id=artist.artist_id,
                    genre_id=genre.genre_id,
                    album_id=album.album_id,
                )
                db.add(song)
        db.commit()
        upload_data_into_es()
        return {"message": "Database populated successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save data from CSV: {str(e)}")
    
class RateSongInput(BaseModel):
    song_name: str
    rating: int
    
class searchSongs(BaseModel):
    attr: List[str]
    desired: List[str]
    
@song_router.post("/rate-song/")
def rate_song(song_data: RateSongInput,user = Depends(curr_user)):
    try:
        song = db.query(Song).filter(Song.title == song_data.song_name).first()
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")
        rating = (
            db.query(Rating).filter(
            Rating.user_id == user,
            Rating.song_id == song.song_id).first()
        )
        rating.rating = song_data.rating
        if not rating:
            rating = Rating(user_id=user, song_id=song.song_id, rating=song_data.rating)
            db.add(rating)
        db.commit()
        return {"message":"rating done successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to rate the song: {str(e)}")

@song_router.get("/search-song/")
def search_song(song_data: searchSongs):
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {song_data.attr[data]: song_data.desired[data]}}
                        for data in range(len(song_data.attr))  
                    ]
                }
            }
        }
    search_results = es.search(index="songs_", body=query)
    retrieved_documents = search_results["hits"]["hits"]
    return retrieved_documents