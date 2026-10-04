import time
import json
import urllib.parse
import urllib.request
import streamlit as st
import streamlit.components.v1 as components

# ------------------------------------------------------------------------------
# CẤU HÌNH GIAO DIỆN & DANH SÁCH NGÔN NGỮ
# ------------------------------------------------------------------------------
st.set_page_config(page_title="AI Translate Cabin Pro", layout="wide")

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
# HÀM DỊCH THUẬT AN TOÀN & ỔN ĐỊNH
# ------------------------------------------------------------------------------
from deep_translator import GoogleTranslator

@st.cache_data(show_spinner=False, ttl=3600)
def translate_safe(text, src_code, tgt_code):
    """Hàm dịch sử dụng deep-translator kết hợp API chuẩn không bị lỗi"""
    if not text.strip():
        return ""
    
    src = src_code.lower()
    tgt = tgt_code.lower()
    if src == "zh-cn": src = "zh-CN"
    if tgt == "zh-cn": tgt = "zh-CN"

    # Cách 1: Sử dụng deep-translator
    try:
        translator = GoogleTranslator(source=src, target=tgt)
        res = translator.translate(text)
        if res:
            return res
    except Exception:
        pass

    # Cách 2: Fallback trực tiếp qua Google Translate API endpoint chính thống
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src}&tl={tgt}&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            if translated_text:
                return translated_text
    except Exception as e:
        return f"Lỗi dịch thuật: {str(e)}"

    return "Không thể dịch được văn bản lúc này. Vui lòng thử lại."

# ------------------------------------------------------------------------------
# XÁC THỰC MẬT KHẨU
# ------------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Đăng nhập Hệ thống Cabin Phiên dịch")
    pwd_input = st.text_input("Nhập mật khẩu truy cập:", type="password")
    if st.button("Đăng nhập"):
        if pwd_input:
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

if "conference_logs" not in st.session_state:
    st.session_state["conference_logs"] = []

# ------------------------------------------------------------------------------
# GIAO DIỆN CHÍNH (TABS)
# ------------------------------------------------------------------------------
tab1, tab2 = st.tabs([
    "💬 Dịch văn bản & Hội thoại", 
    "🎙️ Cabin Phiên dịch Trực tiếp (Continuous)"
])

# ==============================================================================
# TAB 1: DỊCH VĂN BẢN & HỘI THOẠI
# ==============================================================================
with tab1:
    st.subheader("💬 Dịch văn bản & Hội thoại chuyên sâu")
    
    col_t1_src, col_t1_tgt, col_t1_voice = st.columns(3)
    with col_t1_src:
        src_lang_name_t1 = st.selectbox("Ngôn ngữ nguồn:", list(LANG_OPTIONS.keys()), index=0, key="t1_src")
    with col_t1_tgt:
        tgt_lang_name_t1 = st.selectbox("Ngôn ngữ đích:", list(LANG_OPTIONS.keys()), index=1, key="t1_tgt")
    with col_t1_voice:
        voice_t1_label = st.selectbox("Giọng đọc phát âm:", list(VOICE_OPTIONS.keys()), key="t1_voice")

    input_text = st.text_area("Nhập văn bản cần dịch:", height=150, placeholder="Dán văn bản cần dịch vào đây...")
    
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        translate_clicked = st.button("Dịch ngay", key="btn_tab1", type="primary", use_container_width=True)

    if translate_clicked:
        if input_text.strip():
            with st.spinner("Đang dịch thuật văn bản..."):
                src_code = LANG_OPTIONS[src_lang_name_t1]
                tgt_code = LANG_OPTIONS[tgt_lang_name_t1]
                
                res_text = translate_safe(input_text, src_code, tgt_code)
                
                st.markdown("### Kết quả dịch:")
                st.success(res_text)
                
                # Chỉ đọc phát âm nếu kết quả không phải là thông báo lỗi
                if "Lỗi dịch thuật" not in res_text and "Không thể dịch" not in res_text:
                    tts_code = LANG_OPTIONS[tgt_lang_name_t1]
                    clean_res = res_text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
                    components.html(f"""
                        <script>
                            if ('speechSynthesis' in window) {{
                                var msg = new SpeechSynthesisUtterance('{clean_res}');
                                msg.lang = '{tts_code}';
                                window.speechSynthesis.speak(msg);
                            }}
                        </script>
                    """, height=0)
        else:
            st.warning("Vui lòng nhập văn bản cần dịch.")

# ==============================================================================
# TAB 2: CABIN PHIÊN DỊCH TRỰC TIẾP
# ==============================================================================
with tab2:
    st.subheader("🎙️ Phiên dịch Hội nghị Trực tiếp (Chế độ Cabin Liên tục)")
    st.markdown("Micro được giữ mở liên tục, tự động bắt các đoạn ngắt câu để dịch và đọc âm thanh song song.")

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

    spoken_text = st.text_input("Stream Data Bridge", key="cabin_stream_bridge", label_visibility="collapsed")

    if spoken_text and spoken_text.strip():
        raw_text = spoken_text.strip()
        if "last_cabin_text" not in st.session_state or st.session_state["last_cabin_text"] != raw_text:
            st.session_state["last_cabin_text"] = raw_text
            
            src_code_val = LANG_OPTIONS[src_lang_name_t2]
            tgt_code_val = LANG_OPTIONS[tgt_lang_name_t2]
            
            translated = translate_safe(raw_text, src_code_val, tgt_code_val)
            st.session_state["conference_logs"].insert(0, {
                "time": time.strftime("%H:%M:%S"),
                "original": raw_text,
                "translated": translated
            })

    cabin_html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            .cabin-box {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
            }}
            .btn-control {{
                padding: 12px 28px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                margin: 5px;
                color: white;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .btn-start {{ background-color: #28a745; }}
            .btn-stop {{ background-color: #dc3545; }}
            #status-badge {{
                margin-top: 15px;
                font-weight: bold;
                font-size: 15px;
                color: #495057;
            }}
            #live-box {{
                margin-top: 12px;
                font-style: italic;
                color: #0056b3;
                font-size: 17px;
                min-height: 28px;
            }}
        </style>
    </head>
    <body>
    <div class="cabin-box">
        <div>
            <button id="start-btn" class="btn-control btn-start" onclick="startCabin()">🔴 KÍCH HOẠT CABIN TRỰC TIẾP</button>
            <button id="stop-btn" class="btn-control btn-stop" onclick="stopCabin()" disabled>⏹️ DỪNG CABIN</button>
        </div>
        <div id="status-badge">Trạng thái: Đang sẵn sàng kết nối Microphone...</div>
        <div id="live-box">Chưa có âm thanh đầu vào...</div>
    </div>

    <script>
        var recognition;
        var isRunning = false;
        var silenceTimer = null;
        var accumulatedSentence = "";

        function updateStreamlitInput(text) {{
            const doc = window.parent.document;
            const inputs = doc.querySelectorAll('input[type="text"]');
            for (let input of inputs) {{
                if (input.placeholder === "Stream Data Bridge" || input.value !== undefined) {{
                    let setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    if (setter) {{
                        setter.call(input, text);
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        break;
                    }}
                }}
            }}
        }}

        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
            document.getElementById('status-badge').innerText = '❌ Trình duyệt không hỗ trợ Web Speech API. Hãy dùng Google Chrome hoặc Microsoft Edge!';
        }} else {{
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = '{lang_code_js}';

            recognition.onstart = function() {{
                isRunning = true;
                document.getElementById('status-badge').innerHTML = '🟢 Cabin đang mở mic liên tục...';
                document.getElementById('start-btn').disabled = true;
                document.getElementById('stop-btn').disabled = false;
            }};

            recognition.onresult = function(event) {{
                let interim = '';
                let finalStr = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {{
                    if (event.results[i].isFinal) {{
                        finalStr += event.results[i][0].transcript;
                    }} else {{
                        interim += event.results[i][0].transcript;
                    }}
                }}

                let currentSpoken = finalStr || interim;
                if (currentSpoken.trim() !== "") {{
                    accumulatedSentence = currentSpoken;
                    document.getElementById('live-box').innerText = '🎙️ Đang nghe: "' + accumulatedSentence + '"';

                    clearTimeout(silenceTimer);
                    silenceTimer = setTimeout(function() {{
                        if (accumulatedSentence.trim() !== "") {{
                            document.getElementById('live-box').innerText = '⚡ Đang dịch và xử lý cabin...';
                            updateStreamlitInput(accumulatedSentence);
                            accumulatedSentence = "";
                        }}
                    }}, 1200);
                }}
            }};

            recognition.onend = function() {{
                if (isRunning) {{
                    try {{ recognition.start(); }} catch (e) {{}}
                }} else {{
                    document.getElementById('status-badge').innerText = '⏹️ Đã dừng hệ thống cabin.';
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;
                    document.getElementById('live-box').innerText = 'Phiên dịch đã kết thúc.';
                }}
            }};
        }}

        function startCabin() {{
            if (recognition) {{
                isRunning = true;
                try {{ recognition.start(); }} catch (e) {{}}
            }}
        }}

        function stopCabin() {{
            isRunning = false;
            clearTimeout(silenceTimer);
            if (recognition) {{ recognition.stop(); }}
        }}
    </script>
    </body>
    </html>
    """

    components.html(cabin_html_code, height=160)

    st.write("---")
    st.markdown("### 📺 Nhật ký trực tiếp (Live Stream Translation Log)")
    
    col_hist_left, col_hist_right = st.columns(2)
    with col_hist_left:
        st.markdown(f"#### 🌐 Bài phát biểu gốc ({src_lang_name_t2})")
        if st.session_state["conference_logs"]:
            for item in st.session_state["conference_logs"]:
                st.info(f"⏱️ **[{item['time']}]** {item['original']}")
        else:
            st.caption("Chưa có dữ liệu hội thoại trực tiếp...")

    with col_hist_right:
        st.markdown(f"#### 🌐 Bản dịch cabin ({tgt_lang_name_t2})")
        if st.session_state["conference_logs"]:
            for item in st.session_state["conference_logs"]:
                st.success(f"⏱️ **[{item['time']}]** {item['translated']}")
        else:
            st.caption("Đang chờ bản dịch...")
