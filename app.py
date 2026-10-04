import streamlit as st
import asyncio
import edge_tts
from deep_translator import GoogleTranslator
import tempfile
import os

# 1. Cấu hình trang web Streamlit
st.set_page_config(
    page_title="Hệ thống Giọng đọc AI & Dịch hội nghị",
    page_icon="🎙️",
    layout="wide"
)

# 2. Danh sách ngôn ngữ và mã giọng đọc AI (Edge-TTS)
LANGUAGES = {
    "Tiếng Việt": {"code": "vi", "voice": "vi-VN-HoaiMyNeural"},
    "Tiếng Anh (Mỹ)": {"code": "en", "voice": "en-US-JennyNeural"},
    "Tiếng Anh (Anh)": {"code": "en", "voice": "en-GB-SoniaNeural"},
    "Tiếng Nhật": {"code": "ja", "voice": "ja-JP-NanamiNeural"},
    "Tiếng Hàn": {"code": "ko", "voice": "ko-KR-SunHiNeural"},
    "Tiếng Trung (Phổ thông)": {"code": "zh-CN", "voice": "zh-CN-XiaoxiaoNeural"},
    "Tiếng Pháp": {"code": "fr", "voice": "fr-FR-DeniseNeural"},
    "Tiếng Đức": {"code": "de", "voice": "de-DE-KatjaNeural"},
    "Tiếng Tây Ban Nha": {"code": "es", "voice": "es-ES-ElviraNeural"},
    "Tiếng Thái": {"code": "th", "voice": "th-TH-NiwatNeural"}
}

# 3. Hàm tạo âm thanh bằng Edge-TTS (bất đồng bộ)
async def generate_audio_file(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def create_tts_audio(text, voice):
    """Tạo file âm thanh tạm thời và trả về byte dữ liệu"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    
    # Chạy hàm bất đồng bộ
    asyncio.run(generate_audio_file(text, voice, tmp_path))
    
    # Đọc dữ liệu binary của file MP3
    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()
        
    # Xóa file tạm sau khi đã đọc xong
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
        
    return audio_bytes

# --- GIAO DIỆN CHÍNH ---
st.title("🎙️ Hệ thống Giọng đọc AI & Dịch hội nghị Trực tiếp")

# Tạo 2 tab chính
tab1, tab2 = st.tabs(["📝 Chuyển Văn bản thành Giọng đọc (TTS)", "🌐 Dịch Hội nghị Trực tiếp"])

# ==============================================================================
# TAB 1: TEXT-TO-SPEECH (TTS) & TẢI MP3
# ==============================================================================
with tab1:
    st.subheader("Chuyển đổi văn bản thành giọng nói & Tải về MP3")
    
    col_input, col_output = st.columns([1, 1], gap="large")
    
    with col_input:
        selected_lang_name = st.selectbox(
            "1. Chọn ngôn ngữ gốc:",
            list(LANGUAGES.keys()),
            index=0,
            key="tts_lang"
        )
        selected_voice = LANGUAGES[selected_lang_name]["voice"]
        
        text_input = st.text_area(
            "2. Nhập văn bản cần đọc:",
            height=200,
            placeholder="Nhập nội dung văn bản vào đây...",
            key="tts_text"
        )
        
        btn_generate = st.button("▶ Đọc & Tạo file MP3", type="primary", use_container_width=True)

    with col_output:
        st.markdown("### Kết quả âm thanh")
        if btn_generate:
            if not text_input.strip():
                st.warning("⚠️ Vui lòng nhập nội dung văn bản trước khi tạo âm thanh!")
            else:
                with st.spinner("⏳ Đang tạo giọng đọc AI tự nhiên..."):
                    try:
                        audio_data = create_tts_audio(text_input, selected_voice)
                        st.success("✅ Tạo file âm thanh thành công!")
                        
                        # Trình phát nhạc
                        st.audio(audio_data, format="audio/mp3")
                        
                        # Nút tải MP3 về máy
                        st.download_button(
                            label="📥 Tải file MP3 về máy",
                            data=audio_data,
                            file_name=f"giong_doc_{LANGUAGES[selected_lang_name]['code']}.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"❌ Có lỗi xảy ra trong quá trình tạo âm thanh: {e}")

# ==============================================================================
# TAB 2: DỊCH HỘI NGHỊ TRỰC TIẾP
# ==============================================================================
with tab2:
    st.subheader("Phiên dịch Hội nghị Trực tiếp & Phát âm thanh")
    
    col_lang1, col_lang2 = st.columns(2)
    with col_lang1:
        speaker_lang = st.selectbox("Ngôn ngữ Diễn giả (Người nói):", list(LANGUAGES.keys()), index=0, key="spk_lang")
    with col_lang2:
        target_lang = st.selectbox("Ngôn ngữ Thính giả (Cần dịch ra):", list(LANGUAGES.keys()), index=1, key="tgt_lang")
        
    st.markdown("---")
    
    speech_text = st.text_area(
        "Nội dung phát biểu trực tiếp của diễn giả:",
        height=120,
        placeholder="Nhập hoặc dán câu nói/bài phát biểu của diễn giả vào đây...",
        key="conf_text"
    )
    
    btn_translate = st.button("🔄 Dịch ngay & Phát âm thanh", type="primary", use_container_width=True)
    
    if btn_translate:
        if not speech_text.strip():
            st.warning("⚠️ Vui lòng nhập nội dung phát biểu để dịch!")
        else:
            with st.spinner("⏳ Đang dịch thuật và khởi tạo âm thanh hội nghị..."):
                try:
                    src_code = LANGUAGES[speaker_lang]["code"]
                    tgt_code = LANGUAGES[target_lang]["code"]
                    tgt_voice = LANGUAGES[target_lang]["voice"]
                    
                    # Dịch văn bản
                    translated_text = GoogleTranslator(source=src_code, target=tgt_code).translate(speech_text)
                    
                    # Tạo âm thanh bài dịch
                    trans_audio_data = create_tts_audio(translated_text, tgt_voice)
                    
                    # Hiển thị song song hai ngôn ngữ
                    col_orig, col_trans = st.columns(2)
                    with col_orig:
                        st.markdown(f"**🗣️ Văn bản gốc ({speaker_lang}):**")
                        st.info(speech_text)
                        
                    with col_trans:
                        st.markdown(f"**🎧 Bản dịch ({target_lang}):**")
                        st.success(translated_text)
                        
                    st.markdown("---")
                    st.markdown("### 🔊 Phát âm thanh bản dịch")
                    st.audio(trans_audio_data, format="audio/mp3", autoplay=True)
                    
                    st.download_button(
                        label="📥 Tải file MP3 bản dịch",
                        data=trans_audio_data,
                        file_name=f"ban_dich_{tgt_code}.mp3",
                        mime="audio/mp3"
                    )
                except Exception as e:
                    st.error(f"❌ Lỗi dịch thuật hoặc tạo âm thanh: {e}")
