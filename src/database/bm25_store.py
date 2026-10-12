import json
import pickle
import os
from pathlib import Path
from rank_bm25 import BM25Okapi
from src.config import EMBEDDED_FILE, BASE_DIR

# Nơi lưu file BM25 index
BM25_INDEX_PATH = BASE_DIR / "qdrant_db" / "bm25_index.pkl"

def build_and_save_bm25():
    print(f"[*] Đang đọc dữ liệu từ {EMBEDDED_FILE}...")
    valid_corpus = []
    valid_chunk_ids = []
    tokenized_corpus = []

    if not EMBEDDED_FILE.exists():
        print(f"[!] Lỗi: Không tìm thấy file {EMBEDDED_FILE}")
        return

    with open(EMBEDDED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            # Ưu tiên lấy enriched_text, fallback về original_text
            text = (item.get("enriched_text") or item.get("original_text") or "").strip()
            
            # Tách từ cơ bản
            tokens = text.lower().split()
            
            # Chỉ lấy các chunk có từ vựng thực sự để tránh ZeroDivisionError
            if tokens:
                valid_corpus.append(text)
                valid_chunk_ids.append(item.get("chunk_id"))
                tokenized_corpus.append(tokens)

    print(f"[*] Đã lọc được {len(valid_corpus)} chunks hợp lệ có nội dung.")
    
    if not tokenized_corpus:
        print("[!] Không có văn bản hợp lệ để tạo chỉ mục BM25!")
        return

    print("[*] Đang tính toán chỉ mục BM25Okapi...")
    bm25 = BM25Okapi(tokenized_corpus)

    bm25_data = {
        "bm25_model": bm25,
        "chunk_ids": valid_chunk_ids,
        "corpus": valid_corpus
    }

    print(f"[*] Đang lưu BM25 Index ra file: {BM25_INDEX_PATH}")
    BM25_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25_data, f)

    print("[+] Hoàn tất! Đã lưu trữ Inverted Index cho BM25 thành công.")

if __name__ == "__main__":
    build_and_save_bm25()