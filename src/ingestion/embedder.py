import json
import time
from sentence_transformers import SentenceTransformer

input_jsonl = "corpus_chunks.jsonl"
output_embedded_jsonl = "corpus_embedded.jsonl"

print("[*] Đang tải mô hình nhúng tiếng Việt...")
model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")

print(f"[*] Đang đọc dữ liệu từ '{input_jsonl}'...")
chunks = []
with open(input_jsonl, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            chunks.append(json.loads(line))

total = len(chunks)
print(f"[*] Tổng số chunks cần embedding: {total}")

texts = [item["text"] for item in chunks]

print("[*] Bắt đầu sinh vector nhúng trên CPU...")
start_time = time.time()

embeddings = model.encode(texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)

embedded_chunks = []
for chunk, emb in zip(chunks, embeddings):
    chunk["vector"] = emb.tolist()
    embedded_chunks.append(chunk)

with open(output_embedded_jsonl, "w", encoding="utf-8") as out_f:
    for chk in embedded_chunks:
        out_f.write(json.dumps(chk, ensure_ascii=False) + "\n")

elapsed = time.time() - start_time
print(f"\n[+] HOÀN THÀNH!")
print(f"[+] Đã xử lý {len(embedded_chunks)}/{total} chunks trong {elapsed:.1f} giây.")
print(f"[+] Dữ liệu đã lưu tại: '{output_embedded_jsonl}'")