import streamlit as st
import asyncio
import edge_tts
from deep_translator import GoogleTranslator
import tempfile
import os

st.set_page_config(
    page_title="Hệ thống Giọng đọc AI & Dịch hội nghị",
    page_icon="🎙️",
    layout="wide"
)

# 1. Danh sách chi tiết các giọng đọc AI chất lượng cao (Phân loại theo phong cách & vùng miền)
VOICE_OPTIONS = {
    "Tiếng Việt": {
        "Nữ - Hoài Mỹ (Miền Bắc - Chuẩn Báo cáo Khoa học / Thuyết trình)": "vi-VN-HoaiMyNeural",
        "Nam - Nam Minh (Miền Bắc - Trầm ấm, Diễn thuyết / Giảng dạy)": "vi-VN-NamMinhNeural",
        "Nữ - Hoài Mỹ (Phong cách Đọc tin tức / Hội thảo)": "vi-VN-HoaiMyNeural",
        "Nam - Nam Minh (Phong cách Đọc báo / Thuyết minh)": "vi-VN-NamMinhNeural"
    },
    "Tiếng Anh (Mỹ)": {
        "Nữ - Jenny (Chuẩn Báo cáo / Thuyết trình Khoa học)": "en-US-JennyNeural",
        "Nam - Guy (Chuyên nghiệp / Hội thảo Chuyên ngành)": "en-US-GuyNeural",
        "Nữ - Aria (Trang trọng / Thuyết minh)": "en-US-AriaNeural",
        "Nam - Christopher (Trầm, Thuyết trình Dự án)": "en-US-ChristopherNeural"
    },
    "Tiếng Anh (Anh)": {
        "Nữ - Sonia (Giọng Академик / Học thuật chuẩn)": "en-GB-SoniaNeural",
        "Nam - Ryan (Thuyết trình / Báo cáo)": "en-GB-RyanNeural"
    },
    "Tiếng Nhật": {
        "Nữ - Nanami (Chuẩn Thuyết trình)": "ja-JP-NanamiNeural",
        "Nam - Keita (Chuẩn Báo cáo)": "ja-JP-KeitaNeural"
    },
    "Tiếng Hàn": {
        "Nữ - Sun-Hi (Thuyết trình)": "ko-KR-SunHiNeural",
        "Nam - InJoon (Báo cáo)": "ko-KR-InJoonNeural"
    },
    "Tiếng Trung": {
        "Nữ - Xiaoxiao (Chuẩn Trang trọng)": "zh-CN-XiaoxiaoNeural",
        "Nam - Yunjian (Báo cáo Khoa học)": "zh-CN-YunjianNeural"
    },
    "Tiếng Pháp": {
        "Nữ - Denise (Thuyết trình)": "fr-FR-DeniseNeural",
        "Nam - Henri (Hội thảo)": "fr-FR-HenriNeural"
    }
}

LANG_CODES = {
    "Tiếng Việt": "vi",
    "Tiếng Anh (Mỹ)": "en",
    "Tiếng Anh (Anh)": "en",
    "Tiếng Nhật": "ja",
    "Tiếng Hàn": "ko",
    "Tiếng Trung": "zh-CN",
    "Tiếng Pháp": "fr"
}

# 2. Hàm tạo âm thanh bằng Edge-TTS có hỗ trợ tùy chỉnh tốc độ (rate)
async def generate_audio_file(text, voice, rate_str, output_path):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    await communicate.save(output_path)

def create_tts_audio(text, voice, rate_percent):
    # Quy đổi số % thành định dạng chuỗi của Edge-TTS (ví dụ: "+0%", "+20%", "-10%")
    rate_str = f"{'+' if rate_percent >= 0 else ''}{rate_percent}%"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    
    asyncio.run(generate_audio_file(text, voice, rate_str, tmp_path))
    
    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()
        
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
        
    return audio_bytes

# --- GIAO DIỆN CHÍNH ---
st.title("🎙️ Hệ thống Giọng đọc AI Chuyên nghiệp & Dịch hội nghị")

tab1, tab2 = st.tabs(["📝 Chuyển Văn bản thành Giọng đọc (TTS)", "🌐 Dịch Hội nghị Trực tiếp"])

# ==============================================================================
# TAB 1: TEXT-TO-SPEECH (CÓ CHỈNH TỐC ĐỘ VÀ GIỌNG BÁO CÁO)
# ==============================================================================
with tab1:
    st.subheader("Chuyển đổi văn bản thành giọng đọc AI tự nhiên (Khoa học / Thuyết trình)")
    
    col_input, col_output = st.columns([1, 1], gap="large")
    
    with col_input:
        selected_lang = st.selectbox(
            "1. Chọn Ngôn ngữ:",
            list(VOICE_OPTIONS.keys()),
            index=0,
            key="tts_lang"
        )
        
        voices_in_lang = VOICE_OPTIONS[selected_lang]
        selected_voice_label = st.selectbox(
            "2. Chọn Giọng đọc & Phong cách:",
            list(voices_in_lang.keys()),
            index=0,
            key="tts_voice"
        )
        selected_voice_code = voices_in_lang[selected_voice_label]
        
        # Thanh điều chỉnh tốc độ đọc
        speech_rate = st.slider(
            "3. Điều chỉnh Tốc độ đọc (%):",
            min_value=-50,
            max_value=50,
            value=0,
            step=5,
            help="Báo cáo khoa học nên để khoảng -5% đến 0% để đọc rõ ràng, trang trọng.",
            key="tts_rate"
        )
        
        text_input = st.text_area(
            "4. Nhập nội dung bài báo cáo / thuyết trình / văn bản:",
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
                with st.spinner("⏳ Đang khởi tạo giọng đọc AI chuyên nghiệp..."):
                    try:
                        audio_data = create_tts_audio(text_input, selected_voice_code, speech_rate)
                        st.success("✅ Tạo file âm thanh thành công!")
                        
                        st.audio(audio_data, format="audio/mp3")
                        
                        st.download_button(
                            label="📥 Tải file MP3 về máy",
                            data=audio_data,
                            file_name=f"bao_cao_ai_{selected_voice_code}.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"❌ Có lỗi xảy ra trong quá trình tạo âm thanh: {e}")

# ==============================================================================
# TAB 2: DỊCH HỘI NGHỊ TRỰC TIẾP
# ==============================================================================
with tab2:
    st.subheader("Phiên dịch Hội nghị Trực tiếp & Tự động đọc bản dịch")
    
    col_lang1, col_lang2 = st.columns(2)
    with col_lang1:
        speaker_lang = st.selectbox("Ngôn ngữ Diễn giả (Người nói):", list(VOICE_OPTIONS.keys()), index=0, key="spk_lang")
        spk_voice_label = st.selectbox("Giọng đọc diễn giả:", list(VOICE_OPTIONS[speaker_lang].keys()), index=0, key="spk_voice")
        spk_voice_code = VOICE_OPTIONS[speaker_lang][spk_voice_label]

    with col_lang2:
        target_lang = st.selectbox("Ngôn ngữ Thính giả (Cần dịch ra):", list(VOICE_OPTIONS.keys()), index=1, key="tgt_lang")
        tgt_voice_label = st.selectbox("Giọng đọc bản dịch:", list(VOICE_OPTIONS[target_lang].keys()), index=0, key="tgt_voice")
        tgt_voice_code = VOICE_OPTIONS[target_lang][tgt_voice_label]

    conf_speech_rate = st.slider(
        "Tốc độ đọc bản dịch (%):",
        min_value=-30,
        max_value=30,
        value=0,
        step=5,
        key="conf_rate"
    )

    st.markdown("---")
    
    speech_text = st.text_area(
        "Nội dung phát biểu trực tiếp của diễn giả:",
        height=120,
        placeholder="Nhập hoặc dán nội dung phát biểu của diễn giả...",
        key="conf_text"
    )
    
    btn_translate = st.button("🔄 Dịch ngay & Phát âm thanh", type="primary", use_container_width=True)
    
    if btn_translate:
        if not speech_text.strip():
            st.warning("⚠️ Vui lòng nhập nội dung phát biểu để dịch!")
        else:
            with st.spinner("⏳ Đang dịch thuật và khởi tạo âm thanh hội nghị..."):
                try:
                    src_code = LANG_CODES[speaker_lang]
                    tgt_code = LANG_CODES[target_lang]
                    
                    translated_text = GoogleTranslator(source=src_code, target=tgt_code).translate(speech_text)
                    trans_audio_data = create_tts_audio(translated_text, tgt_voice_code, conf_speech_rate)
                    
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
