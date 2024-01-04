from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from elasticsearch import Elasticsearch
from models import create_tables

#DB connectivity
DATABASE_URL = "postgresql://kamal:root@postgres-service:5432/music_appln"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

#ES connectivity
ELASTICSEARCH_URL = "https://host.minikube.internal:9200"
es = Elasticsearch(hosts=ELASTICSEARCH_URL,basic_auth=("elastic","-_ZkEca-LNVXq=x*yR__" ), verify_certs=False)
# es = Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme':'http'}])
def create_index():
    INDEX_NAMES = ["users_","songs_"]
    for i in INDEX_NAMES:
        if not es.indices.exists(index=i):
                es.indices.create(index=i)