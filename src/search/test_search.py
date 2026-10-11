import json
import numpy as np
from sentence_transformers import SentenceTransformer

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.norm(a) * np.norm(b))

# 1. Tải mô hình để mã hóa câu hỏi người dùng
print("[*] Đang tải mô hình nhúng...")
model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")

# 2. Đọc corpus đã nhúng vector
print("[*] Đang nạp dữ liệu từ corpus_embedded.jsonl...")
chunks = []
with open("corpus_embedded.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            chunks.append(json.loads(line))

print(f"[+] Đã tải {len(chunks)} chunks vào bộ nhớ.")

# 3. Thử nghiệm một câu truy vấn thực tế
query = "vượt đèn đỏ xe máy bị phạt bao nhiêu tiền và trừ mấy điểm"
print(f"\n[*] Câu hỏi thử nghiệm: '{query}'")

# Mã hóa câu hỏi thành vector
query_vector = model.encode(query, normalize_embeddings=True)

# 4. Tính điểm tương đồng với toàn bộ chunks
results = []
for item in chunks:
    doc_vec = np.array(item["vector"])
    score = np.dot(query_vector, doc_vec)  # Do đã chuẩn hóa vector nên tích vô hướng chính là cosine similarity
    results.append((score, item))

# Sắp xếp lấy Top 3 kết quả điểm cao nhất
results.sort(key=lambda x: x[0], reverse=True)

print("\n" + "="*80)
print("TOP 3 KẾT QUẢ TÌM KIẾM NGỮ NGHĨA (DENSE RETRIEVAL):")
print("="*80)

for rank, (score, item) in enumerate(results[:3], start=1):
    print(f"\n[Hạng {rank}] - Điểm tương đồng: {score:.4f}")
    print(f"Trích dẫn: {item.get('citation_path')}")
    print(f"Nội dung: {item.get('text')[:300]}...")