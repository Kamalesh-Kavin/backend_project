from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
import pandas as pd
import io
from .models import Genre, Artist, Album, Song, Rating
from .connection import db, es
from pydantic import BaseModel
from .authentication import curr_user
from typing import Optional
from sqlalchemy import func
#import boto3

song_router = APIRouter()

class RateSongInput(BaseModel):
    song_id: int
    rating: float
    

def update_song_in_es(song_id):
    result = es.get(index="songs_",id=song_id)
    data = result["_source"]
    rc= (
        db.query(Song).filter(Song.song_id==song_id).first()
    )
    average_rating = (
        db.query(func.avg(Rating.rating))
        .filter(Rating.song_id == data["song_id"])
        .scalar() 
    )
    data["recommendation_count"] = rc.recommendation_count
    data["rating"] = average_rating
    es.index(index="songs_",id=song_id ,body=data)

def upload_data_into_es():
    songs_details = (
        db.query(
            Song.song_id,
            Song.title,
            Artist.artist_name,
            Album.album_title,
            Genre.genre_name,
            func.coalesce(func.avg(Rating.rating), 0).label('rating'), 
            Song.recommendation_count
        )
        .join(Artist, Artist.artist_id == Song.artist_id)
        .join(Album, Album.album_id == Song.album_id)
        .join(Genre, Genre.genre_id == Song.genre_id)
        .outerjoin(Rating, Rating.song_id == Song.song_id)  # Perform a LEFT OUTER JOIN to include songs without ratings
        .group_by(
            Song.song_id,
            Song.title,
            Artist.artist_name,
            Album.album_title,
            Genre.genre_name
        )  
        .all()
    )
    for song in songs_details:
        song_data = {
            "song_id": song.song_id,
            "title": song.title,
            "artist_name": song.artist_name,
            "album_title": song.album_title,
            "genre_name": song.genre_name,
            "rating":song.rating,
            "recommendation_count": song.recommendation_count
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
        #for aws s3
        '''
        s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
        s3.upload_file(CSV_FILE_PATH, S3_BUCKET_NAME, 'backup/filename.csv')  
        '''
        df['genre'].fillna("Classic", inplace=True)
        df['artist'].fillna("Weekend", inplace=True)
        df['album'].fillna("Scorpion", inplace=True)
        df['song_name'].fillna("Sacrifice", inplace=True)    
        for row in range(len(df)):
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

# import random
# @song_router.post("/random-rating/")
# def random_rating():
#     user_array = [1,3,5,6]
#     song=db.query(Song).all()
#     for i in song:
#         test(i.song_id,random.choice(user_array))
# def test(song_id,user_id):
#     try:
#         rating = (
#             db.query(Rating).filter(
#             Rating.user_id == user_id,
#             Rating.song_id == song_id).first()
#         )
#         random_float = round(random.uniform(3.0, 5.0), 1)
#         if rating:
#             rating.rating = random_float
#         if not rating:
#             rating = Rating(user_id=user_id, song_id=song_id, rating=random_float)
#             db.add(rating)
#         db.commit()
#         update_song_in_es(song_id)
#         return {"message":"rating done successfully"}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Failed to rate the song: {str(e)}")
    
@song_router.post("/rate-song/")
def rate_song(song_data: RateSongInput,user = Depends(curr_user)):
    try:
        rating = (
            db.query(Rating).filter(
            Rating.user_id == user,
            Rating.song_id == song_data.song_id).first()
        )
        if rating:
            rating.rating = song_data.rating
        if not rating:
            rating = Rating(user_id=user, song_id=song_data.song_id, rating=song_data.rating)
            db.add(rating)
        db.commit()
        update_song_in_es(song_data.song_id)
        return {"message":"rating done successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to rate the song: {str(e)}")

@song_router.get("/search-song/")
def search_song(song_name: str,field: Optional[str] = None, value: Optional[str] = None):
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "title": {
                                "query": song_name,
                                "fuzziness": "AUTO"
                            }
                        }
                    }
                ]
            }
        }
    }
    search_results = es.search(index="songs_", body=query)
    retrieved_documents = search_results["hits"]["hits"]
    res=[]
    for doc in retrieved_documents:
        if field is not None and value is not None:
            if doc["_source"][field]==value:
                res.append(doc["_source"])
        else:
            res.append(doc["_source"])
    return res