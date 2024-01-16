from fastapi import APIRouter, Depends
from typing import Optional
from authentication import curr_user
from connection import db, es
from models import Song, User, Album, Artist, Genre, Recommendation
from sqlalchemy.orm import joinedload
from pydantic import BaseModel
from song_routes import update_song_in_es
import random

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
    suggested_to = []
    suggested_from = []
    recommendations_sent = db.query(Recommendation).filter_by(sender_id=user_id).all()
    recommendations_received = db.query(Recommendation).filter_by(receiver_id=user_id).all()
    for recommendation in recommendations_sent:
        if recommendation.recommendation_type.startswith("genre"):
            recom = db.query(Genre).filter_by(genre_id=recommendation.recommendation_type_id).first()
            recom_name=recom.genre_name
        elif recommendation.recommendation_type.startswith("artist"):
            recom = db.query(Artist).filter_by(artist_id=recommendation.recommendation_type_id).first()
            recom_name=recom.artist_name
        elif recommendation.recommendation_type.startswith("album"):
            recom = db.query(Album).filter_by(album_id=recommendation.recommendation_type_id).first()
            recom_name=recom.album_title
        elif recommendation.recommendation_type.startswith("song"):
            recom = db.query(Song).filter_by(song_id=recommendation.recommendation_type_id).first()
            recom_name=recom.title
        suggested_to.append({
            "recommendation_type":recommendation.recommendation_type,
            "recommendation_name":recom_name
        })
    for recommendation in recommendations_received:
        if recommendation.recommendation_type.startswith("genre"):
            recom = db.query(Genre).filter_by(genre_id=recommendation.recommendation_type_id).first()
            recom_name=recom.genre_name
        elif recommendation.recommendation_type.startswith("artist"):
            recom = db.query(Artist).filter_by(artist_id=recommendation.recommendation_type_id).first()
            recom_name=recom.artist_name
        elif recommendation.recommendation_type.startswith("album"):
            recom = db.query(Album).filter_by(album_id=recommendation.recommendation_type_id).first()
            recom_name=recom.album_title
        elif recommendation.recommendation_type.startswith("song"):
            recom = db.query(Song).filter_by(song_id=recommendation.recommendation_type_id).first()
            recom_name=recom.title
        suggested_from.append({
            "recommendation_type":recommendation.recommendation_type,
            "recommendation_name":recom_name
        })
    user_model = {
        "username": user_details.username,
        "password": user_details.password,
        "email": user_details.email,
        "user_id": user_details.user_id,
        "playlists": playlists_data,
        "my_suggestions": suggested_to,
        "recommendations_for_me": suggested_from
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
        suggested_to = []
        suggested_from = []
        recommendations_sent = db.query(Recommendation).filter_by(sender_id=user.user_id).all()
        recommendations_received = db.query(Recommendation).filter_by(receiver_id=user.user_id).all()
        for recommendation in recommendations_sent:
            if recommendation.recommendation_type.startswith("genre"):
                recom = db.query(Genre).filter_by(genre_id=recommendation.recommendation_type_id).first()
                recom_name=recom.genre_name
            elif recommendation.recommendation_type.startswith("artist"):
                recom = db.query(Artist).filter_by(artist_id=recommendation.recommendation_type_id).first()
                recom_name=recom.artist_name
            elif recommendation.recommendation_type.startswith("album"):
                recom = db.query(Album).filter_by(album_id=recommendation.recommendation_type_id).first()
                recom_name=recom.album_title
            elif recommendation.recommendation_type.startswith("song"):
                recom = db.query(Song).filter_by(song_id=recommendation.recommendation_type_id).first()
                recom_name=recom.title
            suggested_to.append({
                "recommendation_type":recommendation.recommendation_type,
                "recommendation_name":recom_name
            })
        for recommendation in recommendations_received:
            if recommendation.recommendation_type.startswith("genre"):
                print(recommendation)
                recom = db.query(Genre).filter_by(genre_id=recommendation.recommendation_type_id).first()
                print(recom)
                recom_name=recom.genre_name
            elif recommendation.recommendation_type.startswith("artist"):
                recom = db.query(Artist).filter_by(artist_id=recommendation.recommendation_type_id).first()
                recom_name=recom.artist_name
            elif recommendation.recommendation_type.startswith("album"):
                recom = db.query(Album).filter_by(album_id=recommendation.recommendation_type_id).first()
                recom_name=recom.album_title
            elif recommendation.recommendation_type.startswith("song"):
                recom = db.query(Song).filter_by(song_id=recommendation.recommendation_type_id).first()
                recom_name=recom.title
            suggested_from.append({
                "recommendation_type":recommendation.recommendation_type,
                "recommendation_name":recom_name
            })

        user_model = {
            "username": user.username,
            "password": user.password,
            "email": user.email,
            "user_id": user.user_id,
            "playlists": playlists_data,
            "my_suggestions": suggested_to,
            "recommendations_for_me": suggested_from
        }
        users_data.append(user_model)
        es.index(index="users_", id=user.user_id, body=user_model)

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
    retrieved_doc=es.search(index="users_", body=query)["hits"]["hits"]
    res = retrieved_doc[0]
    if len(res)!=1:
        return res["_source"]
    else:
        return res[0]["_source"]
    
@user_router.get("/filter-recommendations/")
def recommend_song(user = Depends(curr_user), filter: Optional[str] = None, rec_size: Optional[int] = 10):
    user_playlists_query = {
        "query": {
            "match": {
                "user_id": user
            }
        },
        "_source": {
            "includes": ["username","user_id","recommendations_for_me"]
        }
    }
    res = es.search(index="users_", body=user_playlists_query)["hits"]["hits"][0]["_source"]
    rec = res["recommendations_for_me"]
    result=[]
    result.append({"username":res["username"],"user_id":res["user_id"]})
    for i in range(rec_size):
        if filter is not None:
            if filter==rec[i]["recommendation_type"]:
                result.append(rec[i])
        else:
            result.append(rec[i])
    return result


@user_router.get("/recommend-songs/")
def recommend_song(user = Depends(curr_user), field: Optional[str] = None, value: Optional[str] = None, rec_size: Optional[int] = 10):
    user_playlists_query = {
        "query": {
            "match": {
                "user_id": user
                }  
            }
    }
    recommended_songs = []
    res = es.search(index="users_", body=user_playlists_query)["hits"]["hits"]
    user_playlists = res
    if len(user_playlists)!=1:
        user_playlists = user_playlists["_source"]["playlists"]
    else:
        user_playlists = res[0]["_source"]["playlists"]
    if len(user_playlists)!=0:
        songs_in_user_playlists = []
        artist_genre_pairs=[]
        generic = []
        for song_detail in user_playlists:
            songs_info=song_detail["songs"]
            for song in songs_info:
                artist_name=song["artist_name"]
                genre_name=song["genre_name"]
                pair=(artist_name,genre_name)
                generic.append({
                            "_id":song["song_id"]
                        })
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
            songs_in_user_playlists = generic
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
        rating_query = {
            "size": 0,
            "query": {
                "bool": {
                "filter": {
                    "range": {
                    "rating": {"gt": 4 }
                        }
                    }
                }
            },
            "aggs": {
                "genres": {
                "terms": {
                    "field": "genre_name.keyword",
                    "size": rec_size,
                    "min_doc_count": 2  
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
        re = es.search(index="songs_", body=rating_query)
        recommended_songs=[]
        songs_data=re["aggregations"]["genres"]["buckets"]
        for i in songs_data:
            for song in i["top_hits_per_genre"]["hits"]["hits"]:
                if field is not None and value is not None:
                    if song["_source"][field]==value:
                        if song["_source"] not in recommended_songs:
                            recommended_songs.append(song["_source"])
                else:
                    if song["_source"] not in recommended_songs:
                        recommended_songs.append(song["_source"])
        return recommended_songs

class share_data(BaseModel):
    receiver_id: int
    rd_type: str
    rd_type_id: int

#only for testing
@user_router.post("/random-share-recommendation/")
def test():
    a=200
    while(a!=0):
        user_to_array = [1,5,6]
        user_from_array = [2,3,4]
        type_start=["genre","artist","album","song"]
        rd_to=random.choice(user_to_array)
        rd_from=random.choice(user_from_array)
        rd_type=random.choice(type_start)
        rd_type_id = random.randint(1, 26)
        recommendation = (
                    Recommendation(sender_id=rd_from, receiver_id=rd_to, recommendation_type=rd_type, recommendation_type_id=rd_type_id)
                )
        if rd_type.startswith("genre"):
            genre = db.query(Genre).filter(Genre.genre_id == rd_type_id).first()
            if genre:
                songs_in_genre = db.query(Song).filter(Song.genre_id == rd_type_id).all()
            for song in songs_in_genre:
                song.recommendation_count = song.recommendation_count + 1
                db.add(song)
                db.commit()
                db.refresh(song)
                update_song_in_es(song.song_id)
        if rd_type.startswith("artist"):
            artist = db.query(Artist).filter(Artist.artist_id == rd_type_id).first()
            if artist:
                songs_in_artist = db.query(Song).filter(Song.artist_id == rd_type_id).all()
            for song in songs_in_artist:
                song.recommendation_count = song.recommendation_count + 1
                db.add(song)
                db.commit()
                db.refresh(song)
                update_song_in_es(song.song_id)
        if rd_type.startswith("album"):
            album = db.query(Album).filter(Album.album_id == rd_type_id).first()
            if album:
                songs_in_album = db.query(Song).filter(Song.album_id == rd_type_id).all()
            for song in songs_in_album:
                song.recommendation_count = song.recommendation_count + 1
                db.add(song)
                db.commit()
                db.refresh(song)
                update_song_in_es(song.song_id)
        if rd_type.startswith("song"):
            song = db.query(Song).filter(Song.song_id == rd_type_id).first()
            song.recommendation_count = song.recommendation_count + 1
            db.add(song)
            db.commit()
            db.refresh(song)
            update_song_in_es(song.song_id)
        db.add(recommendation)
        db.commit()
        update_user_in_es(rd_from)
        a-=1
    return {"message":"random recommendation done successfully"}
                
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
        update_user_in_es(user)
        return {"message":"recommendation shared successfuly"}
    except:
        return {"message":"specified recommendation id doesn't exist"}