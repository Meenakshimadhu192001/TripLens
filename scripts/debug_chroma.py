import chroma_sync

print("CHROMA PATH:")
print(chroma_sync.CHROMA_PATH)

print("COLLECTION:")
print(chroma_sync.collection.name)

print("COUNT:")
print(chroma_sync.collection.count())

print("TEST001:")
print(
    chroma_sync.collection.get(
        ids=["TEST001"]
    )
)