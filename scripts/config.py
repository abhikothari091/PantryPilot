import os
from dotenv import load_dotenv
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")  
RAW_PATH = "data_pipeline/data/raw/"
PROCESSED_PATH = "data_pipeline/data/processed/"
ALERT_PATH = "data_pipeline/data/alerts/"