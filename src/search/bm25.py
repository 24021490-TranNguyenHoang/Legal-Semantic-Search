import os
import json
from rank_bm25 import BM25Okapi

class BM25Searcher:
    def __init__(self, corpus_path="data/processed/chunks.json"):
        # Khởi tạo và load dữ liệu text để chạy BM25 baseline
        self.corpus = []
        self.tokenized_corpus = []
        self._load_corpus(corpus_path)
        
    def _load_corpus(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.corpus = json.load(f)
            # Tokenize đơn giản bằng cách tách khoảng trắng (hoặc tiếng Việt tùy ý)
            self.tokenized_corpus = [doc.get("chunk_text", "").lower().split() for doc in self.corpus]
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            # Fallback dữ liệu mẫu nếu chưa có file chunks.json
            self.corpus = [
                {"article_title": "Điều 1. Phạm vi điều chỉnh", "chunk_text": "Luật này quy định về quy tắc giao thông đường bộ...", "document_id": "35.2024.QH15"},
                {"article_title": "Điều 2. Giải thích từ ngữ", "chunk_text": "Phương tiện giao thông đường bộ bao gồm phương tiện giao thông cơ giới...", "document_id": "35.2024.QH15"}
            ]
            self.tokenized_corpus = [doc["chunk_text"].lower().split() for doc in self.corpus]
            self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query_text, top_k=3):
        tokenized_query = query_text.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        
        # Sắp xếp điểm số giảm dần
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in top_indices:
            doc = self.corpus[idx].copy()
            doc["score"] = float(scores[idx])
            results.append(doc)
        return results