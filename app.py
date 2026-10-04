import time
import json
import asyncio
import urllib.parse
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
from deep_translator import MyMemoryTranslator
import edge_tts

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

VOICE_MAP = {
    "us Nam - Anh-Mỹ (Guy - Trầm ấm)": "en-US-GuyNeural",
    "us Nữ - Anh-Mỹ (Jenny - Truyền cảm)": "en-US-JennyNeural",
    "vn Nam - Tiếng Việt (Nam Minh)": "vi-VN-NamMinhNeural",
    "vn Nữ - Tiếng Việt (Hoài My)": "vi-VN-HoaiMyNeural"
}

# ------------------------------------------------------------------------------
# HÀM DỊCH THUẬT AN TOÀN (MYMEMORY)
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def translate_stable(text, src_code, tgt_code):
    if not text.strip():
        return ""
    
    src = src_code.lower()
    tgt = tgt_code.lower()
    if src == "zh-cn": src = "zh-CN"
    if tgt == "zh-cn": tgt = "zh-CN"

    try:
        translator = MyMemoryTranslator(source=src, target=tgt)
        res = translator.translate(text)
        if res and res.strip():
            return res
    except Exception:
        pass

    try:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair={src}|{tgt}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if 'responseData' in data and data['responseData']['translatedText']:
                return data['responseData']['translatedText']
    except Exception as e:
        return f"Không thể kết nối dịch thuật: {str(e)}"

    return "Không thể dịch được văn bản lúc này. Vui lòng thử lại."

# ------------------------------------------------------------------------------
# HÀM TẠO FILE AUDIO MP3 BẰNG EDGE-TTS
# ------------------------------------------------------------------------------
async def generate_tts_async(text, voice_key, speed_rate, output_filename):
    voice_name = VOICE_MAP.get(voice_key, "en-US-GuyNeural")
    percent = int((speed_rate - 1.0) * 100)
    rate_str = f"+{percent}%" if percent >= 0 else f"{percent}%"
    
    communicate = edge_tts.Communicate(text, voice_name, rate=rate_str)
    await communicate.save(output_filename)

def create_mp3(text, voice_key, speed_rate, filename="translated_output.mp3"):
    try:
        asyncio.run(generate_tts_async(text, voice_key, speed_rate, filename))
        return True
    except Exception:
        return False

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

# ------------------------------------------------------------------------------
# GIAO DIỆN CHÍNH (TABS)
# ------------------------------------------------------------------------------
tab1, tab2 = st.tabs([
    "💬 Dịch văn bản & Hội thoại", 
    "🎙️ Cabin Phiên dịch Trực tiếp"
])

# ==============================================================================
# TAB 1: DỊCH VĂN BẢN & HỘI THOẠI (GIỮ NGUYÊN)
# ==============================================================================
with tab1:
    st.subheader("💬 Dịch văn bản & Hội thoại chuyên sâu")
    
    col_t1_src, col_t1_tgt = st.columns(2)
    with col_t1_src:
        src_lang_name_t1 = st.selectbox("Ngôn ngữ nguồn:", list(LANG_OPTIONS.keys()), index=0, key="t1_src")
    with col_t1_tgt:
        tgt_lang_name_t1 = st.selectbox("Ngôn ngữ đích:", list(LANG_OPTIONS.keys()), index=1, key="t1_tgt")

    input_text = st.text_area("Nhập văn bản cần dịch:", height=130, placeholder="Dán văn bản cần dịch vào đây...", key="t1_input_text")
    
    col_btn1, _ = st.columns([1, 5])
    with col_btn1:
        translate_clicked = st.button("Dịch ngay", key="btn_tab1", type="primary", use_container_width=True)

    if translate_clicked:
        if input_text.strip():
            with st.spinner("Đang dịch thuật văn bản..."):
                src_code = LANG_OPTIONS[src_lang_name_t1]
                tgt_code = LANG_OPTIONS[tgt_lang_name_t1]
                res_text = translate_stable(input_text, src_code, tgt_code)
                st.session_state["last_translation"] = res_text
        else:
            st.warning("Vui lòng nhập văn bản cần dịch.")

    if "last_translation" in st.session_state and st.session_state["last_translation"]:
        st.markdown("### Kết quả dịch:")
        st.success(st.session_state["last_translation"])

        st.markdown("---")
        st.markdown("##### 🔊 Cài đặt Âm thanh & Tải về (Tự động cập nhật khi đổi giọng/tốc độ):")
        
        col_v_sel, col_r_sel = st.columns(2)
        with col_v_sel:
            voice_t1_label = st.selectbox("Chọn giọng đọc:", list(VOICE_MAP.keys()), key="t1_voice_dynamic")
        with col_r_sel:
            speed_option = st.slider("Tốc độ đọc (x lần):", min_value=0.5, max_value=2.0, value=1.0, step=0.1, key="t1_speed_dynamic")

        audio_file = "translated_speech.mp3"
        success_audio = create_mp3(st.session_state["last_translation"], voice_t1_label, speed_option, audio_file)

        if success_audio:
            try:
                with open(audio_file, "rb") as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    label="📥 Tải xuống file MP3",
                    data=audio_bytes,
                    file_name="phien_dich_ai.mp3",
                    mime="audio/mp3",
                    key="download_mp3_btn"
                )
            except Exception:
                pass

# ==============================================================================
# TAB 2: CABIN PHIÊN DỊCH TRỰC TIẾP (BÊN TRÁI DỊCH, BÊN PHẢI GỐC)
# ==============================================================================
with tab2:
    st.subheader("🎙️ Phiên dịch Hội nghị Trực tiếp (Cabin Song Song)")
    st.markdown("Hệ thống nhận diện giọng nói trực tiếp, hiển thị bản dịch bên trái và văn bản gốc bên phải theo thời gian thực[cite: 1].")

    col_t2_src, col_t2_tgt, _ = st.columns([2, 2, 1])
    with col_t2_src:
        src_lang_name_t2 = st.selectbox("Ngôn ngữ nói (Mic):", list(LANG_OPTIONS.keys()), index=0, key="t2_src")
    with col_t2_tgt:
        tgt_lang_name_t2 = st.selectbox("Ngôn ngữ dịch out:", list(LANG_OPTIONS.keys()), index=1, key="t2_tgt")

    lang_code_js = "vi-VN" if LANG_OPTIONS[src_lang_name_t2] == "vi" else "en-US"
    tgt_lang_code = LANG_OPTIONS[tgt_lang_name_t2]
    src_lang_code = LANG_OPTIONS[src_lang_name_t2]

    st.write("---")

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
                color: #28a745;
            }}
            .cabin-grid {{
                display: flex;
                gap: 15px;
                margin-top: 15px;
            }}
            .cabin-panel {{
                flex: 1;
                background: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 15px;
                text-align: left;
                max-height: 250px;
                overflow-y: auto;
            }}
            .panel-title {{
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 8px;
                border-bottom: 1px solid #e9ecef;
                padding-bottom: 5px;
            }}
            .panel-content {{
                font-size: 16px;
                line-height: 1.5;
                word-wrap: break-word;
            }}
            #live-translated-text {{
                color: #28a745;
                font-weight: bold;
            }}
            #live-original-text {{
                color: #0056b3;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
    <div class="cabin-box">
        <div>
            <button id="start-btn" class="btn-control btn-start" onclick="startCabin()">🔴 KÍCH HOẠT CABIN TRỰC TIẾP</button>
            <button id="stop-btn" class="btn-control btn-stop" onclick="stopCabin()" disabled>⏹️ DỪNG CABIN</button>
        </div>
        <div id="status-badge">Trạng thái: Sẵn sàng kết nối Microphone...</div>
        
        <div class="cabin-grid">
            <!-- Cột trái: Văn bản dịch -->
            <div class="cabin-panel">
                <div class="panel-title" style="color: #28a745;">🌐 Bản dịch Cabin (Realtime)</div>
                <div id="live-translated-text" class="panel-content">[Đang chờ bản dịch...]</div>
            </div>
            <!-- Cột phải: Văn bản gốc -->
            <div class="cabin-panel">
                <div class="panel-title" style="color: #0056b3;">🎙️ Phát biểu Gốc (Mic)</div>
                <div id="live-original-text" class="panel-content">[Chưa có giọng nói...]</div>
            </div>
        </div>
    </div>

    <script>
        var recognition;
        var isRunning = false;

        async function quickTranslate(text) {{
            try {{
                let url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={src_lang_code}&tl={tgt_lang_code}&dt=t&q=" + encodeURIComponent(text);
                let response = await fetch(url);
                let data = await response.json();
                let translated = data[0].map(item => item[0]).join("");
                return translated;
            }} catch(e) {{
                return "[Lỗi dịch realtime]";
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
                document.getElementById('status-badge').innerText = '🟢 Cabin đang mở mic liên tục (Song song đuổi theo người nói)...';
                document.getElementById('start-btn').disabled = true;
                document.getElementById('stop-btn').disabled = false;
            }};

            recognition.onresult = async function(event) {{
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
                    let origBox = document.getElementById('live-original-text');
                    origBox.innerText = currentSpoken;
                    origBox.scrollTop = origBox.scrollHeight;
                    
                    let translatedResult = await quickTranslate(currentSpoken);
                    let transBox = document.getElementById('live-translated-text');
                    transBox.innerText = translatedResult;
                    transBox.scrollTop = transBox.scrollHeight;
                }}
            }};

            recognition.onend = function() {{
                if (isRunning) {{
                    try {{ recognition.start(); }} catch (e) {{}}
                }} else {{
                    document.getElementById('status-badge').innerText = '⏹️ Đã dừng hệ thống cabin.';
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;
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
            if (recognition) {{ recognition.stop(); }}
        }}
    </script>
    </body>
    </html>
    """

    components.html(cabin_html_code, height=350)
