from sqlalchemy.orm import Session
from datetime import datetime
from main import User, Song, Artist, Album, Genre, Playlist, PlaylistSong, Rating, Recommendation, engine, SessionLocal

# Function to add sample data to tables
def load_sample_data():
    db = SessionLocal()

    # Sample users
    users_data = [
        {"username": "user1", "email": "user1@example.com", "password": "password1"},
        {"username": "user2", "email": "user2@example.com", "password": "password2"},
        # Add more sample users
    ]

    for user in users_data:
        db.add(User(**user))

    db.commit()

    # Sample songs, artists, albums, genres
    # Add sample data for songs, artists, albums, genres

    # Sample playlists
    playlists_data = [
        {"playlist_name": "Favorites", "user_id": 1},  # Assuming user_id 1 is user1
        {"playlist_name": "Workout Mix", "user_id": 2},  # Assuming user_id 2 is user2
        # Add more sample playlists
    ]

    for playlist in playlists_data:
        db.add(Playlist(**playlist))

    db.commit()

    # Sample playlist-song associations
    # Add sample associations between playlists and songs

    # Sample ratings
    ratings_data = [
        {"user_id": 1, "song_id": 1, "rating": 5},  # User 1 rates song 1 with a rating of 5
        {"user_id": 2, "song_id": 2, "rating": 4},  # User 2 rates song 2 with a rating of 4
        # Add more sample ratings
    ]

    for rating in ratings_data:
        db.add(Rating(**rating))

    db.commit()

    # Sample recommendations
    recommendations_data = [
        {"sender_id": 1, "receiver_id": 2, "song_id": 3, "recommendation_type": "song"},
        # Add more sample recommendations
    ]

    for recommendation in recommendations_data:
        db.add(Recommendation(**recommendation))

    db.commit()

    db.close()

# Load sample data into the tables
if __name__ == "__main__":
    load_sample_data()
