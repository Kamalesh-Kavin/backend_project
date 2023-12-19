from fastapi import APIRouter, Depends, HTTPException
from typing import List, Union, Optional
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
def search_user_details(user = Depends(curr_user)):
    upload_data_into_es()
    query = {
        "query": {
            "match": {
                "user_id": user
            }
        }
    }
    retrieved_doc=es.search(index="users_", body=query)["hits"]["hits"][0]["_source"]
    return retrieved_doc

class FilterData(BaseModel):
    filter_attr: List[str]
    filter_val: List[str]
    
@user_router.get("/recommend-songs/")
def recommend_song(user = Depends(curr_user), field: Optional[str] = None, value: Optional[str] = None):
    user_playlists_query = {
        "query": {
            "match": {"user_id": user}  
            }
    }
    recommended_songs = []
    user_playlists = es.search(index="users_", body=user_playlists_query)["hits"]["hits"]
    if len(user_playlists)!=0:
        user_playlists = user_playlists[0]["_source"]["playlists"]
        songs_in_user_playlists = []
        artist_names=[]
        for song_detail in user_playlists:
            songs_info=song_detail["songs"]
            for song in songs_info:
                if field is not None and value is not None:
                    if song[field]==value:
                        songs_in_user_playlists.append({
                            "_id":song["song_id"]
                        })
                else:
                    songs_in_user_playlists.append({
                            "_id":song["song_id"]
                        })
                if song["artist_name"] not in artist_names:
                    artist_names.append(song["artist_name"]) 
        if len(songs_in_user_playlists)==0:
            return {"message":"no songs to recommend from"}
        mlt_query= {
            "size": 0,
            "query": {
                "bool": {
                    "must": {
                        "more_like_this": {
                            "fields": ["genre_name", "artist_name", "album_name"],
                            "like": songs_in_user_playlists,
                            "min_term_freq": 1,
                            "max_query_terms": 1,
                            "min_doc_freq": 1
                        }
                    }
                }
            },
            "aggs": {
                "specific_artists": {
                    "filters": {
                        "filters": {}
                    },
                    "aggs": {
                        "top_songs": {
                            "top_hits": {
                                "size": 5,
                                "_source": {
                                    "includes": ["title", "song_id", "genre_name", "artist_name", "album_title", "rating"]
                                }
                            }
                        }
                    }
                }
            }
        }
        filters = mlt_query["aggs"]["specific_artists"]["filters"]["filters"]
        for index, artist in enumerate(artist_names, start=1):
            filters[f"artist_{index}"] = {"term": {"artist_name.keyword": artist}}
            print(index, artist)
        result = es.search(index='songs_', body=mlt_query)
        artist_data = result["aggregations"]["specific_artists"]["buckets"]
        for artist in artist_data:
            curr_artist = artist_data[artist]["top_songs"]["hits"]["hits"]
            for i in range(len(curr_artist)):
                if field is not None and value is not None:
                    if curr_artist[i]["_source"][field]==value:
                        if curr_artist[i]["_source"] not in recommended_songs:
                            recommended_songs.append(curr_artist[i]["_source"])
                else:
                    if curr_artist[i]["_source"] not in recommended_songs:
                            recommended_songs.append(curr_artist[i]["_source"])
        return recommended_songs
    
    else:
        aggregation_query = {
            "size": 0, 
            "aggs": {
                "genres_count": {
                    "terms": {
                        "field": "genre_name.keyword", 
                        "size": 30 , #max number of genres available
                        "min_doc_count": 501 #min no. of songs required
                    }
                }
            }
        }
        genre_names=[]
        result = es.search(index="songs_", body=aggregation_query)
        if result.get("aggregations") and result["aggregations"].get("genres_count"):
            genre_buckets = result["aggregations"]["genres_count"]["buckets"]
            for bucket in genre_buckets:
                #genre_name = bucket["key"] it has genre_names
                genre_names.append(bucket["key"])
                #song_count = bucket["doc_count"] it has song_count
                
        rating_query = {
            "query": {
                "range": {
                    "rating": {
                        "gt": 3  
                    }
                }
            }
        }
        artist_names=[]
        results = es.search(index="songs_", body=rating_query)
        if results.get("hits") and results["hits"].get("hits"):
            for hit in results["hits"]["hits"]:
                artist_names.append(hit["_source"]["artist_name"])
        query={
            "size": 30, 
            "query": {
                "function_score": {
                "functions": [
                    {
                    "random_score": {} 
                    }
                ],
                "query": {
                    "bool": {
                    "should": [
                        {
                        "terms": {
                            "genre_name.keyword": genre_names
                        }
                        },
                        {
                        "terms": {
                            "artist_name.keyword": artist_names
                        }
                        }
                    ],
                    "minimum_should_match": 2 
                    }
                },
                "boost_mode": "replace"
                }
            }
            }

        search_res = es.search(index="songs_", body=query)
        recommended_songs = search_res["hits"]["hits"]
        recommend_song = []
        for song in recommended_songs:
            recommend_song.append(song["_source"])
        return recommend_song
    