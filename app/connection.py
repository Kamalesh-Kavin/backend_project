from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from elasticsearch import Elasticsearch
from .models import create_tables

#DB connectivity
DATABASE_URL = "postgresql://postgres:root@postgres-db:5432/music_appln"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

#ES connectivity
ELASTICSEARCH_URL = "https://host.docker.internal:9200"
es = Elasticsearch(hosts=ELASTICSEARCH_URL,basic_auth=("elastic", "xBiSrG0ZZg0Mw5V5EeNo"), verify_certs=False)

def create_index():
    INDEX_NAMES = ["users_","songs_"]
    for i in INDEX_NAMES:
        if not es.indices.exists(index=i):
                es.indices.create(index=i)