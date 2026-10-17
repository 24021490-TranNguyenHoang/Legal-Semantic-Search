def main():
    import streamlit as st
    import sys
    from pathlib import Path

    # Đảm bảo import được module từ thư mục gốc
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))

    from src.search.legal_retriever import LegalRetriever, VEHICLE_PATTERNS

    st.set_page_config(
        page_title="Tra cứu Pháp luật Giao thông VN",
        page_icon="⚖️",
        layout="wide"
    )

    # Tải tài nguyên vào cache để giao diện phản hồi nhanh
    @st.cache_resource(show_spinner="Đang khởi tạo mô hình AI và nạp cơ sở tri thức pháp luật...")
    def load_retriever():
        return LegalRetriever()

    retriever = load_retriever()

    # --- GIAO DIỆN CHÍNH ---
    st.title("⚖️ Hệ thống Tra cứu Ngữ nghĩa Pháp luật Giao thông Đường bộ")
    st.markdown("""
Hệ thống ứng dụng kiến trúc **Semantic Hybrid Search (Vector AI + BM25)** kết hợp **Bộ phân tích tri thức pháp lý (Legal Domain Engine)**
giúp tự động nối kết ngôn ngữ đời thường (tiếng lóng, từ thông dụng) với các quy định pháp luật chính xác mới nhất (hiệu lực từ 2025).
""")

    # Gợi ý tìm kiếm nhanh
    st.markdown("**💡 Gợi ý câu hỏi phổ biến:**")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    suggested_query = None
    if col_s1.button("🚦 Vượt đèn đỏ bị phạt như nào"):
        suggested_query = "vượt đèn đỏ bị phạt như nào"
    if col_s2.button("🍺 Nồng độ cồn xe máy phạt bao nhiêu"):
        suggested_query = "uống rượu lái xe máy bị phạt bao nhiêu tiền"
    if col_s3.button("🚗 Chạy quá tốc độ ô tô bị phạt mấy tiền"):
        suggested_query = "chạy quá tốc độ ô tô bị phạt bao nhiêu"
    if col_s4.button("🟡 Tín hiệu đèn giao thông có mấy màu"):
        suggested_query = "tín hiệu đèn giao thông có mấy màu và ý nghĩa"

    # Ô nhập truy vấn
    default_val = suggested_query if suggested_query else ""
    query = st.text_input(
        "Nhập câu hỏi tra cứu hoặc từ khóa hành vi vi phạm:",
        value=default_val,
        placeholder="Ví dụ: vượt đèn đỏ bị phạt như nào, không đội mũ bảo hiểm xe máy phạt bao nhiêu..."
    )

    col_ctrl1, col_ctrl2 = st.columns([2, 1])

    with col_ctrl1:
        vehicle_filter_options = {
            "Tất cả phương tiện": None,
            "🏍️ Xe mô tô, xe gắn máy": "xe_may",
            "🚗 Xe ô tô": "oto",
            "🚲 Xe đạp, xe thô sơ": "xe_dap",
            "🚜 Xe máy chuyên dùng": "chuyen_dung",
            "🚶 Người đi bộ": "di_bo"
        }
        selected_vehicle_label = st.selectbox(
            "Bộ lọc phương tiện (Tùy chọn):",
            options=list(vehicle_filter_options.keys()),
            index=0
        )
        selected_vehicle_override = vehicle_filter_options[selected_vehicle_label]

    with col_ctrl2:
        top_k = st.slider("Số lượng kết quả (Top K):", min_value=3, max_value=10, value=3)

    search_clicked = st.button("🔍 Tra cứu quy định", type="primary", use_container_width=True)

    if search_clicked or query:
        if query.strip():
            with st.spinner("Đang phân tích ngữ nghĩa và truy xuất điều luật..."):
                analysis, results = retriever.search(
                    query=query.strip(),
                    top_k=top_k,
                    vehicle_override=selected_vehicle_override
                )

            # Hiển thị kết quả phân tích ngữ nghĩa (Semantic Insight)
            st.markdown("---")
            with st.container():
                col_in1, col_in2 = st.columns([1, 1])
                with col_in1:
                    violation_text = ", ".join(analysis["matched_violations"]) if analysis["matched_violations"] else "Quy tắc / Định nghĩa chung"
                    st.info(f"📌 **Hành vi nhận diện:** {violation_text}")

                with col_in2:
                    intent_text = "Tra cứu chế tài xử phạt vi phạm hành chính (Nghị định 168/2024/NĐ-CP)" if analysis["is_penalty"] else "Tra cứu quy định, nguyên tắc giao thông"
                    st.success(f"🎯 **Ý định tra cứu:** {intent_text}")

                if analysis["matched_violations"] and "đèn tín hiệu" in violation_text.lower():
                    st.caption(
                        "💡 *Lưu ý pháp lý: Trong văn bản pháp luật giao thông, hành vi 'vượt đèn đỏ' được quy định chuẩn hóa dưới tên gọi "
                        "**'Không chấp hành hiệu lệnh của đèn tín hiệu giao thông'** (Nghị định 168/2024/NĐ-CP). Hệ thống đã tự động chuyển đổi ngữ nghĩa để truy xuất đúng khung xử phạt.*"
                    )

            st.subheader("📋 Kết quả tra cứu quy định pháp luật:")
            if not results:
                st.warning("Không tìm thấy kết quả phù hợp với truy vấn. Vui lòng thử diễn đạt câu hỏi khác.")
            else:
                for rank, item in enumerate(results, start=1):
                    citation = item.get("citation_path", "")
                    fine = item.get("fine_amount")
                    fine_badge = f"💰 **Mức phạt:** `{fine}` | " if fine else ""
                    vehicle_badge = f"**Đối tượng:** {item.get('vehicle_type', '')}"

                    expander_title = f"Top {rank} - {citation}"
                    if fine:
                        expander_title += f" [Phạt: {fine}]"
                    elif item.get("vehicle_type"):
                        expander_title += f" [{item.get('vehicle_type')}]"

                    with st.expander(expander_title, expanded=(rank == 1)):
                        st.markdown(f"**Văn bản áp dụng:** {item.get('law_title')} ({item.get('law_id')})")

                        # Thẻ thông tin nhanh
                        cols_info = st.columns(3)
                        cols_info[0].markdown(f"🏷️ {vehicle_badge}")
                        if fine:
                            cols_info[1].markdown(f"💵 **Khung tiền phạt:** `{fine}`")
                        cols_info[2].markdown(f"📊 **Độ tương đồng (Score):** `{item.get('score', 0):.4f}`")

                        st.markdown("**Nội dung điều khoản chi tiết:**")
                        # Hiển thị nội dung đã được highlight điểm vi phạm
                        highlighted_html = item.get("highlighted_text", "").replace("\n", "<br>")
                        st.markdown(
                            f"""
                        <div style="background-color: #f8f9fa; color: #212529; padding: 15px; border-radius: 8px; border-left: 5px solid #007bff; line-height: 1.6; font-size: 15px;">
                            {highlighted_html}
                        </div>
                        """,
                            unsafe_allow_html=True
                        )
        else:
            st.warning("Vui lòng nhập câu hỏi hoặc từ khóa trước khi tra cứu!")


if __name__ == "__main__":
    main()
