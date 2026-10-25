import os
import sys
import time
import streamlit as st

# Thêm đường dẫn gốc để import module tìm kiếm
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

# Import các searcher từ thư mục src/search/
from src.search.dense import DenseSearcher
from src.search.bm25 import BM25Searcher
from src.search.hybrid import HybridSearcher
from src.search.reranker import Reranker

# Khởi tạo giao diện Streamlit
st.set_page_config(
    page_title="Legal Semantic Search",
    page_icon="⚖️",
    layout="wide",
)

# --- CACHE CÁC MÔ HÌNH TÌM KIẾM ĐỂ TĂNG TỐC ĐỘ KHỞI ĐỘNG ---
@st.cache_resource
def load_search_engines():
    dense_engine = DenseSearcher()
    bm25_engine = BM25Searcher()
    hybrid_engine = HybridSearcher()
    reranker_engine = Reranker()
    return {
        "dense": dense_engine,
        "bm25": bm25_engine,
        "hybrid": hybrid_engine,
        "reranker": reranker_engine
    }

with st.spinner("Đang khởi động hệ thống tìm kiếm & nạp mô hình AI..."):
    engines = load_search_engines()

# --- HÀM TẠO CÂU TRẢ LỜI TỪ LLM (RAG GENERATION) ---
def generate_rag_response(query, search_results):
    if not search_results:
        return "Xin lỗi, tôi không tìm thấy quy định pháp luật nào trong hệ thống liên quan đến câu hỏi của bạn."
    
    context_titles = [f"- {item.get('article_title', 'Điều luật')} ({item.get('document_id', '35.2024.QH15')})" for item in search_results]
    context_str = "\n".join(context_titles)
    
    response = (
        f"Dựa trên các quy định pháp luật hiện hành, tôi xin giải đáp vấn đề **'{query}'** của bạn như sau:\n\n"
        f"Theo thông tin tra cứu được, vấn đề này được quy định chi tiết tại:\n"
        f"{context_str}\n\n"
        f"*(Bạn có thể xem chi tiết trích dẫn luật ở thẻ 'Xem nguồn trích dẫn' bên dưới).*"
    )
    return response

# --- GIAO DIỆN CHÍNH ---
st.title("⚖️ Legal Semantic Search")
st.caption("Hệ thống tìm kiếm ngữ nghĩa văn bản pháp luật sử dụng Qdrant Vector DB, Hybrid Search & Reranker")

# Sidebar cấu hình chiến lược tìm kiếm
with st.sidebar:
    st.header("⚙️ Cấu hình hệ thống")
    
    # Cho phép chọn chiến lược tìm kiếm
    search_strategy = st.selectbox(
        "Chiến lược tìm kiếm:",
        options=["Dense Search", "BM25 Search", "Hybrid Search", "Hybrid + Reranker"],
        index=2 # Mặc định chọn Hybrid Search
    )
    
    # --- KHUNG CHÚ THÍCH ĐỂ PHÂN BIỆT CÁC CHIẾN LƯỢC ---
    with st.expander("📖 Giải thích chiến lược", expanded=True):
        if search_strategy == "Dense Search":
            st.markdown(
                "**Mô tả:** Tìm kiếm dựa trên Vector ngữ nghĩa (Embedding).\n\n"
                "• **Ưu điểm:** Hiểu được ý nghĩa câu hỏi dù dùng từ đồng nghĩa.\n"
                "• **Kết quả:** Trả về các điều luật có chung ngữ nghĩa sâu với câu hỏi."
            )
        elif search_strategy == "BM25 Search":
            st.markdown(
                "**Mô tả:** Tìm kiếm dựa trên từ khóa truyền thống (Keyword-based).\n\n"
                "• **Ưu điểm:** Khớp chính xác tuyệt đối từng từ khóa, mã số điều luật.\n"
                "• **Kết quả:** Phù hợp khi tìm kiếm điều khoản cụ thể (VD: 'Điều 1')."
            )
        elif search_strategy == "Hybrid Search":
            st.markdown(
                "**Mô tả:** Kết hợp song song Dense + BM25.\n\n"
                "• **Ưu điểm:** Vừa hiểu ngữ nghĩa vừa khớp từ khóa.\n"
                "• **Kết quả:** Độ bao phủ tài liệu (Recall) cao hơn, tránh bỏ sót."
            )
        elif search_strategy == "Hybrid + Reranker":
            st.markdown(
                "**Mô tả:** Hybrid kết hợp chấm điểm sâu lại bằng Cross-Encoder.\n\n"
                "• **Ưu điểm:** Độ chính xác (Precision) cao nhất.\n"
                "• **Kết quả:** Sắp xếp lại để đưa điều luật chuẩn xác nhất lên Top 1."
            )

    document_filter = st.selectbox(
        "Lọc theo văn bản:",
        options=[None, "35.2024.QH15"],
        format_func=lambda x: "Tất cả văn bản" if x is None else "Luật Đường bộ 2024"
    )
    
    top_k = st.slider("Số lượng tài liệu trích xuất (Top-K):", 1, 5, 3)
    
    st.markdown("---")
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()

# Khởi tạo session_state lưu lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Tôi là hệ thống Legal Semantic Search. Hãy chọn chiến lược tìm kiếm ở thanh bên trái và đặt câu hỏi cho tôi nhé!"}
    ]

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        if "latency" in msg and msg["role"] == "assistant":
            st.caption(f"⚡ Thời gian phản hồi: `{msg['latency']:.4f}s` | Chiến lược: `{msg.get('strategy', 'N/A')}`")
            
        if msg["role"] == "assistant" and "sources" in msg and msg["sources"]:
            with st.expander("📚 Xem nguồn trích dẫn luật chi tiết"):
                for idx, source in enumerate(msg["sources"]):
                    score = source.get('score', 0.0)
                    st.markdown(f"**{idx + 1}. {source.get('article_title', 'Điều luật')}** (Score: `{score:.4f}`)")
                    st.info(source.get('chunk_text', ''))

# Ô nhập liệu chat của người dùng
if prompt := st.chat_input("Nhập câu hỏi pháp lý của bạn vào đây..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"Đang tìm kiếm bằng chiến lược [{search_strategy}]..."):
            start_time = time.time()
            
            retrieved_docs = []
            if search_strategy == "Dense Search":
                retrieved_docs = engines["dense"].search(prompt, document_id_filter=document_filter, top_k=top_k)
            elif search_strategy == "BM25 Search":
                retrieved_docs = engines["bm25"].search(prompt, top_k=top_k)
            elif search_strategy == "Hybrid Search":
                retrieved_docs = engines["hybrid"].search(prompt, document_id_filter=document_filter, top_k=top_k)
            elif search_strategy == "Hybrid + Reranker":
                hybrid_results = engines["hybrid"].search(prompt, document_id_filter=document_filter, top_k=top_k * 2)
                retrieved_docs = engines["reranker"].rerank(prompt, hybrid_results, top_k=top_k)
            
            end_time = time.time()
            latency = end_time - start_time
            
            bot_response = generate_rag_response(prompt, retrieved_docs)
            
            st.markdown(bot_response)
            st.caption(f"⚡ Thời gian phản hồi: `{latency:.4f}s` | Chiến lược: `{search_strategy}`")
            
            if retrieved_docs:
                with st.expander("📚 Xem nguồn trích dẫn luật chi tiết"):
                    for idx, doc in enumerate(retrieved_docs):
                        score = doc.get('score', 0.0)
                        st.markdown(f"**{idx + 1}. {doc.get('article_title', 'Điều luật')}** (Score: `{score:.4f}`)")
                        st.info(doc.get('chunk_text', ''))
            
    st.session_state.messages.append({
        "role": "assistant", 
        "content": bot_response,
        "sources": retrieved_docs,
        "latency": latency,
        "strategy": search_strategy
    })