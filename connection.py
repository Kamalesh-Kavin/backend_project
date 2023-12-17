from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from elasticsearch import Elasticsearch
from models import create_tables

#DB connectivity
DATABASE_URL = "postgresql://postgres:root@localhost:5432/music_appln"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

#ES connectivity
ELASTICSEARCH_URL = "https://localhost:9200"
es = Elasticsearch(hosts=ELASTICSEARCH_URL,basic_auth=("elastic", "1_W28jlMre-sx005bcoB"), verify_certs=False)

create_tables(engine)