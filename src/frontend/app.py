import streamlit as st
import json
import re
import torch
from transformers import AutoTokenizer, AutoModel
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi
from pathlib import Path

st.set_page_config(page_title="Tra cứu Pháp luật Giao thông VN", page_icon="⚖️", layout="wide")

MODEL_NAME = "bkai-foundation-models/vietnamese-bi-encoder"
CHUNKS_PATH = Path("data/processed/corpus_chunks.jsonl")

def simple_tokenize(text: str):
    """Tách từ đơn giản bằng regex chuẩn hóa."""
    return re.findall(r"\w+", text.lower())

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask

@st.cache_resource
def load_resources():
    # 1. Kết nối Qdrant
    client = QdrantClient(path="./qdrant_db")
    
    # 2. Tải mô hình Embedding bằng Transformers + PyTorch (né 100% lỗi sklearn/DLL của Windows)
    print(f"[*] Đang tải mô hình NLP cho giao diện: {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME)
    model.eval()
    
    # 3. Nạp danh sách chunks từ thư mục data/processed/
    chunks = []
    if CHUNKS_PATH.exists():
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
    else:
        st.error(f"Không tìm thấy file dữ liệu tại {CHUNKS_PATH}. Hãy chạy lại chunker trước!")
                
    # Dùng trường enriched_text hoặc text tùy thuộc vào schema đã tạo
    tokenized_corpus = [simple_tokenize(c.get("enriched_text") or c.get("text", "")) for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
    
    return client, tokenizer, model, chunks, bm25

client, tokenizer, model, chunks, bm25 = load_resources()
collection_name = "legal_vn_traffic"

def encode_query(query_text):
    encoded_input = tokenizer(query_text, padding=True, truncation=True, max_length=256, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)
    embedding = mean_pooling(model_output, encoded_input['attention_mask'])
    # Chuẩn hóa vector (Normalize) giống như cosine similarity yêu cầu
    vector = embedding[0]
    vector = vector / vector.norm(p=2)
    return vector.tolist()

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
st.caption("Ứng dụng kiến trúc Hybrid Search (BM25 + Dense Retrieval) trên dữ liệu pháp lý thực tế")

query = st.text_input("Nhập câu hỏi tra cứu hoặc từ khóa vi phạm:", placeholder="Ví dụ: vượt đèn đỏ xe máy bị phạt bao nhiêu tiền và trừ mấy điểm")

top_k = st.slider("Số lượng kết quả hiển thị (Top K):", min_value=3, max_value=10, value=3)

if st.button("🔍 Tra cứu quy định", type="primary"):
    if query.strip():
        if not chunks or bm25 is None:
            st.error("Dữ liệu chunks chưa được tải thành công. Vui lòng kiểm tra lại quá trình chạy ingestion pipeline!")
        else:
            with st.spinner("Đang thực hiện Hybrid Search..."):
                # 1. Dense Retrieval (Qdrant)
                query_vector = encode_query(query)
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
                        st.markdown(f"**Văn bản:** {item.get('law_title', 'Luật Giao thông')} ({item.get('law_id')})")
                        st.markdown("**Nội dung quy định:**")
                        # Hiển thị ưu tiên enriched_text hoặc original_text hoặc text thô
                        content_to_show = item.get("original_text") or item.get("enriched_text") or item.get("text", "")
                        st.info(content_to_show)
    else:
        st.warning("Vui lòng nhập câu hỏi trước khi tìm kiếm!")