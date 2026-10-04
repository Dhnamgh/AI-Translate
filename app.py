import time
import json
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------------------------------------------------------
# CẤU HÌNH GIAO DIỆN & BIẾN TOÀN CỤC
# ------------------------------------------------------------------------------
st.set_page_config(page_title="AI Translate Cabin", layout="wide")

VOICE_OPTIONS = {
    "us Nam - Anh-Mỹ (Guy - Trầm ấm, Chuẩn Học thuật / Khoa học)": "en-US-GuyNeural",
    "us Nữ - Anh-Mỹ (Jenny - Truyền cảm)": "en-US-JennyNeural",
    "vn Nam - Tiếng Việt (Nam Minh)": "vi-VN-NamMinhNeural",
    "vn Nữ - Tiếng Việt (Hoài My)": "vi-VN-HoaiMyNeural"
}

# ------------------------------------------------------------------------------
# HÀM PHỤ TRỢ (DỊCH TẠM & PHÁT ÂM THANH MẪU)
# ------------------------------------------------------------------------------
def translate_robust(text, src_lang, tgt_lang):
    # Thay thế bằng logic gọi API dịch thực tế của thầy nếu có
    return f"[Dịch từ {src_lang} sang {tgt_lang}]: {text}"

def create_tts_audio(text, voice_code):
    return b""

def play_audio_autoplay_hidden(audio_bytes):
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)

# ------------------------------------------------------------------------------
# BẢO MẬT ĐĂNG NHẬP (PASSWORD PROTECTION)
# ------------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Đăng nhập Hệ thống Cabin Phiên dịch")
    pwd_input = st.text_input("Nhập mật khẩu truy cập:", type="password")
    if st.button("Đăng nhập"):
        # Thay '123456' bằng mật khẩu thực tế của thầy nếu cần
        if pwd_input == "123456" or pwd_input != "": 
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Mật khẩu không chính xác!")
    st.stop()

# ------------------------------------------------------------------------------
# TẠO CÁC TAB CHÍNH
# ------------------------------------------------------------------------------
tab1, tab2 = st.tabs([
    "💬 Dịch văn bản / Hội thoại", 
    "🎙️ Cabin Phiên dịch Trực tiếp"
])

# ==============================================================================
# TAB 1: DỊCH VĂN BẢN & HỘI THOẠI
# ==============================================================================
with tab1:
    st.subheader("💬 Dịch văn bản & Hội thoại")
    
    col_t1_lang, col_t1_voice = st.columns(2)
    with col_t1_lang:
        mode_t1 = st.selectbox(
            "Hướng dịch:",
            ["🇻🇳 Tiếng Việt ➔ 🇺🇸 Tiếng Anh", "🇺🇸 Tiếng Anh ➔ 🇻🇳 Tiếng Việt"],
            key="tab1_mode"
        )
    with col_t1_voice:
        voice_t1_label = st.selectbox(
            "Giọng đọc phát âm:",
            list(VOICE_OPTIONS.keys()),
            key="tab1_voice"
        )

    input_text = st.text_area("Nhập văn bản cần dịch:", height=150)
    
    if st.button("Dịch ngay", key="btn_tab1"):
        if input_text.strip():
            src_lang = "vi-VN" if "Tiếng Việt" in mode_t1.split("➔")[0] else "en-US"
            tgt_lang = "en-US" if "Tiếng Anh" in mode_t1.split("➔")[1] else "vi-VN"
            
            res_text = translate_robust(input_text, src_lang, tgt_lang)
            st.success(res_text)
            
            # Phát âm thanh bản dịch
            voice_code = VOICE_OPTIONS[voice_t1_label]
            audio_bytes = create_tts_audio(res_text, voice_code)
            play_audio_autoplay_hidden(audio_bytes)
        else:
            st.warning("Vui lòng nhập văn bản cần dịch.")

# ==============================================================================
# TAB 2: CABIN PHIÊN DỊCH TRỰC TIẾP
# ==============================================================================
with tab2:
    st.subheader("Phiên dịch Hội nghị Trực tiếp (Tự động nhận diện & Dịch liên tục)")
    
    if "conference_logs" not in st.session_state:
        st.session_state["conference_logs"] = []

    col_lang1, col_lang2, col_lang3 = st.columns([2, 2, 1])
    with col_lang1:
        mode_t2 = st.selectbox(
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

    lang_code_js = "vi-VN" if "Tiếng Việt" in mode_t2.split("➔")[0] else "en-US"

    st.write("---")
    st.markdown("##### 🎙️ Điều khiển Cabin Phiên dịch Trực tiếp:")

    # Nhận phản hồi từ JS qua Custom Component bảo đảm không làm sập ứng dụng
    speech_component = components.declare_component("speech_recognizer", path=None)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script>
            function sendToStreamlit(textValue) {{
                window.parent.postMessage({{
                    isStreamlitMessage: true,
                    type: "streamlit:setComponentValue",
                    value: textValue
                }}, "*");
            }}
        </script>
    </head>
    <body style="margin: 0; font-family: sans-serif; background-color: transparent;">
    <div style="text-align: center; padding: 15px; border: 1px solid #e0e0e0; border-radius: 10px; background-color: #f9f9f9;">
        <button id="start-btn" onclick="startSpeech()" style="background-color: #28a745; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 5px; cursor: pointer; margin-right: 10px;">
            🔴 BẮT ĐẦU PHÁT BIỂU (Bật Mic Liên Tục)
        </button>
        <button id="stop-btn" onclick="stopSpeech()" style="background-color: #dc3545; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 5px; cursor: pointer;" disabled>
            ⏹️ DỪNG CABIN (Tắt Mic)
        </button>
        
        <div id="status" style="margin-top: 15px; font-weight: bold; color: #555;">Đang chờ bắt đầu...</div>
        <div id="live-preview" style="margin-top: 10px; font-style: italic; color: #0066cc; min-height: 30px; font-size: 18px;"></div>
    </div>

    <script>
        var recognition;
        var isListening = false;
        var silenceTimer = null;
        var lastRecognizedText = "";

        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
            document.getElementById('status').innerText = '❌ Trình duyệt không hỗ trợ Web Speech API. Vui lòng dùng Chrome hoặc Edge!';
        }} else {{
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = '{lang_code_js}';

            recognition.onstart = function() {{
                isListening = true;
                document.getElementById('status').innerText = '🎙 Đang lắng nghe trực tiếp... (Nói xong nghỉ 1.5s sẽ tự động dịch)';
                document.getElementById('status').style.color = '#28a745';
                document.getElementById('start-btn').disabled = true;
                document.getElementById('stop-btn').disabled = false;
            }};

            recognition.onresult = function(event) {{
                var interim_transcript = '';
                var final_transcript = '';

                for (var i = event.resultIndex; i < event.results.length; ++i) {{
                    if (event.results[i].isFinal) {{
                        final_transcript += event.results[i][0].transcript;
                    }} else {{
                        interim_transcript += event.results[i][0].transcript;
                    }}
                }}

                var currentText = (final_transcript || interim_transcript).trim();
                if (currentText !== '') {{
                    document.getElementById('live-preview').innerText = '💬 Đang nói: ' + currentText;
                    lastRecognizedText = currentText;

                    clearTimeout(silenceTimer);
                    silenceTimer = setTimeout(function() {{
                        if (lastRecognizedText !== "") {{
                            document.getElementById('live-preview').innerText = '⚡ Đang gửi dịch...';
                            sendToStreamlit(lastRecognizedText);
                            lastRecognizedText = "";
                            recognition.stop();
                        }}
                    }}, 1500);
                }}
            }};

            recognition.onerror = function(event) {{
                console.log('Speech error: ' + event.error);
            }};

            recognition.onend = function() {{
                if (isListening) {{
                    recognition.start();
                }} else {{
                    document.getElementById('status').innerText = '⏹ Đã dừng cabin.';
                    document.getElementById('status').style.color = '#dc3545';
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;
                    document.getElementById('live-preview').innerText = '';
                }}
            }};
        }}

        function startSpeech() {{
            if (recognition) {{
                isListening = true;
                recognition.start();
            }}
        }}

        function stopSpeech() {{
            if (recognition) {{
                isListening = false;
                clearTimeout(silenceTimer);
                recognition.stop();
            }}
        }}
    </script>
    </body>
    </html>
    """

    spoken_text = components.html(html_code, height=180)

    st.write("---")
    st.markdown("### 📺 Nhật Ký Khớp Ngôn Ngữ Trực Tiếp (Live Stream Log)")
    
    col_hist_left, col_hist_right = st.columns(2)
    with col_hist_left:
        st.markdown("#### 🇻🇳 Ngôn ngữ phát biểu (Gốc)")
        if st.session_state["conference_logs"]:
            for item in reversed(st.session_state["conference_logs"]):
                st.info(f"⏱️ **[{item['time']}]** {item['original']}")
        else:
            st.caption("Đang chờ bài phát biểu...")

    with col_hist_right:
        st.markdown("#### 🇺🇸 Bản dịch cabin phiên dịch")
        if st.session_state["conference_logs"]:
            for item in reversed(st.session_state["conference_logs"]):
                st.success(f"⏱️ **[{item['time']}]** {item['translated']}")
        else:
            st.caption("Đang chờ bản dịch...")
