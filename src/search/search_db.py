import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# 1. Kết nối với Qdrant Database (Local)
db_path = "./qdrant_db"
collection_name = "legal_vn_traffic"

print("[*] Đang kết nối Qdrant Database...")
client = QdrantClient(path=db_path)

print("[*] Đang tải mô hình Embedding...")
model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")

# 2. Đặt câu hỏi
query = "vượt đèn đỏ xe máy bị phạt bao nhiêu tiền và trừ mấy điểm"
print(f"\n[?] Câu hỏi người dùng: '{query}'\n")

# 3. Chuyển đổi câu hỏi thành Vector
query_vector = model.encode(query, normalize_embeddings=True).tolist()

# 4. Thực hiện tìm kiếm Vector cực nhanh trong Qdrant bằng hàm API mới
print("[*] Đang quét toàn bộ database...")
response = client.query_points(
    collection_name=collection_name,
    query=query_vector, # Thay 'query_vector=' thành 'query='
    limit=3             # Lấy 3 kết quả tốt nhất
)
search_results = response.points # Lấy danh sách kết quả từ response

# 5. In kết quả
print("="*80)
print("KẾT QUẢ TÌM KIẾM TỪ QDRANT VECTOR DATABASE:")
print("="*80)

for rank, hit in enumerate(search_results, start=1):
    payload = hit.payload
    print(f"\n[Top {rank}] - Điểm Vector (Score): {hit.score:.4f}")
    print(f"Trích dẫn: {payload.get('citation_path')}")
    print(f"Nội dung: {payload.get('text')[:350]}...")