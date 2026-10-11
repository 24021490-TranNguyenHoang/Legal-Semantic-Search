import json
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Import cấu hình từ src.config
from src.config import QDRANT_PATH, COLLECTION_NAME, EMBEDDED_FILE

# 1. Khởi tạo Qdrant lưu trữ cục bộ (Local Storage)
print(f"[*] Khởi tạo Qdrant Database tại: {os.path.abspath(QDRANT_PATH)}")
client = QdrantClient(path=QDRANT_PATH)

# Xóa collection cũ nếu đã tồn tại để tránh nạp trùng dữ liệu
if client.collection_exists(COLLECTION_NAME):
    client.delete_collection(COLLECTION_NAME)

# 2. Tạo Collection với kích thước vector 768 chiều
client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)

# 3. Đọc dữ liệu từ file corpus_embedded.jsonl trong data/processed/
print(f"[*] Đang đọc dữ liệu từ {EMBEDDED_FILE}...")
points = []

with open(EMBEDDED_FILE, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        if not line.strip():
            continue
        item = json.loads(line)
        
        # Tạo payload đẩy đủ các trường phục vụ Retrieval & UI
        payload = {
            "chunk_id": item.get("chunk_id"),
            "law_id": item.get("law_id"),
            "law_title": item.get("law_title"),
            "chapter": item.get("chapter"),
            "article_id": item.get("article_id"),
            "article_title": item.get("article_title"),
            "clause_id": item.get("clause_id"),
            "citation_path": item.get("citation_path"),
            "original_text": item.get("original_text"),
            "enriched_text": item.get("enriched_text"),
            "effective_date": item.get("effective_date"),
            "status": item.get("status")
        }
        
        point = PointStruct(
            id=idx,
            vector=item["vector"],
            payload=payload
        )
        points.append(point)

# 4. Đẩy toàn bộ dữ liệu vào Qdrant theo batch
batch_size = 100
total_points = len(points)
print(f"[*] Đang nạp {total_points} vector vào Qdrant...")

for i in range(0, total_points, batch_size):
    batch = points[i:i + batch_size]
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=batch
    )

print(f"[+] Nạp thành công {total_points} vector vào Collection '{COLLECTION_NAME}'!")