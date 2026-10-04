import random
import streamlit as st
import asyncio
import edge_tts
import tempfile
import os
import io
import time
import re
import base64

# 1. CẤU HÌNH TRANG
st.set_page_config(
    page_title="Hệ thống Dịch thuật & TTS",
    page_icon="🎙️",
    layout="wide"
)

# 2. XÁC THỰC MẬT KHẨU TỪ SECRETS
def check_password():
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

# 3. QUẢN LÝ LỊCH SỬ DỊCH HỘI NGHỊ (DẠNG THEO DÕI NGƯỜI TRÌNH BÀY)
if "conference_logs" not in st.session_state:
    st.session_state["conference_logs"] = []

# 4. DANH SÁCH GIỌNG ĐỌC AI
VOICE_OPTIONS = {
    "🇺🇸 Nam - Anh-Mỹ (Guy)": "en-US-GuyNeural",
    "🇺🇸 Nữ - Anh-Mỹ (Jenny)": "en-US-JennyNeural",
    "🇬🇧 Nữ - Anh-Anh (Sonia)": "en-GB-SoniaNeural",
    "🇻🇳 Nam - Tiếng Việt (Nam Minh)": "vi-VN-NamMinhNeural",
    "🇻🇳 Nữ - Tiếng Việt (Hoài Mỹ)": "vi-VN-HoaiMyNeural"
}

# 5. XỬ LÝ ÂM THANH NEURAL TTS
async def generate_edge_audio_async(text, voice_code, rate_str, pitch_str, output_path):
    communicate = edge_tts.Communicate(text, voice_code, rate=rate_str, pitch=pitch_str)
    await communicate.save(output_path)

def create_tts_audio(text, voice_code, speed_percent=0, pitch_hz=0):
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

# 6. HÀM DỊCH CHUẨN MÃ NGÔN NGỮ (SỬA LỖI TRONG ẢNH)
def translate_robust(text, src_code, tgt_code):
    # Rút gọn mã ngôn ngữ đầu vào về dạng gốc (vi, en)
    src_base = "vi" if "vi" in src_code.lower() else "en"
    tgt_base = "en" if "en" in tgt_code.lower() else "vi"

    # Ưu tiên 1: DeepTranslator Google
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source=src_base, target=tgt_base).translate(text)
    except Exception:
        pass

    # Ưu tiên 2: MyMemory với mã đầy đủ (vi-VN, en-US) để không bị lỗi No support
    try:
        from deep_translator import MyMemoryTranslator
        src_mm = "vi-VN" if src_base == "vi" else "en-US"
        tgt_mm = "en-US" if tgt_base == "en" else "vi-VN"
        return MyMemoryTranslator(source=src_mm, target=tgt_mm).translate(text)
    except Exception as e:
        raise Exception(f"Lỗi kết nối máy chủ dịch: {e}")

# 7. PHÁT ÂM THANH DỊCH TỰ ĐỘNG KHÔNG CẦN TRÌNH PHÁT / KHÔNG CẦN TẢI FILE
def play_audio_autoplay(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay style="display:none;">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    st.markdown(md, unsafe_allow_html=True)


# --- GIAO DIỆN CHÍNH ---
st.title("🎙️ Hệ Thống Phiên Dịch & Chuyển Văn Bản")

tab1, tab2 = st.tabs(["🏛️ Dịch Hội Nghị Trực Tiếp", "📝 Chuyển Văn Bản Thành Giọng Nói (TTS)"])

# TAB 1: DỊCH HỘI NGHỊ (THEO DÕI NGƯỜI TRÌNH BÀY & SONG SONG 2 KHUNG)
with tab1:
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        direction = st.selectbox("Hướng dịch:", ["Việt ➔ Anh", "Anh ➔ Việt"])
    with col_opt2:
        voice_choice = st.selectbox("Giọng đọc phiên dịch:", list(VOICE_OPTIONS.keys()))

    # Thu âm phát biểu
    try:
        import speech_recognition as sr
        from streamlit_mic_recorder import mic_recorder
        from pydub import AudioSegment

        st.write("---")
        recorded = mic_recorder(
            start_prompt="🔴 Bắt đầu nói (Diễn giả)",
            stop_prompt="⏹️ Hoàn tất lượt nói",
            key="conference_mic"
        )

        if recorded and 'bytes' in recorded:
            audio_bytes = recorded['bytes']
            if len(audio_bytes) > 5000:
                with st.spinner("Đang xử lý dịch thuật..."):
                    wav_path = None
                    try:
                        audio_stream = io.BytesIO(audio_bytes)
                        segment = AudioSegment.from_file(audio_stream)
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                            segment.export(tmp_wav.name, format="wav")
                            wav_path = tmp_wav.name

                        rec = sr.Recognizer()
                        with sr.AudioFile(wav_path) as source:
                            audio_data = rec.record(source)

                        src_lang = "vi-VN" if direction == "Việt ➔ Anh" else "en-US"
                        tgt_lang = "en-US" if direction == "Việt ➔ Anh" else "vi-VN"

                        # Nhận diện & dịch
                        original_text = rec.recognize_google(audio_data, language=src_lang)
                        translated_text = translate_robust(original_text, src_lang, tgt_lang)

                        # Thêm vào nhật ký trình bày
                        st.session_state["conference_logs"].append({
                            "time": time.strftime("%H:%M:%S"),
                            "original": original_text,
                            "translated": translated_text
                        })

                        # Tự động phát âm thanh bản dịch ngầm (không cần tải file)
                        translated_audio = create_tts_audio(translated_text, VOICE_OPTIONS[voice_choice])
                        play_audio_autoplay(translated_audio)

                    except Exception as e:
                        st.error(f"Lỗi xử lý: {e}")
                    finally:
                        if wav_path and os.path.exists(wav_path):
                            os.remove(wav_path)
    except ImportError:
        st.error("Chưa cài đặt streamlit-mic-recorder hoặc speech_recognition.")

    st.write("---")
    st.subheader("📺 Khung Khớp Ngôn Ngữ Song Song (Live Stream)")

    # 2 KHUNG NGÔN NGỮ SONG SONG THEO DÕI DIỄN GIẢ
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### 🇻🇳 Ngôn ngữ nói (Tiếng Việt)")
        for item in reversed(st.session_state["conference_logs"]):
            st.info(f"**[{item['time']}]** {item['original']}")

    with col_right:
        st.markdown("### 🇺🇸 Ngôn ngữ dịch (Tiếng Anh)")
        for item in reversed(st.session_state["conference_logs"]):
            st.success(f"**[{item['time']}]** {item['translated']}")

# TAB 2: CHỨC NĂNG TTS BAN ĐẦU CỦA THẦY (GIỮ NGUYÊN HOÀN TOÀN)
with tab2:
    st.subheader("Text to speech")
    text_input = st.text_area("Nhập văn bản cần đọc:", height=150)
    if st.button("Đọc"):
        if text_input:
            audio_data = create_tts_audio(text_input, "en-US-GuyNeural")
            st.audio(audio_data, format="audio/mp3")
