import time
import json
import urllib.parse
import urllib.request
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------------------------------------------------------
# CẤU HÌNH GIAO DIỆN & DANH SÁCH NGÔN NGỮ
# ------------------------------------------------------------------------------
st.set_page_config(page_title="AI Translate Cabin", layout="wide")

LANG_OPTIONS = {
    "🇻🇳 Tiếng Việt": "vi",
    "🇺🇸 Tiếng Anh (Mỹ)": "en",
    "🇬🇧 Tiếng Anh (Anh)": "en",
    "🇨🇳 Tiếng Trung (Phổ thông)": "zh-CN",
    "🇯🇵 Tiếng Nhật": "ja",
    "🇰🇷 Tiếng Hàn": "ko",
    "🇫🇷 Tiếng Pháp": "fr",
    "🇩🇪 Tiếng Đức": "de",
    "🇪🇸 Tiếng Tây Ban Nha": "es",
    "🇮🇹 Tiếng Ý": "it",
    "🇷🇺 Tiếng Nga": "ru",
    "🇹🇭 Tiếng Thái": "th"
}

VOICE_OPTIONS = {
    "us Nam - Anh-Mỹ (Guy - Trầm ấm)": "en",
    "us Nữ - Anh-Mỹ (Jenny - Truyền cảm)": "en",
    "vn Nam - Tiếng Việt (Nam Minh)": "vi",
    "vn Nữ - Tiếng Việt (Hoài My)": "vi"
}

# ------------------------------------------------------------------------------
# HÀM DỊCH & TTS BẰNG THƯ VIỆN CHUẨN PYTHON (KHÔNG BỊ LỖI THIẾU MODULE)
# ------------------------------------------------------------------------------
def translate_robust(text, src_lang, tgt_lang):
    """Dịch thật qua Google Translate API công khai (không cần pip install)"""
    if not text.strip():
        return ""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src_lang}&tl={tgt_lang}&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            return translated_text
    except Exception as e:
        return f"Lỗi kết nối dịch: {str(e)}"

# ------------------------------------------------------------------------------
# BẢO MẬT ĐĂNG NHẬP
# ------------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Đăng nhập Hệ thống Cabin Phiên dịch")
    pwd_input = st.text_input("Nhập mật khẩu truy cập:", type="password")
    if st.button("Đăng nhập"):
        st.session_state["authenticated"] = True
        st.rerun()
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
    
    col_t1_src, col_t1_tgt, col_t1_voice = st.columns(3)
    with col_t1_src:
        src_lang_name_t1 = st.selectbox("Ngôn ngữ nguồn:", list(LANG_OPTIONS.keys()), index=0, key="t1_src")
    with col_t1_tgt:
        tgt_lang_name_t1 = st.selectbox("Ngôn ngữ đích:", list(LANG_OPTIONS.keys()), index=1, key="t1_tgt")
    with col_t1_voice:
        voice_t1_label = st.selectbox("Giọng đọc phát âm:", list(VOICE_OPTIONS.keys()), key="t1_voice")

    input_text = st.text_area("Nhập văn bản cần dịch:", height=150)
    
    if st.button("Dịch ngay", key="btn_tab1"):
        if input_text.strip():
            src_code = LANG_OPTIONS[src_lang_name_t1]
            tgt_code = LANG_OPTIONS[tgt_lang_name_t1]
            
            # Dịch thật
            res_text = translate_robust(input_text, src_code, tgt_code)
            st.success(res_text)
            
            # Đọc âm thanh trực tiếp qua HTML5 SpeechSynthesis (Không lo thiếu file mp3)
            tts_code = LANG_OPTIONS[tgt_lang_name_t1]
            clean_res = res_text.replace("'", "\\'").replace("\n", " ")
            components.html(f"""
                <script>
                    var msg = new SpeechSynthesisUtterance('{clean_res}');
                    msg.lang = '{tts_code}';
                    window.speechSynthesis.speak(msg);
                </script>
            """, height=0)
        else:
            st.warning("Vui lòng nhập văn bản cần dịch.")

# ==============================================================================
# TAB 2: CABIN PHIÊN DỊCH TRỰC TIẾP
# ==============================================================================
with tab2:
    st.subheader("Phiên dịch Hội nghị Trực tiếp (Tự động nhận diện & Dịch liên tục)")
    
    if "conference_logs" not in st.session_state:
        st.session_state["conference_logs"] = []

    col_t2_src, col_t2_tgt, col_t2_voice, col_t2_clear = st.columns([2, 2, 2, 1])
    with col_t2_src:
        src_lang_name_t2 = st.selectbox("Ngôn ngữ nói (Mic):", list(LANG_OPTIONS.keys()), index=0, key="t2_src")
    with col_t2_tgt:
        tgt_lang_name_t2 = st.selectbox("Ngôn ngữ dịch out:", list(LANG_OPTIONS.keys()), index=1, key="t2_tgt")
    with col_t2_voice:
        cabin_voice_label = st.selectbox("Giọng đọc cabin:", list(VOICE_OPTIONS.keys()), key="t2_voice")
    with col_t2_clear:
        st.write("")
        st.write("")
        if st.button("🧹 Xóa nhật ký", use_container_width=True):
            st.session_state["conference_logs"] = []
            st.rerun()

    lang_code_js = "vi-VN" if LANG_OPTIONS[src_lang_name_t2] == "vi" else "en-US"

    st.write("---")
    st.markdown("##### 🎙️ Điều khiển Cabin Phiên dịch Trực tiếp:")

    spoken_text = st.text_input("Nhận diện giọng nói:", key="speech_recognition_input", label_visibility="collapsed")

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script>
            function setStreamlitValue(value) {{
                var inputs = window.parent.document.querySelectorAll('input[type="text"]');
                for (var i = 0; i < inputs.length; i++) {{
                    if (inputs[i].ariaLabel === "Nhận diện giọng nói:") {{
                        let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        nativeInputValueSetter.call(inputs[i], value);
                        inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        break;
                    }}
                }}
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
                document.getElementById('status').innerText = '🎙 Đang lắng nghe... (Tự động dịch sau 1.5s ngắt câu)';
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
                            setStreamlitValue(lastRecognizedText);
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

    components.html(html_code, height=180)

    if spoken_text and spoken_text.strip():
        raw_text = spoken_text.strip()
        if "last_processed_text" not in st.session_state or st.session_state["last_processed_text"] != raw_text:
            st.session_state["last_processed_text"] = raw_text
            
            src_code = LANG_OPTIONS[src_lang_name_t2]
            tgt_code = LANG_OPTIONS[tgt_lang_name_t2]
            
            try:
                translated = translate_robust(raw_text, src_code, tgt_code)
                st.session_state["conference_logs"].append({
                    "time": time.strftime("%H:%M:%S"),
                    "original": raw_text,
                    "translated": translated
                })
                
                # Đọc phát âm bản dịch
                clean_trans = translated.replace("'", "\\'").replace("\n", " ")
                components.html(f"""
                    <script>
                        var msg = new SpeechSynthesisUtterance('{clean_trans}');
                        msg.lang = '{tgt_code}';
                        window.speechSynthesis.speak(msg);
                    </script>
                """, height=0)
                
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi phiên dịch: {e}")

    st.write("---")
    st.markdown("### 📺 Nhật Ký Khớp Ngôn Ngữ Trực Tiếp (Live Stream Log)")
    
    col_hist_left, col_hist_right = st.columns(2)
    with col_hist_left:
        st.markdown(f"#### 🌐 Phát biểu gốc ({src_lang_name_t2})")
        if st.session_state["conference_logs"]:
            for item in reversed(st.session_state["conference_logs"]):
                st.info(f"⏱️ **[{item['time']}]** {item['original']}")
        else:
            st.caption("Đang chờ bài phát biểu...")

    with col_hist_right:
        st.markdown(f"#### 🌐 Bản dịch cabin ({tgt_lang_name_t2})")
        if st.session_state["conference_logs"]:
            for item in reversed(st.session_state["conference_logs"]):
                st.success(f"⏱️ **[{item['time']}]** {item['translated']}")
        else:
            st.caption("Đang chờ bản dịch...")
