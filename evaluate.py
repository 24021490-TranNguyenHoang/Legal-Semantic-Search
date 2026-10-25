import time
import numpy as np
from src.search.dense import DenseSearcher
from src.search.bm25 import BM25Searcher
from src.search.hybrid import HybridSearcher

# 1. Định nghĩa tập Test Set gồm các câu hỏi mẫu và Điều luật chuẩn cần tìm (Ground Truth)
TEST_DATASET = [
    {
        "query": "Phạm vi điều chỉnh của luật giao thông đường bộ",
        "relevant_doc": "Điều 1. Phạm vi điều chỉnh"
    },
    {
        "query": "Phương tiện giao thông cơ giới đường bộ gồm những gì",
        "relevant_doc": "Điều 2. Giải thích từ ngữ"
    }
]

def calculate_mrr(relevant_doc, retrieved_results):
    """Tính Mean Reciprocal Rank (MRR)"""
    for rank, doc in enumerate(retrieved_results, start=1):
        if doc.get("article_title") == relevant_doc:
            return 1.0 / rank
    return 0.0

def calculate_recall(relevant_doc, retrieved_results, k=3):
    """Tính Recall@K"""
    top_k_docs = retrieved_results[:k]
    for doc in top_k_docs:
        if doc.get("article_title") == relevant_doc:
            return 1.0
    return 0.0

def evaluate_system():
    print("🚀 Bắt đầu chạy Evaluation Benchmark cho các chiến lược tìm kiếm...")
    
    # Khởi tạo các engine tìm kiếm
    dense_engine = DenseSearcher()
    bm25_engine = BM25Searcher()
    hybrid_engine = HybridSearcher()
    
    strategies = {
        "Dense Search": dense_engine,
        "BM25 Search": bm25_engine,
        "Hybrid Search": hybrid_engine
    }
    
    results_summary = {}
    
    for name, engine in strategies.items():
        mrr_scores = []
        recall_scores = []
        latencies = []
        
        for item in TEST_DATASET:
            query = item["query"]
            target = item["relevant_doc"]
            
            start_time = time.time()
            if name == "BM25 Search":
                res = engine.search(query, top_k=3)
            else:
                res = engine.search(query, top_k=3)
            end_time = time.time()
            
            latencies.append(end_time - start_time)
            mrr_scores.append(calculate_mrr(target, res))
            recall_scores.append(calculate_recall(target, res, k=3))
            
        results_summary[name] = {
            "MRR": np.mean(mrr_scores),
            "Recall@3": np.mean(recall_scores),
            "Avg Latency (s)": np.mean(latencies)
        }
        
    # In bảng báo cáo kết quả tổng kết ra Terminal
    print("\n" + "="*50)
    print(f"{'CHIẾN LƯỢC TÌM KIẾM':<20} | {'MRR':<8} | {'Recall@3':<10} | {'LATENCY (s)':<10}")
    print("="*50)
    for name, metrics in results_summary.items():
        print(f"{name:<20} | {metrics['MRR']:<8.2f} | {metrics['Recall@3']:<10.2f} | {metrics['Avg Latency (s)']:<10.4f}")
    print("="*50)
    print("✅ Đã hoàn thành đánh giá hệ thống!")

if __name__ == "__main__":
    evaluate_system()
    