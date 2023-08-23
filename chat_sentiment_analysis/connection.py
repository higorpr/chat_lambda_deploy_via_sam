from pymongo import MongoClient
import os

# Insert connection string and db name:
client = MongoClient(os.environ['ConnectionString'])
db = client[os.environ['DbName']]

chats_db = db["chats"]
messages_db = db["messages"]