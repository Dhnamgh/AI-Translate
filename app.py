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
import streamlit.components.v1 as components

# 1. CẤU HÌNH TRANG
st.set_page_config(
    page_title="AI Conference Interpreter",
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

# 3. QUẢN LÝ BỘ NHỚ HỘI NGHỊ (TRANSCRIPT HISTORY)
if "transcript_history" not in st.session_state:
    st.session_state["transcript_history"] = []

# 4. DANH SÁCH GIỌNG ĐỌC AI (NEURAL)
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

# 6. HÀM DỊCH CHUẨN MÃ NGÔN NGỮ (SỬA LỖI MYMEMORY / GOOGLE)
def translate_robust(text, src_code, tgt_code):
    # Chuẩn hóa mã ngôn ngữ phù hợp với thư viện dịch
    src_clean = "vi" if "vi" in src_code.lower() else "en"
    tgt_clean = "en" if "en" in tgt_code.lower() else "vi"

    # Cách 1: Sử dụng DeepTranslator Google
    try:
        from deep_translator import GoogleTranslator
        chunks = re.split(r'(\.|\,|\n)', text)
        translated_chunks = []
        current_chunk = ""
        for part in chunks:
            if len(current_chunk) + len(part) < 200:
                current_chunk += part
            else:
                if current_chunk.strip():
                    res = GoogleTranslator(source=src_clean, target=tgt_clean).translate(current_chunk)
                    translated_chunks.append(res)
                    time.sleep(0.1)
                current_chunk = part
        if current_chunk.strip():
            res = GoogleTranslator(source=src_clean, target=tgt_clean).translate(current_chunk)
            translated_chunks.append(res)
        return " ".join(translated_chunks)
    except Exception:
        pass

    # Cách 2: Dự phòng MyMemory với mã ngôn ngữ đầy đủ
    try:
        from deep_translator import MyMemoryTranslator
        src_mm = "vi-VN" if src_clean == "vi" else "en-US"
        tgt_mm = "en-US" if tgt_clean == "en" else "vi-VN"
        return MyMemoryTranslator(source=src_mm, target=tgt_mm).translate(text)
    except Exception as e:
        raise Exception(f"Lỗi kết nối máy chủ dịch: {e}")

def play_audio_hidden(audio_bytes):
    """Phát tự động âm thanh bản dịch ngầm mà không hiện trình phát hay nút tải"""
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay style="display:none;">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    st.markdown(md, unsafe_allow_html=True)

# --- GIAO DIỆN HỘI NGHỊ SONGBONG TRỰC TIẾP ---
st.title("🎙️ Hệ Thống Phiên Dịch Hội Nghị Trực Tiếp")

tab1, tab2 = st.tabs(["🏛️ Cabin Phiên Dịch Song Song", "📝 Chuyển Văn bản TTS"])

with tab1:
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1])
    with col_ctrl1:
        mode = st.selectbox(
            "Hướng dịch phiên dịch:",
            ["🇻🇳 Tiếng Việt ➔ 🇺🇸 Tiếng Anh", "🇺🇸 Tiếng Anh ➔ 🇻🇳 Tiếng Việt"]
        )
    with col_ctrl2:
        selected_voice = st.selectbox(
            "Giọng phát cabin phiên dịch:",
            list(VOICE_OPTIONS.keys()),
            index=0
        )
    with col_ctrl3:
        st.write("")
        st.write("")
        if st.button("🧹 Xóa nhật ký"):
            st.session_state["transcript_history"] = []
            st.rerun()

    # THIẾT LẬP MICRO THU ÂM
    mic_ready = False
    try:
        import speech_recognition as sr
        from streamlit_mic_recorder import mic_recorder
        from pydub import AudioSegment
        mic_ready = True
    except ImportError:
        st.error("⚠️ Chưa cài đủ thư viện speech_recognition / pydub / streamlit_mic_recorder!")

    if mic_ready:
        st.write("---")
        recorded_audio = mic_recorder(
            start_prompt="🔴 BẤM ĐỂ NÓI (BẮT ĐẦU PHÁT BIỂU)",
            stop_prompt="⏹️ BẤM DỪNG (XỬ LÝ DỊCH & PHÁT CABIN)",
            key="live_conference_mic"
        )

        if recorded_audio and 'bytes' in recorded_audio:
            audio_bytes = recorded_audio['bytes']
            if len(audio_bytes) > 5000:
                with st.spinner("⏳ Đang xử lý giọng nói & dịch thuật..."):
                    wav_path = None
                    try:
                        audio_stream = io.BytesIO(audio_bytes)
                        audio_segment = AudioSegment.from_file(audio_stream)
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                            audio_segment.export(tmp_wav.name, format="wav")
                            wav_path = tmp_wav.name

                        recognizer = sr.Recognizer()
                        with sr.AudioFile(wav_path) as source:
                            audio_data_rec = recognizer.record(source)

                        if mode == "🇻🇳 Tiếng Việt ➔ 🇺🇸 Tiếng Anh":
                            src_lang_code, tgt_lang_code = "vi-VN", "en-US"
                        else:
                            src_lang_code, tgt_lang_code = "en-US", "vi-VN"

                        spoken_text = recognizer.recognize_google(audio_data_rec, language=src_lang_code)
                        translated_text = translate_robust(spoken_text, src_lang_code, tgt_lang_code)

                        # Lưu vào tiến trình hội nghị
                        timestamp = time.strftime("%H:%M:%S")
                        st.session_state["transcript_history"].append({
                            "time": timestamp,
                            "original": spoken_text,
                            "translated": translated_text
                        })

                        # Phát tự động giọng cabin ngầm
                        tts_voice_code = VOICE_OPTIONS[selected_voice]
                        translated_audio_bytes = create_tts_audio(translated_text, tts_voice_code)
                        play_audio_hidden(translated_audio_bytes)

                    except sr.UnknownValueError:
                        st.warning("⚠️ Không nhận diện được âm thanh. Vui lòng nói rõ hơn.")
                    except Exception as e:
                        st.error(f"❌ Lỗi: {e}")
                    finally:
                        if wav_path and os.path.exists(wav_path):
                            os.remove(wav_path)

        # HÌNH THỨC HIỂN THỊ SONG SONG 2 CỘT THEO TIẾN TRÌNH HỘI NGHỊ
        st.write("### 📺 Bảng Theo Dõi Diễn Tiến Hội Nghị (Live Transcript)")
        
        col_header_left, col_header_right = st.columns(2)
        with col_header_left:
            st.markdown("#### 🇻🇳 Ngôn ngữ gốc (Tiếng Việt)")
        with col_header_right:
            st.markdown("#### 🇺🇸 Bản dịch cabin (Tiếng Anh)")

        st.divider()

        # Hiển thị từng lượt phát biểu
        if st.session_state["transcript_history"]:
            for item in reversed(st.session_state["transcript_history"]):
                col_left, col_right = st.columns(2)
                with col_left:
                    st.info(f"⏱️ **[{item['time']}]** {item['original']}")
                with col_right:
                    st.success(f"🌐 **[{item['time']}]** {item['translated']}")
        else:
            st.text("Chưa có dữ liệu phát biểu. Hãy bấm nút micro bên trên để bắt đầu...")

with tab2:
    st.subheader("Text to speech")
    text_input = st.text_area("Nhập văn bản cần đọc:", height=150)
    if st.button("Đọc"):
        if text_input:
            audio_data = create_tts_audio(text_input, "en-US-GuyNeural")
            st.audio(audio_data, format="audio/mp3")
