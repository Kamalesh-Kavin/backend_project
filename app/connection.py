from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from elasticsearch import Elasticsearch
from models import create_tables
from dotenv import load_dotenv
import os

load_dotenv()

#DB connectivity
engine = create_engine(os.environ.get("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

#ES connectivity

es = Elasticsearch(hosts=os.environ.get("ELASTICSEARCH_URL"),basic_auth=(os.environ.get("ELASTICSEARCH_USERNAME"),os.environ.get("ELASTICSEARCH_PASSWORD") ), verify_certs=False, timeout=100)

def create_index():
    INDEX_NAMES = ["users_","songs_"]
    for i in INDEX_NAMES:
        if not es.indices.exists(index=i):
                es.indices.create(index=i)