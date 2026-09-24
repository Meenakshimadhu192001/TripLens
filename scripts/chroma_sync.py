import os
import sqlite3
import chromadb
from chromadb.utils import embedding_functions

DB_PATH = os.path.join("database", "triplens.db")
CHROMA_PATH = os.path.join("database", "chroma_db")

client = chromadb.PersistentClient(path=CHROMA_PATH)
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = client.get_or_create_collection(
    name="travel_packages",
    embedding_function=embedding_func
)

def sync_package_to_chroma(canonical_doc):
    pkg_id = canonical_doc["package_id"]
    metadata = {
        "package_id": pkg_id,
        "package_name": str(canonical_doc["package_name"]),
        "start_location": str(canonical_doc["start_location"]),
        "duration_days": int(canonical_doc["duration_days"]) if canonical_doc["duration_days"] else 0,
        "price": float(canonical_doc["price"]) if canonical_doc["price"] else 0.0,
        "total_transit_hours": float(canonical_doc["total_transit_hours"])
    }
    collection.upsert(
        ids=[pkg_id],
        documents=[canonical_doc["canonical_text"]],
        metadatas=[metadata]
    )

def sync_all_existing_packages():
    from scripts.data_access import fetch_all_canonical_documents
    docs = fetch_all_canonical_documents()
    print(f"[CHROMA] Indexing {len(docs)} packages into ChromaDB...")
    
    ids = [d["package_id"] for d in docs]
    texts = [d["canonical_text"] for d in docs]
    metas = [{
        "package_id": d["package_id"],
        "package_name": str(d["package_name"]),
        "start_location": str(d["start_location"]),
        "duration_days": int(d["duration_days"]) if d["duration_days"] else 0,
        "price": float(d["price"]) if d["price"] else 0.0,
        "total_transit_hours": float(d["total_transit_hours"])
    } for d in docs]
    
    batch_size = 50
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i:i+batch_size],
            documents=texts[i:i+batch_size],
            metadatas=metas[i:i+batch_size]
        )
    print(f"[CHROMA COMPLETE] Total vectors in collection: {collection.count()}")

if __name__ == "__main__":
    sync_all_existing_packages()
