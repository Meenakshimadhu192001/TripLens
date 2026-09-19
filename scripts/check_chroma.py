import os
import chromadb

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

CHROMA_PATH = os.path.join(
    BASE_DIR,
    "database",
    "chroma_db"
)

client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = client.get_collection(
    name="travel_packages"
)

print("ChromaDB document count:", collection.count())

result = collection.get(
    ids=["TEST001"],
    include=["documents", "metadatas"]
)

print("\nTEST001 result:")
print(result)