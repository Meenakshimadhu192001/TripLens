import sys
sys.path.insert(0, "scripts")

import chroma_sync

print("START")

d = chroma_sync.get_package_document("HP002")

print("DOCUMENT READY")
print("LENGTH:", len(d))

try:
    chroma_sync.collection.upsert(
        ids=["HP002"],
        documents=[d],
        metadatas=[{"package_id": "HP002"}]
    )
    print("UPSERT SUCCESS")
except Exception as e:
    print("ERROR:", repr(e))

print("END")