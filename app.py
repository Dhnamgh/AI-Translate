import random
import streamlit as st
import asyncio
import edge_tts
from deep_translator import GoogleTranslator, MyMemoryTranslator
import tempfile
import os
import io
import time
import base64

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

# 3. DANH SÁCH GIỌNG ĐỌC AI (NEURAL)
VOICE_OPTIONS = {
    # Giọng Tiếng Anh - Mỹ (US)
    "🇺🇸 Nam - Anh-Mỹ (Guy - Trầm ấm, Chuẩn Học thuật / Khoa học)": "en-US-GuyNeural",
    "🇺🇸 Nữ - Anh-Mỹ (Jenny - Truyền cảm, Tự nhiên)": "en-US-JennyNeural",
    "🇺🇸 Nữ - Anh-Mỹ (Aria - Trang trọng, Rõ chữ)": "en-US-AriaNeural",
    "🇺🇸 Nam - Anh-Mỹ (Christopher - Đọc báo cáo / Bản tin)": "en-US-ChristopherNeural",

    # Giọng Tiếng Anh - Anh (UK)
    "🇬🇧 Nữ - Anh-Anh (Sonia - Giọng Anh chuẩn Quý phái)": "en-GB-SoniaNeural",
    "🇬🇧 Nam - Anh-Anh (Ryan - Điềm tĩnh, Trang trọng)": "en-GB-RyanNeural",

    # Giọng Tiếng Việt
    "🇻🇳 Nữ - Tiếng Việt (Hoài Mỹ - Báo cáo / Thuyết trình)": "vi-VN-HoaiMyNeural",
    "🇻🇳 Nam - Tiếng Việt (Nam Minh - Trang trọng / Giảng dạy)": "vi-VN-NamMinhNeural"
}

# 4. HÀM TẠO ÂM THANH
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

# 5. HÀM DỊCH CHUẨN XỬ LÝ LỖI MÁY CHỦ
def translate_robust(text, src_code_full, tgt_code_full):
    src_base = "vi" if "vi" in src_code_full.lower() else "en"
    tgt_base = "en" if "en" in tgt_code_full.lower() else "vi"

    # Cách 1: Thử Google Translator
    try:
        return GoogleTranslator(source=src_base, target=tgt_base).translate(text)
    except Exception:
        pass

    # Cách 2: Dự phòng MyMemory với mã ngôn ngữ chuẩn đầy đủ (vi-VN, en-US)
    try:
        src_mm = "vi-VN" if src_base == "vi" else "en-US"
        tgt_mm = "en-US" if tgt_base == "en" else "vi-VN"
        return MyMemoryTranslator(source=src_mm, target=tgt_mm).translate(text)
    except Exception as e:
        raise Exception(f"Lỗi dịch thuật: {e}")

# 6. PHÁT ÂM THANH CABIN TỰ ĐỘNG NGẦM (KHÔNG HIỂN THỊ TRÌNH PHÁT)
def play_audio_autoplay_hidden(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay style="display:none;">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    st.markdown(md, unsafe_allow_html=True)


# --- GIAO DIỆN ỨNG DỤNG ---
st.title("AI Translate")

tab1, tab2 = st.tabs(["📝 Chuyển Văn bản thành Giọng đọc (TTS)", "🎙️ Dịch Hội nghị Bằng Giọng nói"])

# ==============================================================================
# TAB 1: TEXT TO SPEECH (GIỮ NGUYÊN HOÀN TOÀN CODE CŨ CỦA THẦY)
# ==============================================================================
with tab1:
    st.subheader("Text to speech")
    
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        selected_voice_label = st.selectbox(
            "1. Chọn giọng đọc AI (Anh - Mỹ / Anh - Anh / Tiếng Việt):",
            list(VOICE_OPTIONS.keys()),
            index=0
        )
        voice_code = VOICE_OPTIONS[selected_voice_label]
        
        speech_rate = st.slider(
            "2. Điều chỉnh Tốc độ đọc (%):",
            min_value=-40, max_value=40, value=-5, step=5,
            help="Đọc bài báo khoa học / thuyết trình nên để khoảng -5% đến 0% để âm thanh rõ chữ."
        )

        pitch_val = st.slider(
            "3. Điều chỉnh Cao độ (Pitch Hz):",
            min_value=-20, max_value=20, value=0, step=2,
            help="Tăng/giảm độ trầm ấm của giọng đọc."
        )

        text_input = st.text_area(
            "4. Nhập nội dung văn bản / bài báo cáo:",
            height=200,
            placeholder="Nhập văn bản tiếng Anh hoặc tiếng Việt cần chuyển thành giọng đọc..."
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
# TAB 2: DỊCH HỘI NGHỊ TRỰC TIẾP (CẬP NHẬT TÍNH NĂNG THEO YÊU CẦU)
# ==============================================================================
with tab2:
    st.subheader("Phiên dịch Hội nghị bằng Giọng nói (Micro & Phát lại âm thanh)")
    
    if "conference_logs" not in st.session_state:
        st.session_state["conference_logs"] = []

    # KIỂM TRA THƯ VIỆN MICRO HỆ THỐNG
    mic_ready = False
    try:
        import speech_recognition as sr
        from streamlit_mic_recorder import mic_recorder
        mic_ready = True
    except ImportError:
        st.error("⚠️ Hệ thống chưa cài đủ gói `streamlit-mic-recorder` và `SpeechRecognition`. Vui lòng kiểm tra file `requirements.txt`.")

    if mic_ready:
        col_lang1, col_lang2, col_lang3 = st.columns([2, 2, 1])
        with col_lang1:
            mode = st.selectbox(
                "Hướng dịch phiên dịch:",
                ["🇻🇳 Tiếng Việt ➔ 🇺🇸 Tiếng Anh", "🇺🇸 Tiếng Anh ➔ 🇻🇳 Tiếng Việt"],
                key="tab2_mode"
            )
        with col_lang2:
            cabin_voice_label = st.selectbox(
                "Giọng đọc cabin phiên dịch:",
                list(VOICE_OPTIONS.keys()),
                key="tab2_cabin_voice"
            )
        with col_lang3:
            st.write("")
            st.write("")
            if st.button("🧹 Xóa nhật ký", use_container_width=True):
                st.session_state["conference_logs"] = []
                st.rerun()

        st.write("---")
        st.markdown("##### 🎙️ Bắt đầu phát biểu (Nhấn nút dưới đây để nói):")
        
        recorded_audio = mic_recorder(
            start_prompt="🔴 Bấm để nói (Start Recording)",
            stop_prompt="⏹️ Bấm để dừng & Dịch (Stop Recording)",
            key="conference_mic"
        )

        if recorded_audio and 'bytes' in recorded_audio:
            audio_bytes = recorded_audio['bytes']
            if len(audio_bytes) > 5000:
                with st.spinner("⏳ Đang xử lý nhận diện & dịch thuật..."):
                    tmp_wav_path = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                            tmp_wav.write(audio_bytes)
                            tmp_wav_path = tmp_wav.name

                        recognizer = sr.Recognizer()
                        with sr.AudioFile(tmp_wav_path) as source:
                            audio_data_rec = recognizer.record(source)

                        if mode == "🇻🇳 Tiếng Việt ➔ 🇺🇸 Tiếng Anh":
                            src_code, tgt_code = "vi-VN", "en-US"
                        else:
                            src_code, tgt_code = "en-US", "vi-VN"

                        spoken_text = recognizer.recognize_google(audio_data_rec, language=src_code)
                        translated_text = translate_robust(spoken_text, src_code, tgt_code)

                        # Lưu lịch sử dịch hội nghị
                        st.session_state["conference_logs"].append({
                            "time": time.strftime("%H:%M:%S"),
                            "original": spoken_text,
                            "translated": translated_text
                        })

                        # Phát âm thanh dịch tự động ngầm
                        tts_voice_code = VOICE_OPTIONS[cabin_voice_label]
                        translated_audio_bytes = create_tts_audio(translated_text, tts_voice_code)
                        play_audio_autoplay_hidden(translated_audio_bytes)

                    except sr.UnknownValueError:
                        st.error("❌ Không thể nhận diện được giọng nói. Vui lòng nói rõ hơn và thử lại!")
                    except Exception as e:
                        st.error(f"❌ Có lỗi trong quá trình xử lý: {e}")
                    finally:
                        if tmp_wav_path and os.path.exists(tmp_wav_path):
                            os.remove(tmp_wav_path)

        st.write("---")
        st.markdown("### 📺 Nhật Ký Khớp Ngôn Ngữ Trực Tiếp (Live Stream Log)")
        
        col_hist_left, col_hist_right = st.columns(2)
        with col_hist_left:
            st.markdown("#### 🇻🇳 Ngôn ngữ phát biểu (Gốc)")
            if st.session_state["conference_logs"]:
                for item in reversed(st.session_state["conference_logs"]):
                    st.info(f"⏱️ **[{item['time']}]** {item['original']}")
            else:
                st.caption("Chưa có lượt phát biểu nào...")

        with col_hist_right:
            st.markdown("#### 🇺🇸 Bản dịch cabin phiên dịch")
            if st.session_state["conference_logs"]:
                for item in reversed(st.session_state["conference_logs"]):
                    st.success(f"⏱️ **[{item['time']}]** {item['translated']}")
            else:
                st.caption("Chưa có bản dịch...")
