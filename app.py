import random
import streamlit as st
import asyncio
import edge_tts
from deep_translator import GoogleTranslator
import tempfile
import os

# 1. CẤU HÌNH TRANG
st.set_page_config(
    page_title="AI Translate",
    page_icon="🌐",
    layout="wide"
)

# 2. XÁC THỰC MẬT KHẨU TỪ SECRETS
def check_password():
    """Kiểm tra mật khẩu truy cập ứng dụng"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.subheader("🔒 Yêu cầu Mật khẩu Truy cập")
        user_input = st.text_input("Nhập mật khẩu để tiếp tục:", type="password")
        
        if st.button("Đăng nhập", type="primary"):
            correct_password = st.secrets.get("APP_PASSWORD", "123456")
            if user_input == correct_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Mật khẩu không đúng. Vui lòng thử lại!")
        return False
    return True

if not check_password():
    st.stop()

# 3. DANH SÁCH GIỌNG ĐỌC
VOICE_OPTIONS = {
    "Nữ - Miền Bắc (Hoài Mỹ - Báo cáo / Thuyết trình)": "vi-VN-HoaiMyNeural",
    "Nam - Miền Bắc (Nam Minh - Trang trọng / Giảng dạy)": "vi-VN-NamMinhNeural",
}

# 4. HÀM TẠO ÂM THANH BẰNG EDGE-TTS (HỖ TRỢ ĐIỀU CHỈNH TỐC ĐỘ / TÔNG GIỌNG)
async def generate_edge_audio_async(text, voice_code, rate_str, pitch_str, output_path):
    communicate = edge_tts.Communicate(text, voice_code, rate=rate_str, pitch=pitch_str)
    await communicate.save(output_path)

def create_tts_audio(text, voice_code, speed_percent, pitch_hz):
    rate_str = f"{'+' if speed_percent >= 0 else ''}{speed_percent}%"
    pitch_str = f"{'+' if pitch_hz >= 0 else ''}{pitch_hz}Hz"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    
    asyncio.run(generate_edge_audio_async(text, voice_code, rate_str, pitch_str, tmp_path))
    
    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()
        
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
        
    return audio_bytes

# --- GIAO DIỆN ỨNG DỤNG ---
st.title("AI Translate")

tab1, tab2 = st.tabs(["📝 Chuyển Văn bản thành Giọng đọc (TTS)", "🌐 Dịch Hội nghị Trực tiếp"])

# ==============================================================================
# TAB 1: TEXT TO SPEECH
# ==============================================================================
with tab1:
    st.subheader("Text to speech")
    
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        selected_voice_label = st.selectbox(
            "1. Chọn giọng đọc AI:",
            list(VOICE_OPTIONS.keys()),
            index=0
        )
        voice_code = VOICE_OPTIONS[selected_voice_label]
        
        speech_rate = st.slider(
            "2. Điều chỉnh Tốc độ đọc (%):",
            min_value=-40,
            max_value=40,
            value=-5,
            step=5,
            help="Đọc báo cáo khoa học nên để khoảng -5% đến 0% để âm thanh tròn chữ, rõ ràng."
        )

        pitch_val = st.slider(
            "3. Điều chỉnh Cao độ (Pitch Hz):",
            min_value=-20,
            max_value=20,
            value=0,
            step=2,
            help="Tăng/giảm độ trầm ấm của giọng đọc."
        )

        text_input = st.text_area(
            "4. Nhập nội dung văn bản / bài báo cáo:",
            height=200,
            placeholder="Nhập văn bản cần chuyển thành giọng đọc..."
        )
        
        btn_generate = st.button("▶ Đọc & Tạo file MP3", type="primary", use_container_width=True)

    with col_right:
        st.markdown("### Kết quả âm thanh")
        if btn_generate:
            if not text_input.strip():
                st.warning("⚠️ Vui lòng nhập nội dung văn bản!")
            else:
                with st.spinner("⏳ Đang khởi tạo giọng đọc AI..."):
                    try:
                        audio_data = create_tts_audio(text_input, voice_code, speech_rate, pitch_val)
                        st.success("✅ Tạo âm thanh thành công!")
                        
                        st.audio(audio_data, format="audio/mp3")
                        
                        st.download_button(
                            label="📥 Tải file MP3 về máy",
                            data=audio_data,
                            file_name="bao_cao_ai_translate.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"❌ Có lỗi xảy ra: {e}")

# ==============================================================================
# TAB 2: DỊCH HỘI NGHỊ TRỰC TIẾP
# ==============================================================================
with tab2:
    st.subheader("Phiên dịch Hội nghị Trực tiếp")
    
    col_lang1, col_lang2 = st.columns(2)
    with col_lang1:
        src_lang = st.selectbox("Ngôn ngữ gốc:", ["Tiếng Việt", "Tiếng Anh"], index=0)
    with col_lang2:
        tgt_lang = st.selectbox("Ngôn ngữ đích:", ["Tiếng Anh", "Tiếng Việt"], index=0)
        
    speech_text = st.text_area("Nội dung phát biểu:", height=120, placeholder="Nhập văn bản cần dịch...")
    btn_translate = st.button("🔄 Dịch ngay", type="primary", use_container_width=True)
    
    if btn_translate and speech_text.strip():
        with st.spinner("⏳ Đang xử lý dịch thuật..."):
            try:
                lang_map = {"Tiếng Việt": "vi", "Tiếng Anh": "en"}
                translated_text = GoogleTranslator(
                    source=lang_map[src_lang], 
                    target=lang_map[tgt_lang]
                ).translate(speech_text)
                
                st.markdown(f"**Bản dịch ({tgt_lang}):**")
                st.success(translated_text)
            except Exception as e:
                st.error(f"❌ Lỗi dịch thuật: {e}")
