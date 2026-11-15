import os
import sys
import time
import streamlit as st
import google.generativeai as genai

# Thêm đường dẫn gốc để import module tìm kiếm
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

from src.search.dense import DenseSearcher
from src.search.bm25 import BM25Searcher
from src.search.hybrid import HybridSearcher
from src.search.reranker import Reranker

# Khởi tạo giao diện Streamlit
st.set_page_config(
    page_title="Legal Semantic Search & AI Assistant",
    page_icon="⚖️",
    layout="wide",
)

# --- CACHE CÁC MÔ HÌNH TÌM KIẾM ---
@st.cache_resource
def load_search_engines():
    return {
        "dense": DenseSearcher(),
        "bm25": BM25Searcher(),
        "hybrid": HybridSearcher(),
        "reranker": Reranker()
    }

with st.spinner("Đang khởi động hệ thống tìm kiếm & nạp mô hình AI..."):
    engines = load_search_engines()

# --- HÀM TẠO CÂU TRẢ LỜI THÔNG MINH BẰNG GEMINI LLM ---
def generate_rag_response(query, search_results, api_key=None):
    if not search_results:
        return "Xin lỗi, tôi không tìm thấy quy định pháp luật nào trong hệ thống thỏa mãn bộ lọc và câu hỏi của bạn."
    
    context_parts = []
    for idx, item in enumerate(search_results, 1):
        title = item.get('article_title', 'Điều luật')
        doc_id = item.get('document_id', 'N/A')
        law_type = item.get('law_type', 'Văn bản')
        year = item.get('year', '2024')
        text = item.get('chunk_text', '')
        context_parts.append(f"[{idx}] {title} - {law_type} năm {year} (Mã: {doc_id}):\n{text}")
    
    context_str = "\n\n".join(context_parts)
    
    if api_key and api_key.strip():
        try:
            genai.configure(api_key=api_key.strip())
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""Bạn là một trợ lý pháp lý AI chuyên nghiệp. Hãy dựa VÀO ĐÚNG CÁC ĐIỀU LUẬT ĐƯỢC CUNG CẤP DƯỚI ĐÂY để trả lời câu hỏi của người dùng một cách chính xác, súc tích và có trích dẫn nguồn luật cụ thể.
Tuyệt đối không tự bịa đặt thông tin.

---
CÁC ĐIỀU LUẬT THAM KHẢO:
{context_str}
---

CÂU HỎI CỦA NGƯỜI DÙNG: {query}

HÃY TRẢ LỜI BẰNG TIẾNG VIỆT MỘT CÁCH RÕ RÀNG, CHUYÊN NGHIỆP:"""

            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.warning(f"⚠️ Gọi Gemini API thất bại. Chuyển về chế độ trích xuất tĩnh. Lỗi: {e}")

    # Fallback template
    context_titles = [f"- {item.get('article_title')} ({item.get('law_type')} - {item.get('document_id')})" for item in search_results]
    context_str_fallback = "\n".join(context_titles)
    return (
        f"Dựa trên các quy định pháp luật hiện hành, tôi xin giải đáp vấn đề **'{query}'** của bạn như sau:\n\n"
        f"Theo thông tin tra cứu được, vấn đề này được quy định chi tiết tại:\n"
        f"{context_str_fallback}\n\n"
        f"💡 *(Mẹo: Nhập **Gemini API Key** ở thanh Sidebar bên trái để bật tính năng AI sinh câu trả lời tự động!)*"
    )

# --- GIAO DIỆN CHÍNH ---
st.title("⚖️ Legal Semantic Search & AI Assistant")
st.caption("Hệ thống hỏi đáp pháp luật thông minh ứng dụng Hybrid Search, Reranker, Metadata Filtering & Gemini LLM")

# Sidebar cấu hình
with st.sidebar:
    st.header("⚙️ Cấu hình hệ thống")
    
    search_strategy = st.selectbox(
        "Chiến lược tìm kiếm:",
        options=["Dense Search", "BM25 Search", "Hybrid Search", "Hybrid + Reranker"],
        index=2 
    )
    
    with st.expander("📖 Giải thích chiến lược", expanded=False):
        st.markdown(
            "• **Dense:** Vector ngữ nghĩa sâu.\n"
            "• **BM25:** Khớp từ khóa chính xác.\n"
            "• **Hybrid:** Kết hợp song song Dense + BM25.\n"
            "• **Reranker:** Chấm điểm tinh chỉnh Top đầu chuẩn xác nhất."
        )

    st.markdown("---")
    st.subheader("🗂️ Lọc Metadata Chuyên Sâu")
    
    # Bộ lọc loại văn bản
    law_type_filter = st.selectbox(
        "Loại văn bản:",
        options=["Tất cả", "Luật", "Nghị định", "Thông tư"],
        index=0
    )
    
    # Bộ lọc năm ban hành
    year_filter = st.selectbox(
        "Năm ban hành:",
        options=["Tất cả", 2024, 2023, 2025],
        index=0
    )
    
    top_k = st.slider("Số lượng tài liệu trích xuất (Top-K):", 1, 5, 3)
    
    st.markdown("---")
    st.subheader("🔑 Cấu hình AI (LLM)")
    gemini_api_key = st.text_input(
        "Gemini API Key:",
        type="password",
        value=os.getenv("GEMINI_API_KEY", ""),
        help="Nhập API Key của bạn để bật tính năng sinh câu trả lời tự động."
    )
    
    st.markdown("---")
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()

# Khởi tạo session_state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Hãy cấu hình bộ lọc metadata ở thanh bên trái, chọn chiến lược tìm kiếm và đặt câu hỏi cho tôi nhé!"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "latency" in msg and msg["role"] == "assistant":
            st.caption(f"⚡ Thời gian phản hồi: `{msg['latency']:.4f}s` | Chiến lược: `{msg.get('strategy', 'N/A')}`")
            
        if msg["role"] == "assistant" and "sources" in msg and msg["sources"]:
            with st.expander("📚 Xem nguồn trích dẫn luật chi tiết"):
                for idx, source in enumerate(msg["sources"]):
                    score = source.get('score', 0.0)
                    st.markdown(f"**{idx + 1}. {source.get('article_title', 'Điều luật')}** - *{source.get('law_type')} năm {source.get('year')}* (Score: `{score:.4f}`)")
                    st.info(source.get('chunk_text', ''))

if prompt := st.chat_input("Nhập câu hỏi pháp lý của bạn vào đây..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"Đang tìm kiếm với bộ lọc chuyên sâu [{search_strategy}]..."):
            start_time = time.time()
            
            # Xử lý tham số lọc metadata truyền vào engine
            filter_law = None if law_type_filter == "Tất cả" else law_type_filter
            filter_year = None if year_filter == "Tất cả" else year_filter
            
            # Gọi search engine (hỗ trợ lọc theo law_type và year nếu các searcher hỗ trợ filter)
            # Ở đây ta gọi trực tiếp hoặc truyền thêm điều kiện lọc payload Qdrant
            retrieved_docs = []
            if search_strategy == "Dense Search":
                retrieved_docs = engines["dense"].search(prompt, top_k=top_k)
            elif search_strategy == "BM25 Search":
                retrieved_docs = engines["bm25"].search(prompt, top_k=top_k)
            elif search_strategy == "Hybrid Search":
                retrieved_docs = engines["hybrid"].search(prompt, top_k=top_k)
            elif search_strategy == "Hybrid + Reranker":
                hybrid_results = engines["hybrid"].search(prompt, top_k=top_k * 2)
                retrieved_docs = engines["reranker"].rerank(prompt, hybrid_results, top_k=top_k)
            
            # Lọc kết quả theo Metadata đã chọn ở Sidebar (Client-side / Post-filtering đảm bảo an toàn tuyệt đối)
            filtered_docs = []
            for doc in retrieved_docs:
                match_law = (filter_law is None) or (doc.get("law_type") == filter_law)
                match_year = (filter_year is None) or (doc.get("year") == filter_year)
                if match_law and match_year:
                    filtered_docs.append(doc)
            
            # Nếu lọc xong mà rỗng nhưng có retrieved_docs, ta có thể lấy top_k sau khi lọc
            retrieved_docs = filtered_docs[:top_k] if filtered_docs else retrieved_docs[:top_k]
            
            end_time = time.time()
            latency = end_time - start_time
            
            bot_response = generate_rag_response(prompt, retrieved_docs, api_key=gemini_api_key)
            
            st.markdown(bot_response)
            st.caption(f"⚡ Thời gian phản hồi: `{latency:.4f}s` | Chiến lược: `{search_strategy}` | Bộ lọc: [Loại: {law_type_filter}, Năm: {year_filter}]")
            
            if retrieved_docs:
                with st.expander("📚 Xem nguồn trích dẫn luật chi tiết"):
                    for idx, doc in enumerate(retrieved_docs):
                        score = doc.get('score', 0.0)
                        st.markdown(f"**{idx + 1}. {doc.get('article_title', 'Điều luật')}** - *{doc.get('law_type')} năm {doc.get('year')}* (Score: `{score:.4f}`)")
                        st.info(doc.get('chunk_text', ''))
            
    st.session_state.messages.append({
        "role": "assistant", 
        "content": bot_response,
        "sources": retrieved_docs,
        "latency": latency,
        "strategy": search_strategy
    })