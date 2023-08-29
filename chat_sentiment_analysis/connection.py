from pymongo import MongoClient
import os

# Insert connection string and db name:
client = MongoClient(os.environ.get('ConnectionString'))
db = client[os.environ.get('DbName')]

chats_db = db["chats"]
messages_db = db["messages"]