from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from subprocess import run
from pydantic import BaseModel

app = FastAPI()

# PostgreSQL database configuration
DATABASE_URL = "postgresql://postgres:root@localhost:5432/music_appln"
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define database models (corresponding to tables)
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    playlists = relationship("Playlist", back_populates="user")
    ratings = relationship("Rating", back_populates="user")
    recommendations_sent = relationship("Recommendation", foreign_keys='[Recommendation.sender_id]', back_populates="sender")
    recommendations_received = relationship("Recommendation", foreign_keys='[Recommendation.receiver_id]', back_populates="receiver")


class Song(Base):
    __tablename__ = "songs"

    song_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    artist_id = Column(Integer, ForeignKey('artists.artist_id'))
    album_id = Column(Integer, ForeignKey('albums.album_id'))
    genre_id = Column(Integer, ForeignKey('genres.genre_id'))
    duration = Column(Integer)  # Duration in seconds
    release_date = Column(DateTime, default=datetime.utcnow)


class Artist(Base):
    __tablename__ = "artists"

    artist_id = Column(Integer, primary_key=True, index=True)
    artist_name = Column(String, index=True)
    songs = relationship("Song", backref="artist")


class Album(Base):
    __tablename__ = "albums"

    album_id = Column(Integer, primary_key=True, index=True)
    album_title = Column(String, index=True)
    release_date = Column(DateTime, default=datetime.utcnow)
    artist_id = Column(Integer, ForeignKey('artists.artist_id'))
    songs = relationship("Song", backref="album")


class Genre(Base):
    __tablename__ = "genres"

    genre_id = Column(Integer, primary_key=True, index=True)
    genre_name = Column(String, index=True)
    songs = relationship("Song", backref="genre")


class Playlist(Base):
    __tablename__ = "playlists"

    playlist_id = Column(Integer, primary_key=True, index=True)
    playlist_name = Column(String, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="playlists")
    songs = relationship("Song", secondary="playlist_song")


class PlaylistSong(Base):
    __tablename__ = "playlist_song"

    playlist_song_id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey('playlists.playlist_id'))
    song_id = Column(Integer, ForeignKey('songs.song_id'))
    added_at = Column(DateTime, default=datetime.utcnow)


class Rating(Base):
    __tablename__ = "ratings"

    rating_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    song_id = Column(Integer, ForeignKey('songs.song_id'))
    rating = Column(Integer)  # Rating on a scale of 1 to 5
    rated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ratings")


class Recommendation(Base):
    __tablename__ = "recommendations"

    recommendation_id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.user_id'))
    receiver_id = Column(Integer, ForeignKey('users.user_id'))
    song_id = Column(Integer, ForeignKey('songs.song_id'))
    recommendation_type = Column(String)
    recommended_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="recommendations_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="recommendations_received")


# Create tables in the database
Base.metadata.create_all(bind=engine)


class UserCreate(BaseModel):
    username: str
    email: str
    password: str

# Pydantic model for response
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

class UserLogin(BaseModel):
    username: str
    password: str
    
# Endpoint for user registration
@app.post("/register/", response_model=UserResponse)
def register_user(user: UserCreate):
    db = SessionLocal()
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user_email = db.query(User).filter(User.email == user.email).first()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    user_response = UserResponse(
        id=new_user.user_id,
        username=new_user.username,
        email=new_user.email,
        created_at=new_user.created_at
    )
    
    db.close()
    #return {"message": "regn successful"}
    return user_response

# Endpoint for user login
@app.post("/login/")
def login_user(user: UserLogin):
    db = SessionLocal()
    db_user = db.query(User).filter(User.username == user.username).first()
    db.close()

    if db_user is None or db_user.password != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}
    
@app.get("/")
def read_root():
    return {"message": "Welcome to the music app!"}

@app.post("/load-sample-data")
def load_data():
    run(["python", "load_data_script.py"])
    return {"message": "Sample data loaded successfully!"}