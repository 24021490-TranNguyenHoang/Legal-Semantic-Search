import streamlit as st
import json
import re
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

st.set_page_config(page_title="Tra cứu Pháp luật Giao thông VN", page_icon="⚖️", layout="wide")

def simple_tokenize(text: str):
    """Tách từ đơn giản bằng regex chuẩn hóa."""
    return re.findall(r"\w+", text.lower())

@st.cache_resource
def load_resources():
    # 1. Kết nối Qdrant
    client = QdrantClient(path="./qdrant_db")
    
    # 2. Tải mô hình Embedding
    model = SentenceTransformer("bkai-foundation-models/vietnamese-bi-encoder")
    
    # 3. Nạp danh sách chunks để xây dựng chỉ mục BM25
    chunks = []
    with open("corpus_chunks.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    tokenized_corpus = [simple_tokenize(c["text"]) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    
    return client, model, chunks, bm25

client, model, chunks, bm25 = load_resources()
collection_name = "legal_vn_traffic"

def reciprocal_rank_fusion(dense_ranks, sparse_ranks, k=60):
    """Thuật toán Reciprocal Rank Fusion (RRF) để kết hợp 2 bảng xếp hạng."""
    rrf_scores = {}
    
    for rank, doc_id in enumerate(dense_ranks, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        
    for rank, doc_id in enumerate(sparse_ranks, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        
    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_docs

# --- GIAO DIỆN WEB ---
st.title("⚖️ Hệ thống Tìm kiếm Pháp luật Giao thông Đường bộ")
st.caption("Ứng dụng kiến trúc Hybrid Search (BM25 + Dense Retrieval) trên 1.457 đơn vị pháp lý")

query = st.text_input("Nhập câu hỏi tra cứu hoặc từ khóa vi phạm:", placeholder="Ví dụ: vượt đèn đỏ xe máy bị phạt bao nhiêu tiền và trừ mấy điểm")

top_k = st.slider("Số lượng kết quả hiển thị (Top K):", min_value=3, max_value=10, value=3)

if st.button("🔍 Tra cứu quy định", type="primary"):
    if query.strip():
        with st.spinner("Đang thực hiện Hybrid Search..."):
            # 1. Dense Retrieval (Qdrant)
            query_vector = model.encode(query, normalize_embeddings=True).tolist()
            dense_response = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=30
            )
            dense_ids = [hit.id for hit in dense_response.points]
            
            # 2. Sparse Retrieval (BM25)
            tokenized_query = simple_tokenize(query)
            bm25_scores = bm25.get_scores(tokenized_query)
            sparse_ids = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:30]
            
            # 3. Dung hợp kết quả bằng RRF
            fused_results = reciprocal_rank_fusion(dense_ids, sparse_ids, k=60)[:top_k]
            
            st.success("Kết quả tra cứu tối ưu:")
            for rank, (doc_idx, rrf_score) in enumerate(fused_results, start=1):
                item = chunks[doc_idx]
                with st.expander(f"Top {rank} [RRF Score: {rrf_score:.4f}] - {item.get('citation_path')}", expanded=(rank == 1)):
                    st.markdown(f"**Văn bản:** {item.get('law_title')} ({item.get('law_id')})")
                    st.markdown("**Nội dung quy định:**")
                    st.info(item.get("text"))
    else:
        st.warning("Vui lòng nhập câu hỏi trước khi tìm kiếm!")