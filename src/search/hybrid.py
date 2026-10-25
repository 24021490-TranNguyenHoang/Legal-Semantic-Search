from src.search.dense import DenseSearcher
from src.search.bm25 import BM25Searcher

class HybridSearcher:
    def __init__(self):
        self.dense_searcher = DenseSearcher()
        try:
            self.bm25_searcher = BM25Searcher()
        except Exception:
            self.bm25_searcher = None

    def search(self, query_text, document_id_filter=None, top_k=3, alpha=0.5):
        """
        alpha: Trọng số cân bằng giữa Dense (Vector) và BM25 (Keyword)
        alpha = 1.0 nghĩa là chỉ dùng Dense, alpha = 0.0 nghĩa là chỉ dùng BM25.
        """
        # Lấy kết quả từ Dense Search
        dense_results = self.dense_searcher.search(query_text, document_id_filter=document_id_filter, top_k=top_k * 2)
        
        # Nếu có BM25, kết hợp điểm số (Reciprocal Rank Fusion hoặc Linear Combination)
        if self.bm25_searcher:
            bm25_results = self.bm25_searcher.search(query_text, top_k=top_k * 2)
            
            # Gộp kết quả đơn giản theo điểm score quy đổi
            combined_dict = {}
            
            for item in dense_results:
                key = item.get("article_title")
                combined_dict[key] = {
                    **item,
                    "score": alpha * item.get("score", 0.0)
                }
                
            for item in bm25_results:
                key = item.get("article_title")
                if key in combined_dict:
                    combined_dict[key]["score"] += (1 - alpha) * (item.get("score", 0.0) / 10.0) # Chuẩn hóa điểm bm25
                else:
                    combined_dict[key] = {
                        **item,
                        "score": (1 - alpha) * (item.get("score", 0.0) / 10.0)
                    }
                    
            # Sắp xếp lại theo điểm hybrid score giảm dần
            sorted_results = sorted(combined_dict.values(), key=lambda x: x["score"], reverse=True)
            return sorted_results[:top_k]
            
        return dense_results[:top_k]