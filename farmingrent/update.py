from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient("mongodb://localhost:27017/")
db = client["farmingrent"]
toolsdb = db["tools"]

for tool in toolsdb.find():
    if "t_id" not in tool:
        toolsdb.update_one(
            {"_id": tool["_id"]},
            {"$set": {"t_id": str(tool["_id"])}}
        )
print("All documents updated with t_id!")
