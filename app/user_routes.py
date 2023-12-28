from fastapi import APIRouter, Depends
from typing import Optional
from authentication import curr_user
from connection import db, es
from models import Song, User, Album, Artist, Genre, Recommendation
from sqlalchemy.orm import joinedload
from pydantic import BaseModel
from song_routes import update_song_in_es

user_router = APIRouter()
  
def update_user_in_es(user_id):
    user_details = db.query(User).filter(User.user_id==user_id).options(
        joinedload(User.playlists)  # Use joinedload to eagerly load playlists
    ).all()
    user_details = user_details[0]
    playlists_data = []
    for playlist in user_details.playlists:
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
        "username": user_details.username,
        "password": user_details.password,
        "email": user_details.email,
        "user_id": user_details.user_id,
        "playlists": playlists_data
    }
    es.index(index="users_",id=user_details.user_id,body=user_model)
    return {"message":"user data stored successfully"}

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
            "email": user.email,
            "user_id": user.user_id,
            "playlists": playlists_data
        }
        users_data.append(user_model)
        es.index(index="users_",id=user.user_id,body=user_model)
    return {"message":"user data stored successfully"}

@user_router.get("/user-details/")
def get_user_details(user = Depends(curr_user)):
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
    
@user_router.get("/recommend-songs/")
def recommend_song(user = Depends(curr_user), field: Optional[str] = None, value: Optional[str] = None, rec_size: Optional[int] = 10):
    user_playlists_query = {
        "query": {
            "match": {"user_id": user}  
            }
    }
    recommended_songs = []
    user_playlists = es.search(index="users_", body=user_playlists_query)["hits"]["hits"][0]["_source"]["playlists"]
    if len(user_playlists)!=0:
        songs_in_user_playlists = []
        artist_genre_pairs=[]
        for song_detail in user_playlists:
            songs_info=song_detail["songs"]
            for song in songs_info:
                artist_name=song["artist_name"]
                genre_name=song["genre_name"]
                pair=(artist_name,genre_name)
                if field is not None and value is not None:
                    if song[field]==value:
                        songs_in_user_playlists.append({
                            "_id":song["song_id"]
                        })
                        if pair not in artist_genre_pairs:
                            artist_genre_pairs.append(pair)
                else:
                    songs_in_user_playlists.append({
                            "_id":song["song_id"]
                        })
                    if pair not in artist_genre_pairs:
                            artist_genre_pairs.append(pair)
        if len(songs_in_user_playlists)==0:
            return {"message":"no songs to recommend from"}
        size_query=rec_size//len(artist_genre_pairs)
        mlt_query= {
            "size": 50,
            "query": {
                "bool": {
                    "must": {
                        "more_like_this": {
                            "fields": ["artist_name"],
                            "like": songs_in_user_playlists,
                            "min_term_freq": 1,
                            "max_query_terms": 6,
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
                                "size": size_query,
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
        for index, artist in enumerate(artist_genre_pairs):
            filters[f"artist_{index+1}"] = {
                "bool": {
                    "filter": [
                        {"term": {"artist_name.keyword": artist[0]}},
                        {"term": {"genre_name.keyword": artist[1]}}
                    ]
                }
            }
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
    
    else: #for users who have no pre-existing playlists - general songs
        combined_query={
            "size": 0,
            "aggs": {
                "genres_count": {
                    "terms": {
                        "field": "genre_name.keyword",
                        "min_doc_count": 10
                    }
                },
                "artists_list": {
                    "terms": {
                        "field": "artist_name.keyword",
                        "size": 10
                    }
                }
            }
        }
        re = es.search(index="songs_", body=combined_query)
        genre_data = re["aggregations"]["genres_count"]["buckets"]
        artist_data = re["aggregations"]["artists_list"]["buckets"]
        genre_names=[]
        artist_names=[]
        for i in genre_data:
            genre_names.append(i["key"])
        for i in artist_data:
            artist_names.append(i["key"])
        query={
            "size": rec_size, 
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
            if field is not None and value is not None:
                if song["_source"][field]==value:
                    if song["_source"] not in recommended_songs:
                        recommend_song.append(song["_source"])
            else:
                if song["_source"] not in recommended_songs:
                    recommend_song.append(song["_source"])
        return recommend_song

@user_router.get("/top_rated_songs/")
def top_rated_songs( rec_size: Optional[int] = 10):
    rating_query = {
        "size": 0,
        "aggs": {
            "genres": {
                "terms": {
                    "field": "genre_name.keyword",
                    "size": rec_size  
                },
                "aggs": {
                    "top_hits_per_genre": {
                        "top_hits": {
                            "size": 2,
                            "sort": [
                                {
                                "rating": {
                                    "order": "desc"
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    re=es.search(index="songs_",body=rating_query)
    rec_songs=[]
    songs_data=re["aggregations"]["genres"]["buckets"]
    for i in songs_data:
        for song in i["top_hits_per_genre"]["hits"]["hits"]:
            if song["_source"] not in rec_songs:
                rec_songs.append(song["_source"])
    return rec_songs

@user_router.get("/top_recommended_songs/")
def top_recommended_songs( rec_size: Optional[int] = 10):
    rating_query = {
        "size": 0,
        "aggs": {
            "genres": {
                "terms": {
                    "field": "genre_name.keyword",
                    "size": rec_size  
                },
                "aggs": {
                    "top_hits_per_genre": {
                        "top_hits": {
                            "size": 2,
                            "sort": [
                                {
                                "recommendation_count": {
                                    "order": "desc"
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
    re=es.search(index="songs_",body=rating_query)
    rec_songs=[]
    songs_data=re["aggregations"]["genres"]["buckets"]
    for i in songs_data:
        for song in i["top_hits_per_genre"]["hits"]["hits"]:
            if song["_source"] not in rec_songs:
                rec_songs.append(song["_source"])
    return rec_songs

@user_router.get("/trending_songs/")
def trending_songs( rec_size: Optional[int] = 10):
    top_songs_query = {
    "size": rec_size, 
    "query": {
        "match_all": {} 
    },
    "sort": [
        {"recommendation_count": {"order": "desc"}}  
    ],
    "_source": {
        "includes": ["title", "artist_name", "genre_name", "album_title","recommendation_count"] 
    }
}
    re=es.search(index="songs_",body=top_songs_query)
    songs_data= re["hits"]["hits"]
    rec_songs=[]
    for song in songs_data:
        if song["_source"] not in rec_songs:
            rec_songs.append(song["_source"])
    return rec_songs

class share_data(BaseModel):
    receiver_id: int
    rd_type: str
    rd_type_id: int
    
@user_router.post("/share-recommendation/")
def share_recommendation(data: share_data,user = Depends(curr_user)):
    recommendation = (
                Recommendation(sender_id=user, receiver_id=data.receiver_id, recommendation_type=data.rd_type, recommendation_type_id=data.rd_type_id)
            )
    try:
        if data.rd_type.startswith("genre"):
            genre = db.query(Genre).filter(Genre.genre_id == data.rd_type_id).first()
            if genre:
                songs_in_genre = db.query(Song).filter(Song.genre_id == data.rd_type_id).all()
            for song in songs_in_genre:
                song.recommendation_count = song.recommendation_count + 1
                db.add(song)
                db.commit()
                db.refresh(song)
                update_song_in_es(song.song_id)
        if data.rd_type.startswith("artist"):
            artist = db.query(Artist).filter(Artist.artist_id == data.rd_type_id).first()
            if artist:
                songs_in_artist = db.query(Song).filter(Song.artist_id == data.rd_type_id).all()
            for song in songs_in_artist:
                song.recommendation_count = song.recommendation_count + 1
                db.add(song)
                db.commit()
                db.refresh(song)
                update_song_in_es(song.song_id)
        if data.rd_type.startswith("album"):
            album = db.query(Album).filter(Album.album_id == data.rd_type_id).first()
            if album:
                songs_in_album = db.query(Song).filter(Song.album_id == data.rd_type_id).all()
            for song in songs_in_album:
                song.recommendation_count = song.recommendation_count + 1
                db.add(song)
                db.commit()
                db.refresh(song)
                update_song_in_es(song.song_id)
        if data.rd_type.startswith("song"):
            song = db.query(Song).filter(Song.song_id == data.rd_type_id).first()
            song.recommendation_count = song.recommendation_count + 1
            db.add(song)
            db.commit()
            db.refresh(song)
            update_song_in_es(song.song_id)
        db.add(recommendation)
        db.commit()
        return {"message":"recommendation shared successfuly"}
    except:
        return {"message":"specified recommendation id doesn't exist"}