import time
import json
import asyncio
import urllib.parse
import urllib.request
import textwrap
import streamlit as st
import streamlit.components.v1 as components
from deep_translator import GoogleTranslator
import edge_tts

st.set_page_config(page_title="AI Translate Cabin Pro", layout="wide")

st.markdown("""
<style>
    h1, h2, h3, h4, h5, h6, 
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
    }
    
    .stSelectbox label p, .stTextArea label p, .stSlider label p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
        font-weight: bold !important;
    }
    
    .stButton button p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
    }

    /* Thanh Tab Menu màu xanh đồng bộ, hỗ trợ cuộn ngang trên điện thoại */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0d6efd;
        padding: 6px 8px 0px 8px;
        border-radius: 8px 8px 0px 0px;
        gap: 6px;
        border-bottom: 2px solid #0a58ca;
        overflow-x: auto;
        white-space: nowrap;
        flex-wrap: nowrap;
    }

    .stTabs button[data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.15);
        color: #ffffff !important;
        border-radius: 6px 6px 0px 0px;
        padding: 10px 16px;
        border: none !important;
        flex-shrink: 0;
        transition: all 0.25s ease;
    }

    .stTabs button[data-baseweb="tab"]:hover {
        background-color: rgba(255, 255, 255, 0.3);
    }

    .stTabs button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0d6efd !important;
        box-shadow: 0 -2px 6px rgba(0,0,0,0.1);
    }

    .stTabs button[data-baseweb="tab"] p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 14px !important;
        font-weight: bold !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        border-top: none;
        border-radius: 0px 0px 8px 8px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    .translated-box {
        background-color: #e8f5e9;
        border: 1px solid #c8e6c9;
        border-radius: 8px;
        padding: 14px;
        min-height: 220px;
        max-height: 350px;
        overflow-y: auto;
        color: #1b5e20;
        font-size: 15px;
        line-height: 1.6;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

LANG_OPTIONS = {
    "VN Tiếng Việt": "vi",
    "us Tiếng Anh (Mỹ)": "en",
    "gb Tiếng Anh (Anh)": "en",
    "cn Tiếng Trung": "zh-CN",
    "jp Tiếng Nhật": "ja",
    "kr Tiếng Hàn": "ko",
    "fr Tiếng Pháp": "fr",
    "de Tiếng Đức": "de",
    "es Tiếng Tây Ban Nha": "es",
    "it Tiếng Ý": "it",
    "ru Tiếng Nga": "ru",
    "th Tiếng Thái": "th"
}

VOICE_MAP = {
    "us Nam - Anh-Mỹ (Guy - Trầm ấm)": "en-US-GuyNeural",
    "us Nữ - Anh-Mỹ (Jenny - Truyền cảm)": "en-US-JennyNeural",
    "vn Nam - Tiếng Việt (Nam Minh)": "vi-VN-NamMinhNeural",
    "vn Nữ - Tiếng Việt (Hoài My)": "vi-VN-HoaiMyNeural"
}

# --- TAB 1 CORE (KHÓA CỨNG) ---
@st.cache_data(show_spinner=False, ttl=3600)
def translate_stable(text, src_code, tgt_code):
    if not text.strip():
        return ""
    src = "zh-CN" if src_code.lower() == "zh-cn" else src_code
    tgt = "zh-CN" if tgt_code.lower() == "zh-cn" else tgt_code
    paragraphs = text.split('\n')
    final_translated = []
    for p in paragraphs:
        if not p.strip():
            final_translated.append("")
            continue
        chunks = textwrap.wrap(p, width=1200, replace_whitespace=False)
        p_trans = ""
        for chunk in chunks:
            success = False
            try:
                url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl={src}&tl={tgt}&q={urllib.parse.quote(chunk)}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    p_trans += (" ".join(data) if isinstance(data, list) else str(data)) + " "
                    success = True
            except Exception:
                pass
            if not success:
                try:
                    url2 = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src}&tl={tgt}&dt=t&q={urllib.parse.quote(chunk)}"
                    req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req2, timeout=8) as response2:
                        data2 = json.loads(response2.read().decode('utf-8'))
                        p_trans += "".join([item[0] for item in data2[0] if item[0]]) + " "
                        success = True
                except Exception:
                    p_trans += "[Lỗi dịch đoạn này] "
            time.sleep(0.1)
        final_translated.append(p_trans.strip())
    return "\n".join(final_translated)

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

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("Đăng nhập Hệ thống Cabin Phiên dịch")
    pwd_input = st.text_input("Nhập mật khẩu truy cập:", type="password")
    if st.button("Đăng nhập"):
        if pwd_input:
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

tab1, tab2, tab3 = st.tabs([
    "Dịch văn bản & Hội thoại", 
    "Cabin Phiên dịch Trực tiếp",
    "Học Tiếng Anh cùng AI"
])

# ==============================================================================
# TAB 1: BỐ CỤC 2 CỘT NGANG HÀNG
# ==============================================================================
with tab1:
    st.subheader("Dịch văn bản & Hội thoại chuyên sâu")
    col_t1_left, col_t1_right = st.columns(2)
    
    with col_t1_left:
        src_lang_name_t1 = st.selectbox("Ngôn ngữ nguồn:", list(LANG_OPTIONS.keys()), index=0, key="t1_src")
        input_text = st.text_area("Nhập văn bản cần dịch:", height=220, placeholder="Dán văn bản cần dịch vào đây...", key="t1_input_text")
        translate_clicked = st.button("Dịch ngay", key="btn_tab1", type="primary", use_container_width=True)

    with col_t1_right:
        tgt_lang_name_t1 = st.selectbox("Ngôn ngữ đích:", list(LANG_OPTIONS.keys()), index=1, key="t1_tgt")
        st.markdown('<p style="font-family: \'Times New Roman\', serif; font-size: 13px; font-weight: bold; margin-bottom: 6px;">Kết quả dịch:</p>', unsafe_allow_html=True)
        result_display = st.session_state.get("last_translation", "")
        if result_display:
            st.markdown(f'<div class="translated-box">{result_display}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="translated-box" style="background-color: #f8f9fa; border-color: #dee2e6; color: #6c757d; font-style: italic;">Bản dịch sẽ hiển thị ngang hàng tại đây...</div>', unsafe_allow_html=True)

    if translate_clicked:
        if input_text.strip():
            with st.spinner("Đang dịch thuật văn bản..."):
                src_code_t1 = LANG_OPTIONS[src_lang_name_t1]
                tgt_code_t1 = LANG_OPTIONS[tgt_lang_name_t1]
                res_text = translate_stable(input_text, src_code_t1, tgt_code_t1)
                st.session_state["last_translation"] = res_text
                st.rerun()
        else:
            st.warning("Vui lòng nhập văn bản cần dịch.")

    if "last_translation" in st.session_state and st.session_state["last_translation"]:
        st.markdown("---")
        st.markdown("### Cài đặt Âm thanh & Tải về:")
        col_v_sel, col_r_sel = st.columns(2)
        with col_v_sel:
            voice_t1_label = st.selectbox("Chọn giọng đọc:", list(VOICE_MAP.keys()), key="t1_voice_dynamic")
        with col_r_sel:
            speed_option = st.slider("Tốc độ đọc (x lần):", min_value=0.5, max_value=2.0, value=1.0, step=0.1, key="t1_speed_dynamic")

        audio_file = "translated_speech.mp3"
        if create_mp3(st.session_state["last_translation"], voice_t1_label, speed_option, audio_file):
            try:
                with open(audio_file, "rb") as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button("Tải xuống file MP3", data=audio_bytes, file_name="phien_dich_ai.mp3", mime="audio/mp3", key="download_mp3_btn")
            except Exception:
                pass

# ==============================================================================
# TAB 2: CABIN PHIÊN DỊCH TRỰC TIẾP
# ==============================================================================
with tab2:
    st.subheader("Phiên dịch Hội nghị Trực tiếp (Cabin Song Song)")
    col_t2_src, col_t2_tgt, _ = st.columns([2, 2, 1])
    with col_t2_src:
        src_lang_name_t2 = st.selectbox("Ngôn ngữ nói (Mic):", list(LANG_OPTIONS.keys()), index=0, key="t2_src")
    with col_t2_tgt:
        tgt_lang_name_t2 = st.selectbox("Ngôn ngữ dịch out:", list(LANG_OPTIONS.keys()), index=1, key="t2_tgt")

    src_code_val = LANG_OPTIONS[src_lang_name_t2]
    tgt_code_val = LANG_OPTIONS[tgt_lang_name_t2]
    lang_code_js = "vi-VN" if src_code_val == "vi" else "en-US"

    st.write("---")

    cabin_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            .cabin-box { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 12px; padding: 15px; text-align: center; }
            .btn-control { font-family: 'Times New Roman', Times, serif !important; padding: 12px 24px; font-size: 14px !important; font-weight: bold; border-radius: 8px; border: none; cursor: pointer; margin: 5px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .btn-start { background-color: #0d6efd; }
            .btn-stop { background-color: #dc3545; }
            #status-badge { font-family: 'Times New Roman', Times, serif !important; margin-top: 10px; font-weight: bold; font-size: 13px !important; color: #0d6efd; }
            .cabin-grid { display: flex; flex-direction: row; gap: 15px; margin-top: 15px; }
            .cabin-panel { flex: 1; background: #ffffff; border: 1px solid #ced4da; border-radius: 8px; padding: 15px; text-align: left; height: 480px; overflow-y: auto; box-shadow: inset 0 0 5px rgba(0,0,0,0.05); }
            .panel-title { font-family: 'Times New Roman', Times, serif !important; font-weight: bold; font-size: 14px !important; margin-bottom: 10px; border-bottom: 1px solid #e9ecef; padding-bottom: 5px; }
            .panel-content { font-size: 16px; line-height: 1.6; word-wrap: break-word; }
            @media (max-width: 768px) { .cabin-grid { flex-direction: column; } .cabin-panel { height: 280px; } }
        </style>
    </head>
    <body>
    <div class="cabin-box">
        <div>
            <button id="start-btn" class="btn-control btn-start" onclick="startCabin()">KÍCH HOẠT CABIN TRỰC TIẾP</button>
            <button id="stop-btn" class="btn-control btn-stop" onclick="stopCabin()" disabled>DỪNG CABIN</button>
        </div>
        <div id="status-badge">Trạng thái: Sẵn sàng kết nối Microphone...</div>
        <div class="cabin-grid">
            <div class="cabin-panel" id="scroll-trans">
                <div class="panel-title">Bản dịch Cabin (__TGT_NAME__)</div>
                <div id="live-translated-text" class="panel-content"></div>
            </div>
            <div class="cabin-panel" id="scroll-orig">
                <div class="panel-title">Phát biểu Gốc (__SRC_NAME__)</div>
                <div id="live-original-text" class="panel-content"></div>
            </div>
        </div>
    </div>
    <script>
        var recognition;
        var isRunning = false;
        var origSegments = [];
        var transSegments = [];
        var currentSpeechBuffer = "";
        var pauseTimer = null;
        var interimTimer = null;
        var sourceLang = '__SRC_CODE__';
        var targetLang = '__TGT_CODE__';

        function scrollToBottom() {
            let pTrans = document.getElementById('scroll-trans');
            let pOrig = document.getElementById('scroll-orig');
            if(pTrans) pTrans.scrollTop = pTrans.scrollHeight;
            if(pOrig) pOrig.scrollTop = pOrig.scrollHeight;
        }

        async function fetchTranslation(text) {
            if (!text || text.trim() === "") return "";
            let chunk = text.length > 800 ? text.substring(text.length - 800) : text;
            let q = encodeURIComponent(chunk);
            try {
                let res = await fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=${sourceLang}&tl=${targetLang}&q=${q}`);
                if (res.ok) {
                    let data = await res.json();
                    return Array.isArray(data) ? data.join(" ") : data;
                }
            } catch(e) {}
            try {
                let res2 = await fetch(`https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sourceLang}&tl=${targetLang}&dt=t&q=${q}`);
                if (res2.ok) {
                    let data2 = await res2.json();
                    return data2[0].map(item => item[0]).join("");
                }
            } catch(e) {}
            return "";
        }

        function commitSentence(sentence) {
            let cleanOrig = sentence.trim();
            if (!cleanOrig) return;
            cleanOrig = cleanOrig.charAt(0).toUpperCase() + cleanOrig.slice(1);
            if (!cleanOrig.match(/[.!?]$/)) cleanOrig += ".";
            if (origSegments.length > 0 && origSegments[origSegments.length - 1] === cleanOrig) {
                currentSpeechBuffer = "";
                return;
            }
            let idx = origSegments.length;
            origSegments.push(cleanOrig);
            transSegments.push("[Đang dịch...]");
            currentSpeechBuffer = "";
            renderUI("", "");

            fetchTranslation(cleanOrig).then(translated => {
                let cleanTrans = translated.trim();
                if (cleanTrans) {
                    cleanTrans = cleanTrans.charAt(0).toUpperCase() + cleanTrans.slice(1);
                    if (!cleanTrans.match(/[.!?]$/)) cleanTrans += ".";
                } else {
                    cleanTrans = cleanOrig;
                }
                transSegments[idx] = cleanTrans;
                renderUI("", "");
            });
        }

        function renderUI(interimText = "", interimTransText = "") {
            let origHTML = "";
            let transHTML = "";
            for (let i = 0; i < origSegments.length; i++) {
                origHTML += "<span style='color: #0056b3; font-weight: 500; display: block; margin-bottom: 12px;'>" + origSegments[i] + "</span>";
                let t = transSegments[i];
                let color = t.includes("[Đang dịch") ? "#888888" : "#28a745";
                let weight = t.includes("[Đang dịch") ? "normal" : "bold";
                transHTML += "<span style='color: " + color + "; font-weight: " + weight + "; display: block; margin-bottom: 12px;'>" + t + "</span>";
            }
            let origBox = document.getElementById('live-original-text');
            let transBox = document.getElementById('live-translated-text');
            origBox.innerHTML = interimText.trim() !== "" ? origHTML + "<span style='color: #888888; font-style: italic;'>" + interimText + "</span>" : origHTML;
            transBox.innerHTML = interimTransText.trim() !== "" ? transHTML + "<span style='color: #888888; font-style: italic;'>" + interimTransText + "</span>" : transHTML;
            scrollToBottom();
        }

        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            document.getElementById('status-badge').innerText = 'Trình duyệt không hỗ trợ Web Speech API. Hãy dùng Google Chrome hoặc Safari!';
        } else {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = '__LANG_JS__';

            recognition.onstart = function() {
                isRunning = true;
                currentSpeechBuffer = "";
                document.getElementById('status-badge').innerText = 'Trạng thái: Cabin đang mở mic liên tục...';
                document.getElementById('start-btn').disabled = true;
                document.getElementById('stop-btn').disabled = false;
            };

            recognition.onresult = function(event) {
                clearTimeout(pauseTimer);
                let latestText = "";
                let isFinalChunk = false;
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    latestText += event.results[i][0].transcript;
                    if (event.results[i].isFinal) isFinalChunk = true;
                }
                currentSpeechBuffer = latestText.trim();
                if (isFinalChunk && currentSpeechBuffer) {
                    commitSentence(currentSpeechBuffer);
                    return;
                }
                if (currentSpeechBuffer) {
                    renderUI(currentSpeechBuffer);
                    clearTimeout(interimTimer);
                    interimTimer = setTimeout(async () => {
                        let t_interim = await fetchTranslation(currentSpeechBuffer);
                        if (t_interim) renderUI(currentSpeechBuffer, t_interim.trim());
                    }, 120);
                    let wordCount = currentSpeechBuffer.split(/\\s+/).length;
                    let timeoutDuration = wordCount > 10 ? 800 : 1200;
                    pauseTimer = setTimeout(() => {
                        if (currentSpeechBuffer) {
                            commitSentence(currentSpeechBuffer);
                            try { recognition.stop(); } catch(e) {}
                        }
                    }, timeoutDuration);
                }
            };

            recognition.onend = function() {
                if (isRunning) {
                    try { recognition.start(); } catch (e) {}
                } else {
                    document.getElementById('status-badge').innerText = 'Trạng thái: Đã dừng hệ thống cabin.';
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;
                }
            };
        }

        function startCabin() {
            if (recognition) {
                isRunning = true;
                origSegments = [];
                transSegments = [];
                currentSpeechBuffer = "";
                try { recognition.start(); } catch (e) {}
            }
        }

        function stopCabin() {
            isRunning = false;
            clearTimeout(pauseTimer);
            if (currentSpeechBuffer) commitSentence(currentSpeechBuffer);
            if (recognition) recognition.stop();
        }
    </script>
    </body>
    </html>
    """

    cabin_html_code = (cabin_template
        .replace("__TGT_NAME__", tgt_lang_name_t2)
        .replace("__SRC_NAME__", src_lang_name_t2)
        .replace("__SRC_CODE__", src_code_val)
        .replace("__TGT_CODE__", tgt_code_val)
        .replace("__LANG_JS__", lang_code_js)
    )
    components.html(cabin_html_code, height=720, scrolling=True)

# ==============================================================================
# TAB 3: HỌC TIẾNG ANH CÙNG AI (BÀI GIẢNG & KỊCH BẢN + TẢI FILE WORD + HỘI THOẠI)
# ==============================================================================
with tab3:
    st.subheader("Hệ thống Học Tiếng Anh & Soạn Kịch bản Giảng dạy cùng AI")

    english_tutor_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #f4f6f9;
                margin: 0;
                padding: 8px;
                color: #212529;
            }
            /* Menu xanh 5 chức năng co giãn mượt trên PC & Mobile */
            .blue-menu-bar {
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                background-color: #0d6efd;
                border-radius: 8px;
                padding: 5px;
                gap: 5px;
                margin-bottom: 12px;
                box-shadow: 0 3px 8px rgba(13, 110, 253, 0.25);
            }
            @media (max-width: 900px) {
                .blue-menu-bar {
                    grid-template-columns: repeat(2, 1fr);
                }
            }
            .menu-item {
                padding: 10px 10px;
                border: none;
                border-radius: 6px;
                background-color: transparent;
                color: #ffffff;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
                text-align: center;
                transition: all 0.2s ease;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .menu-item:hover { background-color: rgba(255, 255, 255, 0.2); }
            .menu-item.active {
                background-color: #ffffff;
                color: #0d6efd;
                box-shadow: 0 2px 6px rgba(0,0,0,0.12);
            }
            .arrow-icon { font-size: 10px; transition: transform 0.2s ease; margin-left: 4px; }
            .menu-item.active .arrow-icon { transform: rotate(180deg); }

            .dropdown-panel {
                background: #ffffff;
                border: 1px solid #cfe2ff;
                border-top: 4px solid #0d6efd;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                display: none;
            }
            .dropdown-panel.active { display: block; }

            .topic-control-box {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 15px;
            }
            .input-group { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
            .input-group:last-child { margin-bottom: 0; }
            input[type="text"], select {
                flex: 1;
                min-width: 180px;
                padding: 10px 12px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
            }
            .btn-blue {
                padding: 10px 16px;
                border: none;
                border-radius: 6px;
                background-color: #0d6efd;
                color: white;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
            }
            .btn-blue:hover { background-color: #0b5ed7; }
            .btn-outline-blue {
                padding: 8px 12px;
                border: 1px solid #0d6efd;
                border-radius: 6px;
                background-color: #ffffff;
                color: #0d6efd;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
            }
            .btn-dark-blue {
                padding: 8px 12px;
                border: none;
                border-radius: 6px;
                background-color: #084298;
                color: #ffffff;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
            }
            .btn-word {
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                background-color: #198754;
                color: #ffffff;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
                box-shadow: 0 2px 5px rgba(25, 135, 84, 0.3);
            }
            .btn-word:hover { background-color: #157347; }

            /* Khung hiển thị Bài viết / Kịch bản có thanh trượt kéo qua lại, lên xuống */
            .lecture-scroll-box {
                width: 100%;
                height: 430px;
                overflow: auto;
                border: 1px solid #b6d4fe;
                border-radius: 8px;
                background-color: #ffffff;
                padding: 18px;
                box-shadow: inset 0 0 6px rgba(0,0,0,0.04);
                font-family: 'Times New Roman', Times, serif;
            }
            .lecture-inner-content {
                min-width: 680px; /* Đảm bảo có thanh trượt ngang trên màn hình hẹp để đọc rõ bảng/cột */
                line-height: 1.65;
                font-size: 15px;
            }
            .lecture-title {
                font-size: 18px;
                font-weight: bold;
                color: #084298;
                border-bottom: 2px solid #0d6efd;
                padding-bottom: 6px;
                margin-bottom: 14px;
                text-transform: uppercase;
            }
            .lecture-section {
                margin-bottom: 16px;
                padding: 12px;
                background: #f8f9fa;
                border-left: 4px solid #0d6efd;
                border-radius: 4px;
            }
            .sec-heading {
                font-weight: bold;
                color: #0d6efd;
                font-size: 15px;
                margin-bottom: 6px;
            }
            .sec-en {
                color: #111111;
                font-size: 15px;
                margin-bottom: 6px;
            }
            .sec-vi {
                color: #495057;
                font-style: italic;
                font-size: 14px;
                border-top: 1px dashed #ced4da;
                padding-top: 5px;
            }

            /* Bố cục Video Hội thoại */
            .video-layout { display: flex; gap: 15px; flex-direction: row; }
            @media (max-width: 768px) { .video-layout { flex-direction: column; } }
            .video-main { flex: 1.35; }
            .video-sidebar { flex: 1; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 14px; }

            .media-screen {
                background: linear-gradient(135deg, #0a2540 0%, #0d6efd 100%);
                color: white;
                border-radius: 10px;
                padding: 18px 14px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.15);
            }
            .wave-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid rgba(255,255,255,0.2);
                padding-bottom: 10px;
                margin-bottom: 12px;
                flex-wrap: wrap;
                gap: 6px;
            }
            .wave-bars { display: flex; align-items: center; gap: 4px; height: 22px; }
            .bar { width: 4px; height: 8px; background: #6ea8fe; border-radius: 2px; }
            .playing .bar { animation: soundWave 0.5s infinite alternate; }
            .playing .bar:nth-child(2) { animation-delay: 0.1s; }
            .playing .bar:nth-child(3) { animation-delay: 0.2s; }
            .playing .bar:nth-child(4) { animation-delay: 0.3s; }
            @keyframes soundWave {
                from { height: 6px; background: #6ea8fe; }
                to { height: 22px; background: #ffffff; }
            }

            .dialogue-container {
                background: rgba(0, 0, 0, 0.35);
                border-radius: 8px;
                padding: 12px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .turn-box {
                background: rgba(255, 255, 255, 0.12);
                border-left: 3px solid #6ea8fe;
                padding: 10px 12px;
                border-radius: 6px;
                text-align: left;
            }
            .turn-box.role-b { background: rgba(255, 255, 255, 0.2); border-left: 3px solid #ffc107; }
            .role-label {
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
                color: #9ec5fe;
                margin-bottom: 3px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .role-b .role-label { color: #ffe69c; }
            .sub-en { font-size: 15px; font-weight: bold; color: #ffffff; line-height: 1.45; }
            .sub-vi { font-size: 13px; color: #cfe2ff; margin-top: 4px; font-style: italic; }
            .sub-hidden { filter: blur(5px); user-select: none; opacity: 0.35; }
            .controls-row { display: flex; gap: 6px; justify-content: center; margin-top: 14px; flex-wrap: wrap; }

            .vocab-card { background: #ffffff; border-left: 4px solid #0d6efd; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
            .grammar-card { background: #e7f1ff; border: 1px solid #b6d4fe; border-radius: 6px; padding: 12px; margin-top: 10px; }
            .word-header { font-size: 20px; font-weight: bold; color: #0d6efd; margin-bottom: 4px; }
            .phonetic { color: #6c757d; font-size: 14px; font-family: monospace; margin-bottom: 10px; }
            .meaning-box { background: #f1f8ff; border-left: 4px solid #0d6efd; padding: 12px; border-radius: 6px; margin-bottom: 12px; }
            .sample-sentence-box { background: #f8f9fa; border: 1px solid #dee2e6; padding: 14px; border-radius: 8px; font-size: 16px; font-weight: 500; margin-bottom: 14px; line-height: 1.5; }
            .score-circle { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px; margin-top: 10px; }
            .word-correct { color: #198754; font-weight: bold; }
            .word-wrong { color: #dc3545; text-decoration: line-through; }
            .chat-window { height: 280px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; background: #fdfdfd; margin-bottom: 10px; }
            .msg-user { background: #0d6efd; color: white; padding: 9px 12px; border-radius: 12px 12px 2px 12px; max-width: 85%; margin-left: auto; margin-bottom: 8px; font-size: 14px; }
            .msg-ai { background: #e9ecef; color: #212529; padding: 9px 12px; border-radius: 12px 12px 12px 2px; max-width: 90%; margin-right: auto; margin-bottom: 8px; font-size: 14px; line-height: 1.45; }
        </style>
    </head>
    <body>
        <!-- THANH MENU XANH 5 MỤC CHỨC NĂNG -->
        <div class="blue-menu-bar">
            <button class="menu-item active" onclick="openPanel('lecture', this)">
                <span>Bài viết & Kịch bản Giảng</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('video', this)">
                <span>Video & Hội thoại</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('dict', this)">
                <span>Từ điển & Phát âm</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('speak', this)">
                <span>Luyện Nói & Chấm điểm</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('chat', this)">
                <span>Gia sư Song ngữ</span>
                <span class="arrow-icon">▼</span>
            </button>
        </div>

        <!-- PANEL 1: BÀI VIẾT / KỊCH BẢN GIẢNG BÀI + TẢI FILE WORD -->
        <div id="panel-lecture" class="dropdown-panel active">
            <div class="topic-control-box">
                <div class="input-group">
                    <select id="preset-lecture-select" onchange="loadPresetLecture()">
                        <option value="ttest1">Chủ đề mẫu 1: Bài giảng Kiểm định t-test 1 mẫu (One-Sample t-Test)</option>
                        <option value="logistic">Chủ đề mẫu 2: Bài giảng Hồi quy Logistic Đa biến (Multivariate Logistic Regression)</option>
                        <option value="rct">Chủ đề mẫu 3: Thiết kế Thử nghiệm Lâm sàng Ngẫu nhiên Có đối chứng (RCT)</option>
                    </select>
                </div>
                <div class="input-group">
                    <input type="text" id="custom-lecture-topic" placeholder="Hoặc nhập chủ đề bài giảng / bài viết bạn cần soạn (VD: bài giảng về t test 1 mẫu, phân tích phương sai ANOVA...)" onkeypress="if(event.key==='Enter') generateLectureScript()">
                    <button class="btn-blue" id="btn-gen-lecture" onclick="generateLectureScript()">Soạn bài viết / Kịch bản</button>
                </div>
            </div>

            <!-- Thanh công cụ điều khiển bài viết & Nút tải Word -->
            <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
                <button class="btn-word" onclick="downloadLectureWord()">Tải về file Word (.doc)</button>
                <button class="btn-blue" onclick="playFullLecture(1.0)">Nghe kịch bản (1.0x)</button>
                <button class="btn-dark-blue" onclick="playFullLecture(0.65)">Nghe chậm (0.65x)</button>
                <button class="btn-blue" style="background-color: #dc3545;" onclick="stopClip()">Dừng đọc</button>
                <button class="btn-outline-blue" id="btn-toggle-lec-vi" onclick="toggleLectureVi()">Ẩn bản dịch tiếng Việt</button>
            </div>

            <!-- Khung hiển thị bài viết dài có thanh cuộn lên xuống và kéo qua lại -->
            <div class="lecture-scroll-box" id="lecture-display-area">
                <!-- Nội dung kịch bản bài giảng sẽ render tại đây -->
            </div>
        </div>

        <!-- PANEL 2: XEM VIDEO / NGHE HỘI THOẠI NHẬP VAI THỰC TẾ -->
        <div id="panel-video" class="dropdown-panel">
            <div class="topic-control-box">
                <div class="input-group">
                    <select id="video-topic-select" onchange="changeVideoLesson()">
                        <option value="immigration">Chủ đề 1: Thủ tục Nhập cảnh & Hải quan Sân bay</option>
                        <option value="biostat">Chủ đề 2: Thống kê Y sinh & Nghiên cứu Lâm sàng</option>
                        <option value="pharma">Chủ đề 3: Dược lâm sàng & Tư vấn Thuốc</option>
                        <option value="conference">Chủ đề 4: Báo cáo tại Hội nghị Khoa học Quốc tế</option>
                        <option value="hotel">Chủ đề 5: Nhận phòng Khách sạn & Lưu trú Công tác</option>
                    </select>
                    <button class="btn-outline-blue" onclick="nextClipInTopic()">Đổi tình huống khác</button>
                </div>

                <div class="input-group">
                    <input type="text" id="custom-topic-input" placeholder="Tự nhập tình huống hội thoại (VD: khai báo hải quan, khám bệnh, phỏng vấn...)" onkeypress="if(event.key==='Enter') generateCustomDialogue()">
                    <button class="btn-blue" id="btn-gen-topic" onclick="generateCustomDialogue()">Tạo hội thoại thực tế</button>
                </div>
            </div>

            <div class="video-layout">
                <div class="video-main">
                    <div class="media-screen" id="media-player-box">
                        <div class="wave-header">
                            <span style="font-size: 12px; font-weight: bold; color: #9ec5fe;" id="clip-badge">TÌNH HUỐNG HỘI THOẠI 01</span>
                            <div class="wave-bars" id="wave-indicator">
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
                            </div>
                            <span style="font-size: 12px; color: #e2e3e5;" id="player-status">Sẵn sàng phát</span>
                        </div>

                        <div class="dialogue-container" id="subtitle-container"></div>

                        <div class="controls-row">
                            <button class="btn-blue" style="background-color: #198754;" onclick="playFullDialogue(1.0)">Nghe hội thoại (1.0x)</button>
                            <button class="btn-dark-blue" onclick="playFullDialogue(0.65)">Nghe chậm (0.65x)</button>
                            <button class="btn-blue" style="background-color: #dc3545;" onclick="stopClip()">Dừng phát</button>
                            <button class="btn-outline-blue" id="btn-toggle-sub" onclick="toggleSubtitle()">Ẩn phụ đề</button>
                        </div>
                    </div>
                </div>

                <div class="video-sidebar">
                    <div style="font-weight: bold; color: #0d6efd; font-size: 15px; margin-bottom: 10px; border-bottom: 1px solid #dee2e6; padding-bottom: 6px;">
                        Từ vựng trọng tâm trong tình huống
                    </div>
                    <div id="related-vocab-list"></div>

                    <div style="font-weight: bold; color: #084298; font-size: 15px; margin-top: 16px; margin-bottom: 8px; border-bottom: 1px solid #dee2e6; padding-bottom: 6px;">
                        Cấu trúc Ngữ pháp & Mẫu câu giao tiếp
                    </div>
                    <div id="related-grammar-box"></div>
                </div>
            </div>
        </div>

        <!-- PANEL 3: TỪ ĐIỂN AI & PHÁT ÂM -->
        <div id="panel-dict" class="dropdown-panel">
            <div class="input-group">
                <input type="text" id="dict-input" placeholder="Nhập từ vựng tiếng Anh (VD: hypothesis, degrees of freedom, null)..." onkeypress="if(event.key==='Enter') lookupWord()">
                <button class="btn-blue" onclick="lookupWord()">Tra cứu</button>
            </div>
            <div id="dict-result">
                <p style="color: #6c757d; font-style: italic;">Nhập một từ tiếng Anh bất kỳ để xem nghĩa tiếng Việt, phiên âm quốc tế (IPA), ví dụ ngữ cảnh và nghe giọng đọc chuẩn.</p>
            </div>
        </div>

        <!-- PANEL 4: LUYỆN NÓI & CHẤM ĐIỂM PHÁT ÂM -->
        <div id="panel-speak" class="dropdown-panel">
            <div class="input-group">
                <select id="topic-select" onchange="loadNextSentence()">
                    <option value="immigration">Chủ đề: Nhập cảnh & Hải quan Sân bay</option>
                    <option value="medical">Chủ đề: Y khoa & Nghiên cứu Khoa học</option>
                    <option value="academic">Chủ đề: Hội thảo & Thuyết trình Quốc tế</option>
                </select>
                <button class="btn-outline-blue" onclick="loadNextSentence()">Đổi câu mẫu khác</button>
            </div>
            <div class="sample-sentence-box">
                <div style="font-size: 12px; color: #0d6efd; font-weight: bold; margin-bottom: 4px;">CÂU MẪU LUYỆN ĐỌC:</div>
                <span id="target-sentence">The one-sample t-test compares the mean of a single sample to a known population mean.</span>
                <div style="margin-top: 10px;">
                    <button class="btn-blue" onclick="speakText(document.getElementById('target-sentence').innerText, 0.95)">Nghe mẫu chuẩn</button>
                    <button class="btn-outline-blue" onclick="speakText(document.getElementById('target-sentence').innerText, 0.65)">Nghe chậm</button>
                </div>
                <div id="target-vi" style="font-size: 14px; color: #555; margin-top: 8px; font-weight: normal; font-style: italic;">
                    (Kiểm định t một mẫu so sánh giá trị trung bình của một mẫu đơn lẻ với giá trị trung bình quần thể đã biết.)
                </div>
            </div>
            <button id="btn-record-eval" class="btn-blue" style="width: 100%; padding: 13px; font-size: 14px;" onclick="startPronunciationCheck()">
                BẤM ĐỂ ĐỌC CÂU TRÊN VÀ CHẤM ĐIỂM AI
            </button>
            <div id="speak-feedback" style="margin-top: 15px;"></div>
        </div>

        <!-- PANEL 5: GIA SƯ HỘI THOẠI SONG NGỮ -->
        <div id="panel-chat" class="dropdown-panel">
            <div class="chat-window" id="chat-box">
                <div class="msg-ai">
                    <b>AI English Tutor:</b> Xin chào! Hãy nhập câu tiếng Việt bạn muốn diễn đạt trong bài giảng/hội nghị, hoặc nhập câu tiếng Anh để tôi kiểm tra và chỉnh sửa tự nhiên hơn.
                </div>
            </div>
            <div class="input-group">
                <input type="text" id="chat-input" placeholder="Nhập câu tiếng Việt hoặc tiếng Anh..." onkeypress="if(event.key==='Enter') sendTutorMessage()">
                <button class="btn-blue" onclick="sendTutorMessage()">Gửi AI</button>
            </div>
        </div>

        <script>
            function openPanel(panelId, btn) {
                document.querySelectorAll('.dropdown-panel').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));
                document.getElementById('panel-' + panelId).classList.add('active');
                btn.classList.add('active');
                stopClip();
            }

            // =========================================================================
            // PHẦN 1: DỮ LIỆU & LOGIC BÀI VIẾT / KỊCH BẢN GIẢNG BÀI + XUẤT WORD
            // =========================================================================
            const LECTURE_BANK = {
                ttest1: {
                    title: "LECTURE SCRIPT: ONE-SAMPLE T-TEST IN BIOSTATISTICS (BÀI GIẢNG KIỂM ĐỊNH T 1 MẪU)",
                    sections: [
                        {
                            heading: "1. Opening & Purpose (Mở đầu & Mục đích kiểm định)",
                            en: "Good morning everyone. Today, we will explore the One-Sample t-Test, one of the most fundamental parametric hypothesis tests in biostatistics. Simply put, we use a one-sample t-test when we want to determine whether the mean of a single sample differs significantly from a known or hypothesized population mean (denoted as mu-zero).",
                            vi: "Chào buổi sáng tất cả các bạn. Hôm nay, chúng ta sẽ tìm hiểu về Kiểm định t một mẫu (One-Sample t-Test), một trong những kiểm định giả thuyết tham số cơ bản nhất trong thống kê y sinh. Nói một cách đơn giản, chúng ta sử dụng kiểm định t một mẫu khi muốn xác định liệu giá trị trung bình của một mẫu đơn lẻ có khác biệt có ý nghĩa thống kê so với giá trị trung bình quần thể đã biết hoặc giả định (ký hiệu là mu-0) hay không."
                        },
                        {
                            heading: "2. Key Assumptions (Các giả định cốt lõi cần kiểm tra)",
                            en: "Before running this test in SPSS or Stata, we must verify three critical assumptions: First, the dependent variable must be continuous (measured on an interval or ratio scale). Second, the observations must be independent of one another. Third, the data should follow an approximately normal distribution, especially when the sample size is small (n < 30).",
                            vi: "Trước khi chạy kiểm định này trên SPSS hoặc Stata, chúng ta phải kiểm tra ba giả định quan trọng: Thứ nhất, biến phụ thuộc phải là biến liên tục (đo lường trên thang đo khoảng hoặc tỷ lệ). Thứ hai, các quan sát phải độc lập với nhau. Thứ ba, dữ liệu cần tuân theo phân phối xấp xỉ chuẩn, đặc biệt là khi cỡ mẫu nhỏ (n < 30)."
                        },
                        {
                            heading: "3. Hypotheses & Formula (Cặp giả thuyết & Công thức tính toán)",
                            en: "In hypothesis testing, we set up two competing statements. The null hypothesis (H0) states that the sample mean is equal to the hypothesized population mean. The alternative hypothesis (H1) states that there is a significant difference. The test statistic t is calculated as: t = (x-bar minus mu-zero) divided by (s divided by the square root of n), with n minus 1 degrees of freedom.",
                            vi: "Trong kiểm định giả thuyết, chúng ta thiết lập hai phát biểu đối lập. Giả thuyết không (H0) phát biểu rằng trung bình mẫu bằng với trung bình quần thể giả định. Giả thuyết đối (H1) phát biểu rằng có sự khác biệt có ý nghĩa. Trị số thống kê t được tính bằng công thức: t = (x trung bình trừ mu-0) chia cho (độ lệch chuẩn s chia căn bậc hai của n), với bậc tự do là n trừ 1."
                        },
                        {
                            heading: "4. Clinical Example & Interpretation (Ví dụ lâm sàng & Diễn giải kết quả)",
                            en: "For example, suppose the normal fasting blood glucose level in healthy adults is 90 mg/dL. We measure glucose levels in a sample of 25 patients taking a new medication and find a sample mean of 96 mg/dL. If our calculated p-value is less than the significance level alpha of 0.05, we reject the null hypothesis and conclude that the patients' average blood glucose differs significantly from the standard norm.",
                            vi: "Ví dụ, giả sử mức đường huyết lúc đói bình thường ở người trưởng thành khỏe mạnh là 90 mg/dL. Chúng ta đo đường huyết trên một mẫu gồm 25 bệnh nhân đang dùng một loại thuốc mới và thu được trung bình mẫu là 96 mg/dL. Nếu trị số p tính được nhỏ hơn mức ý nghĩa alpha là 0.05, chúng ta bác bỏ giả thuyết không và kết luận rằng mức đường huyết trung bình của nhóm bệnh nhân này khác biệt có ý nghĩa thống kê so với chuẩn bình thường."
                        }
                    ],
                    vocab: [
                        { word: "One-Sample t-Test", mean: "Kiểm định t một mẫu" },
                        { word: "Hypothesized population mean", mean: "Giá trị trung bình quần thể giả định" },
                        { word: "Null hypothesis (H0)", mean: "Giả thuyết không" },
                        { word: "Degrees of freedom (df)", mean: "Bậc tự do" },
                        { word: "Significance level (alpha)", mean: "Mức ý nghĩa thống kê" }
                    ]
                },
                logistic: {
                    title: "LECTURE SCRIPT: MULTIVARIATE LOGISTIC REGRESSION (BÀI GIẢNG HỒI QUY LOGISTIC ĐA BIẾN)",
                    sections: [
                        {
                            heading: "1. Introduction & When to Use (Mở đầu & Khi nào sử dụng)",
                            en: "Welcome to today's lecture on Multivariate Logistic Regression. Unlike linear regression, which predicts a continuous outcome, binary logistic regression is used when our dependent variable is dichotomous—meaning it has only two possible outcomes, such as cured versus not cured, or disease present versus absent.",
                            vi: "Chào mừng các bạn đến với bài giảng hôm nay về Hồi quy Logistic Đa biến. Không giống như hồi quy tuyến tính vốn dự báo một kết cục liên tục, hồi quy logistic nhị phân được sử dụng khi biến phụ thuộc của chúng ta là biến nhị giá—nghĩa là chỉ có hai kết cục có thể xảy ra, chẳng hạn như khỏi bệnh so với không khỏi bệnh, hoặc có bệnh so với không bệnh."
                        },
                        {
                            heading: "2. Controlling Confounders & Odds Ratio (Kiểm soát yếu tố gây nhiễu & Tỷ số chênh OR)",
                            en: "The primary advantage of a multivariate model is its ability to adjust for multiple confounding variables simultaneously. Instead of regression coefficients, we interpret the Adjusted Odds Ratio (aOR) along with its 95% confidence interval. An aOR greater than 1 indicates an increased risk, whereas an aOR less than 1 suggests a protective factor.",
                            vi: "Ưu điểm chính của mô hình đa biến là khả năng hiệu chỉnh đồng thời cho nhiều biến gây nhiễu. Thay vì các hệ số hồi quy thông thường, chúng ta diễn giải Tỷ số chênh hiệu chỉnh (aOR) cùng với khoảng tin cậy 95% của nó. Giá trị aOR lớn hơn 1 cho thấy nguy cơ tăng lên, trong khi aOR nhỏ hơn 1 gợi ý một yếu tố bảo vệ."
                        }
                    ],
                    vocab: [
                        { word: "Dichotomous outcome", mean: "Kết cục nhị giá (2 giá trị)" },
                        { word: "Adjusted Odds Ratio (aOR)", mean: "Tỷ số chênh đã hiệu chỉnh" },
                        { word: "Confounding variable", mean: "Biến gây nhiễu" },
                        { word: "Confidence interval (CI)", mean: "Khoảng tin cậy" }
                    ]
                },
                rct: {
                    title: "LECTURE SCRIPT: RANDOMIZED CONTROLLED TRIALS (THIẾT KẾ THỬ NGHIỆM LÂM SÀNG RCT)",
                    sections: [
                        {
                            heading: "1. Core Principles of RCT (Nguyên lý cốt lõi của RCT)",
                            en: "Randomized Controlled Trials, or RCTs, represent the highest level of primary clinical evidence. By randomly assigning participants into either an intervention group or a control group, randomization balances both known and unknown prognostic factors across groups at baseline.",
                            vi: "Thử nghiệm lâm sàng ngẫu nhiên có đối chứng, gọi tắt là RCT, đại diện cho mức độ bằng chứng lâm sàng nguyên phát cao nhất. Bằng cách phân bổ ngẫu nhiên người tham gia vào nhóm can thiệp hoặc nhóm chứng, việc ngẫu nhiên hóa giúp cân bằng cả các yếu tố tiên lượng đã biết và chưa biết giữa các nhóm tại thời điểm ban đầu."
                        },
                        {
                            heading: "2. Blinding & Intention-to-Treat (Làm mù & Phân tích theo ý định điều trị)",
                            en: "To minimize information bias, double-blinding is implemented so that neither the patients nor the clinicians know which treatment is being administered. Furthermore, data should be analyzed according to the Intention-to-Treat (ITT) principle to preserve the benefits of randomization.",
                            vi: "Để giảm thiểu sai số thông tin, kỹ thuật làm mù đôi được áp dụng để cả bệnh nhân lẫn bác sĩ lâm sàng đều không biết phương pháp điều trị nào đang được sử dụng. Hơn nữa, dữ liệu nên được phân tích theo nguyên tắc Ý định điều trị (ITT) nhằm bảo toàn lợi ích của việc phân bổ ngẫu nhiên."
                        }
                    ],
                    vocab: [
                        { word: "Randomization", mean: "Sự phân bổ ngẫu nhiên" },
                        { word: "Double-blinding", mean: "Làm mù đôi" },
                        { word: "Intention-to-Treat (ITT)", mean: "Phân tích theo ý định điều trị" }
                    ]
                }
            };

            let currentLectureObj = LECTURE_BANK["ttest1"];
            let isLectureViVisible = true;

            function renderLecture(lecObj) {
                currentLectureObj = lecObj;
                let area = document.getElementById('lecture-display-area');
                let viStyle = isLectureViVisible ? "" : "display: none;";

                let html = `<div class="lecture-inner-content">
                    <div class="lecture-title">${lecObj.title}</div>`;

                lecObj.sections.forEach((sec, idx) => {
                    html += `
                        <div class="lecture-section">
                            <div class="sec-heading" style="display:flex; justify-content:space-between; align-items:center;">
                                <span>${sec.heading}</span>
                                <button class="btn-outline-blue" style="padding:2px 8px; font-size:11px;" onclick="speakText('${sec.en.replace(/'/g, "\\'")}', 0.95)">Nghe phần này</button>
                            </div>
                            <div class="sec-en">${sec.en}</div>
                            <div class="sec-vi lec-vi-text" style="${viStyle}">${sec.vi}</div>
                        </div>
                    `;
                });

                if (lecObj.vocab && lecObj.vocab.length > 0) {
                    html += `<div style="margin-top:14px; padding:12px; background:#e7f1ff; border-radius:6px;">
                        <b style="color:#084298;">Thuật ngữ chuyên ngành trong bài giảng:</b>
                        <ul style="margin:6px 0 0 18px; padding:0;">`;
                    lecObj.vocab.forEach(v => {
                        html += `<li style="margin-bottom:4px;"><b>${v.word}:</b> ${v.mean}</li>`;
                    });
                    html += `</ul></div>`;
                }

                html += `</div>`;
                area.innerHTML = html;
            }

            function loadPresetLecture() {
                stopClip();
                let key = document.getElementById('preset-lecture-select').value;
                renderLecture(LECTURE_BANK[key]);
            }

            async function generateLectureScript() {
                let rawTopic = document.getElementById('custom-lecture-topic').value.trim();
                if (!rawTopic) {
                    alert("Vui lòng nhập chủ đề bài giảng hoặc bài viết bạn muốn tạo!");
                    return;
                }
                stopClip();
                let btn = document.getElementById('btn-gen-lecture');
                btn.innerText = "Đang biên soạn kịch bản...";
                btn.disabled = true;

                try {
                    let lower = rawTopic.toLowerCase();
                    // Nếu người dùng nhập liên quan đến t-test 1 mẫu -> Nạp ngay kịch bản chuẩn mực
                    if ((lower.includes("t test") || lower.includes("t-test")) && (lower.includes("1") || lower.includes("một") || lower.includes("one"))) {
                        renderLecture(LECTURE_BANK["ttest1"]);
                        return;
                    }
                    if (lower.includes("logistic")) {
                        renderLecture(LECTURE_BANK["logistic"]);
                        return;
                    }

                    // Tạo kịch bản giảng bài cho bất kỳ chủ đề nào người dùng nhập
                    let enTopic = rawTopic;
                    if (/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(rawTopic)) {
                        enTopic = await translateText(rawTopic, 'vi', 'en');
                    }

                    let rawSections = [
                        {
                            heading: "1. Introduction & Overview (Mở đầu & Tổng quan chủ đề)",
                            en: `Good morning colleagues and students. In today's session, we will examine ${enTopic}. Understanding the theoretical foundation and practical application of ${enTopic} is essential for rigorous academic research and evidence-based decision-making.`
                        },
                        {
                            heading: "2. Core Principles & Methodology (Nguyên lý cốt lõi & Phương pháp luận)",
                            en: `When applying ${enTopic}, we must carefully define our study objectives, verify all underlying assumptions, and select the most appropriate analytical framework. Paying close attention to methodological rigor ensures that our findings are both reliable and reproducible.`
                        },
                        {
                            heading: "3. Practical Application & Interpretation (Ứng dụng thực tế & Diễn giải kết quả)",
                            en: `Let us consider a practical scenario involving ${enTopic}. When interpreting the results, researchers should not rely solely on statistical significance, but also evaluate the clinical or practical relevance of the observed effects.`
                        },
                        {
                            heading: "4. Summary & Q&A Transition (Tổng kết & Chuyển sang thảo luận)",
                            en: `To summarize, ${enTopic} provides a structured approach to solving complex research questions. Thank you for your attention, and I now welcome any questions or comments from the audience.`
                        }
                    ];

                    let fullSections = [];
                    for (let s of rawSections) {
                        let viText = await translateText(s.en, 'en', 'vi');
                        fullSections.push({ heading: s.heading, en: s.en, vi: viText });
                    }

                    let words = enTopic.replace(/[^a-zA-Z\s]/g, "").split(/\s+/).filter(w => w.length >= 4);
                    let vocabList = [];
                    for (let w of words.slice(0, 4)) {
                        let cleanW = w.toLowerCase();
                        let meanVi = await translateText(cleanW, 'en', 'vi');
                        vocabList.push({ word: cleanW, mean: meanVi });
                    }
                    vocabList.push({ word: "methodological rigor", mean: "tính chặt chẽ về mặt phương pháp luận" });
                    vocabList.push({ word: "reproducible", mean: "có thể lặp lại / tái lập được kết quả" });

                    renderLecture({
                        title: `LECTURE SCRIPT & ARTICLE: ${enTopic.toUpperCase()} (${rawTopic.toUpperCase()})`,
                        sections: fullSections,
                        vocab: vocabList
                    });
                } catch (e) {
                    alert("Có lỗi khi tạo kịch bản, vui lòng thử lại!");
                } finally {
                    btn.innerText = "Soạn bài viết / Kịch bản";
                    btn.disabled = false;
                }
            }

            function toggleLectureVi() {
                isLectureViVisible = !isLectureViVisible;
                let btn = document.getElementById('btn-toggle-lec-vi');
                document.querySelectorAll('.lec-vi-text').forEach(el => {
                    el.style.display = isLectureViVisible ? "block" : "none";
                });
                btn.innerText = isLectureViVisible ? "Ẩn bản dịch tiếng Việt" : "Hiện bản dịch tiếng Việt";
            }

            function playFullLecture(rate) {
                if (!('speechSynthesis' in window)) return;
                stopClip();
                let sections = currentLectureObj.sections;
                isPlayingSequence = true;
                let idx = 0;

                function speakNextSec() {
                    if (!isPlayingSequence || idx >= sections.length) {
                        isPlayingSequence = false;
                        return;
                    }
                    let u = new SpeechSynthesisUtterance(sections[idx].en);
                    u.lang = 'en-US';
                    u.rate = rate;
                    u.onend = function() {
                        idx++;
                        setTimeout(speakNextSec, 400);
                    };
                    window.speechSynthesis.speak(u);
                }
                speakNextSec();
            }

            // XUẤT FILE MICROSOFT WORD (.DOC) CHUẨN TIMES NEW ROMAN
            function downloadLectureWord() {
                if (!currentLectureObj) return;
                let lec = currentLectureObj;

                let bodyHtml = `
                    <h2 style="text-align:center; color:#084298; font-family:'Times New Roman', serif;">${lec.title}</h2>
                    <hr/>
                `;

                lec.sections.forEach(sec => {
                    bodyHtml += `
                        <p style="font-weight:bold; color:#0d6efd; font-size:13pt; margin-top:12pt; margin-bottom:4pt;">${sec.heading}</p>
                        <p style="font-size:12pt; line-height:1.5; text-align:justify; margin-bottom:4pt;">${sec.en}</p>
                        <p style="font-size:11.5pt; font-style:italic; color:#333333; line-height:1.4; text-align:justify; margin-bottom:10pt;"><i>(Dịch nghĩa: ${sec.vi})</i></p>
                    `;
                });

                if (lec.vocab && lec.vocab.length > 0) {
                    bodyHtml += `<p style="font-weight:bold; color:#084298; font-size:13pt; margin-top:14pt;">KEY TERMINOLOGY (THUẬT NGỮ TRỌNG TÂM):</p><ul>`;
                    lec.vocab.forEach(v => {
                        bodyHtml += `<li style="font-size:12pt; margin-bottom:4pt;"><b>${v.word}:</b> ${v.mean}</li>`;
                    });
                    bodyHtml += `</ul>`;
                }

                let wordDocument = `
                    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
                    <head><meta charset='utf-8'><title>${lec.title}</title>
                    <style>body { font-family: 'Times New Roman', Times, serif; }</style>
                    </head>
                    <body>${bodyHtml}</body>
                    </html>
                `;

                let blob = new Blob(['\ufeff', wordDocument], { type: 'application/msword' });
                let url = URL.createObjectURL(blob);
                let link = document.createElement('a');
                link.href = url;
                link.download = 'Kich_Ban_Bai_Giang_AI.doc';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }

            // Khởi tạo bài giảng mặc định khi mở tab
            renderLecture(LECTURE_BANK["ttest1"]);

            // =========================================================================
            // PHẦN 2: HỘI THOẠI NHẬP VAI THỰC TẾ (GIỮ NGUYÊN BẢN ĐÃ CHẠY TỐT)
            // =========================================================================
            const DIALOGUE_BANK = {
                immigration: [
                    {
                        title: "Tình huống 1: Kiểm tra Hộ chiếu & Mục đích nhập cảnh",
                        turns: [
                            { role: "Immigration Officer (An ninh cửa khẩu)", en: "Good morning. May I see your passport and boarding pass, please? What is the purpose of your visit?", vi: "Chào buổi sáng. Vui lòng cho tôi xem hộ chiếu và thẻ lên máy bay. Mục đích chuyến đi của ông/bà là gì?" },
                            { role: "Passenger (Người nhập cảnh)", en: "Here you are. I am attending an international medical conference at the university for five days.", vi: "Đây ạ. Tôi đến tham dự một hội nghị y khoa quốc tế tại trường đại học trong 5 ngày." },
                            { role: "Immigration Officer (An ninh cửa khẩu)", en: "Where will you be staying, and do you have a return flight ticket?", vi: "Ông/bà sẽ lưu trú ở đâu và có vé máy bay khứ hồi chưa?" },
                            { role: "Passenger (Người nhập cảnh)", en: "I am staying at the Grand Hotel downtown. Here is my hotel reservation and return ticket.", vi: "Tôi ở tại khách sạn Grand ở trung tâm thành phố. Đây là xác nhận đặt phòng và vé khứ hồi của tôi." }
                        ],
                        vocab: [
                            { word: "immigration", ipa: "/ˌɪm.əˈɡreɪ.ʃən/", mean: "nhập cảnh, di trú" },
                            { word: "purpose of visit", ipa: "/ˈpɝː.pəs əv ˈvɪz.ɪt/", mean: "mục đích chuyến đi" },
                            { word: "boarding pass", ipa: "/ˈbɔːr.dɪŋ pæs/", mean: "thẻ lên máy bay" },
                            { word: "reservation", ipa: "/ˌrez.ɚˈveɪ.ʃən/", mean: "sự đặt chỗ trước" }
                        ],
                        grammar: {
                            title: "Thì Hiện tại Tiếp diễn diễn tả kế hoạch đã định sẵn",
                            rule: "S + am/is/are + V-ing + (thời gian/địa điểm cụ thể)",
                            example: "I am staying at a hotel near the airport and returning on Friday."
                        }
                    },
                    {
                        title: "Tình huống 2: Khai báo Hải quan & Hành lý",
                        turns: [
                            { role: "Customs Officer (Nhân viên Hải quan)", en: "Do you have anything to declare, such as restricted medications, food, or more than ten thousand dollars in cash?", vi: "Ông/bà có hàng hóa gì cần khai báo không, như thuốc hạn chế, thực phẩm, hoặc hơn 10.000 đô la tiền mặt?" },
                            { role: "Passenger (Người nhập cảnh)", en: "No, I only have personal belongings and my prescribed medication with a doctor's note.", vi: "Không, tôi chỉ mang đồ dùng cá nhân và thuốc kê đơn có giấy xác nhận của bác sĩ." }
                        ],
                        vocab: [
                            { word: "declare", ipa: "/dɪˈkler/", mean: "khai báo (hải quan)" },
                            { word: "personal belongings", ipa: "/ˈpɝː.sən.əl bɪˈlɑːŋ.ɪŋz/", mean: "đồ dùng cá nhân" }
                        ],
                        grammar: {
                            title: "Câu hỏi nghi vấn với 'Anything' & Câu mệnh lệnh lịch sự",
                            rule: "Do you have anything to + V-infinitive? / Please + V-bare...",
                            example: "Do you have any liquids to declare? Please open your suitcase for inspection."
                        }
                    }
                ],
                biostat: [
                    {
                        title: "Thảo luận thiết kế nghiên cứu & Cỡ mẫu",
                        turns: [
                            { role: "Principal Investigator", en: "How did we calculate the required sample size for this clinical trial?", vi: "Chúng ta đã tính toán cỡ mẫu cần thiết cho thử nghiệm lâm sàng này như thế nào?" },
                            { role: "Biostatistician", en: "We based it on an eighty percent statistical power and a five percent significance level, accounting for a ten percent dropout rate.", vi: "Chúng tôi dựa trên lực thống kê 80% và mức ý nghĩa 5%, có tính đến tỷ lệ bỏ cuộc 10%." }
                        ],
                        vocab: [
                            { word: "statistical power", ipa: "/stəˈtɪs.tɪ.kəl ˈpaʊ.ɚ/", mean: "lực thống kê" },
                            { word: "significance level", ipa: "/sɪɡˈnɪf.ə.kəns ˈlev.əl/", mean: "mức ý nghĩa thống kê" }
                        ],
                        grammar: {
                            title: "Phân từ hiện tại (V-ing) rút gọn mệnh đề bổ sung",
                            rule: "Main Clause + , accounting for / considering + Noun Phrase",
                            example: "We ran a multivariate model, adjusting for age and baseline severity."
                        }
                    }
                ],
                pharma: [
                    {
                        title: "Tư vấn sử dụng thuốc & Tác dụng phụ",
                        turns: [
                            { role: "Pharmacist", en: "Take one tablet twice daily after meals. Avoid driving if you experience drowsiness.", vi: "Uống một viên hai lần mỗi ngày sau bữa ăn. Tránh lái xe nếu bạn cảm thấy buồn ngủ." },
                            { role: "Patient", en: "Can I take this medication alongside my blood pressure pills?", vi: "Tôi có thể uống thuốc này cùng với thuốc huyết áp của tôi không?" }
                        ],
                        vocab: [
                            { word: "drowsiness", ipa: "/ˈdraʊ.zi.nəs/", mean: "cơn buồn ngủ" },
                            { word: "drug interaction", ipa: "/drʌɡ ˌɪn.t̬ɚˈæk.ʃən/", mean: "tương tác thuốc" }
                        ],
                        grammar: {
                            title: "Câu điều kiện loại 1 trong hướng dẫn y khoa",
                            rule: "Imperative (V-bare) + if + S + V (Present Simple)",
                            example: "Consult your physician immediately if any allergic rash develops."
                        }
                    }
                ],
                conference: [
                    {
                        title: "Trình bày kết quả & Trả lời câu hỏi phản biện",
                        turns: [
                            { role: "Speaker", en: "As illustrated in the Kaplan-Meier curve, overall survival was significantly higher in the treatment group.", vi: "Như minh họa trong đường cong Kaplan-Meier, tỷ lệ sống còn toàn bộ cao hơn đáng kể ở nhóm điều trị." },
                            { role: "Moderator", en: "Thank you for a clear presentation. Could you elaborate on the limitations of your study?", vi: "Cảm ơn bài trình bày rõ ràng. Ông/bà có thể nói rõ hơn về những hạn chế của nghiên cứu không?" }
                        ],
                        vocab: [
                            { word: "illustrate", ipa: "/ˈɪl.ə.streɪt/", mean: "minh họa" },
                            { word: "elaborate on", ipa: "/iˈlæb.ə.reɪt ɑːn/", mean: "trình bày chi tiết thêm" }
                        ],
                        grammar: {
                            title: "Cấu trúc bị động so sánh trong báo cáo kết quả",
                            rule: "S + was/were + Adv + Comparative Adj + in + Group",
                            example: "The incidence rate was markedly lower in the vaccinated cohort."
                        }
                    }
                ],
                hotel: [
                    {
                        title: "Làm thủ tục Nhận phòng Khách sạn",
                        turns: [
                            { role: "Receptionist", en: "Welcome to Grand Hotel. Do you have a reservation under your name?", vi: "Chào mừng đến khách sạn Grand. Quý khách có đặt phòng trước dưới tên mình không ạ?" },
                            { role: "Guest", en: "Yes, my name is Nam Dao. I booked a deluxe room for four nights.", vi: "Vâng, tên tôi là Nam Đào. Tôi đã đặt một phòng deluxe cho 4 đêm." }
                        ],
                        vocab: [
                            { word: "deluxe room", ipa: "/dəˈlʌks ruːm/", mean: "phòng cao cấp" }
                        ],
                        grammar: {
                            title: "Thì Quá khứ đơn diễn tả hành động đặt chỗ đã hoàn tất",
                            rule: "S + booked / reserved + Object + for + Duration",
                            example: "I reserved an airport shuttle for tomorrow morning."
                        }
                    }
                ]
            };

            let currentTopicKey = "immigration";
            let currentClipIndex = 0;
            let isSubVisible = true;
            let customDialogueObj = null;
            let isPlayingSequence = false;

            function renderDialogueScene(sceneObj, badgeText) {
                document.getElementById('clip-badge').innerText = badgeText;
                let container = document.getElementById('subtitle-container');
                let html = "";

                sceneObj.turns.forEach((turn, idx) => {
                    let roleClass = idx % 2 === 1 ? "turn-box role-b" : "turn-box";
                    let blurClass = isSubVisible ? "" : "sub-hidden";
                    html += `
                        <div class="${roleClass}">
                            <div class="role-label">
                                <span>${turn.role}</span>
                                <button class="btn-outline-blue" style="padding:2px 8px; font-size:11px; background:rgba(255,255,255,0.9);" onclick="speakText('${turn.en.replace(/'/g, "\\'")}', 0.95)">Nghe câu này</button>
                            </div>
                            <div class="sub-en ${blurClass}">${turn.en}</div>
                            <div class="sub-vi ${blurClass}">${turn.vi}</div>
                        </div>
                    `;
                });
                container.innerHTML = html;

                let vocabHtml = "";
                sceneObj.vocab.forEach(v => {
                    vocabHtml += `
                        <div class="vocab-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:bold; color:#0d6efd; font-size:15px;">${v.word}</span>
                                <button class="btn-outline-blue" style="padding:3px 8px; font-size:11px;" onclick="speakText('${v.word.replace(/'/g, "\\'")}', 0.9)">Nghe</button>
                            </div>
                            ${v.ipa ? `<div style="font-family:monospace; color:#6c757d; font-size:12px;">${v.ipa}</div>` : ''}
                            <div style="color:#212529; font-size:13px; margin-top:3px;">Nghĩa: <b>${v.mean}</b></div>
                        </div>
                    `;
                });
                document.getElementById('related-vocab-list').innerHTML = vocabHtml;

                document.getElementById('related-grammar-box').innerHTML = `
                    <div class="grammar-card">
                        <div style="font-weight:bold; color:#084298; font-size:14px; margin-bottom:5px;">${sceneObj.grammar.title}</div>
                        <div style="background:#ffffff; padding:6px 8px; border-radius:4px; font-family:monospace; font-size:12px; color:#d63384; margin-bottom:6px;">
                            ${sceneObj.grammar.rule}
                        </div>
                        <div style="font-size:13px; color:#333;">
                            <b>Ví dụ mở rộng:</b> <i>"${sceneObj.grammar.example}"</i>
                            <button class="btn-outline-blue" style="padding:2px 7px; font-size:11px; margin-left:5px;" onclick="speakText('${sceneObj.grammar.example.replace(/'/g, "\\'")}', 0.95)">Nghe</button>
                        </div>
                    </div>
                `;
            }

            function renderVideoLesson() {
                if (customDialogueObj) {
                    renderDialogueScene(customDialogueObj, customDialogueObj.title);
                } else {
                    let list = DIALOGUE_BANK[currentTopicKey];
                    let scene = list[currentClipIndex];
                    renderDialogueScene(scene, `${scene.title} (${currentClipIndex + 1}/${list.length})`);
                }
            }

            function changeVideoLesson() {
                stopClip();
                customDialogueObj = null;
                currentTopicKey = document.getElementById('video-topic-select').value;
                currentClipIndex = 0;
                renderVideoLesson();
            }

            function nextClipInTopic() {
                stopClip();
                if (customDialogueObj) customDialogueObj = null;
                let list = DIALOGUE_BANK[currentTopicKey];
                currentClipIndex = (currentClipIndex + 1) % list.length;
                renderVideoLesson();
            }

            async function generateCustomDialogue() {
                let rawTopic = document.getElementById('custom-topic-input').value.trim();
                if (!rawTopic) { alert("Vui lòng nhập tình huống hội thoại!"); return; }
                stopClip();
                let btn = document.getElementById('btn-gen-topic');
                btn.innerText = "Đang tạo...";
                btn.disabled = true;

                try {
                    let lower = rawTopic.toLowerCase();
                    if (lower.includes("nhập cảnh") || lower.includes("hải quan") || lower.includes("sân bay") || lower.includes("immigration")) {
                        customDialogueObj = DIALOGUE_BANK["immigration"][0];
                        renderDialogueScene(customDialogueObj, `TÌNH HUỐNG TỰ CHỌN: ${rawTopic.toUpperCase()}`);
                        return;
                    }
                    let enTopic = rawTopic;
                    if (/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(rawTopic)) {
                        enTopic = await translateText(rawTopic, 'vi', 'en');
                    }
                    let turnsEn = [
                        { role: "Person A (Đối tác / Nhân viên)", en: `Good morning. How can I assist you today regarding ${enTopic}?` },
                        { role: "Person B (Bạn / Khách)", en: `Hello, I need some information and assistance with ${enTopic}. Could you guide me through the procedure?` },
                        { role: "Person A (Đối tác / Nhân viên)", en: `Certainly. Please provide your relevant documents first, and we will process your request right away.` },
                        { role: "Person B (Bạn / Khách)", en: `Thank you very much for your prompt support. Here are the details you requested.` }
                    ];
                    let turnsFull = [];
                    for (let t of turnsEn) {
                        let viText = await translateText(t.en, 'en', 'vi');
                        turnsFull.push({ role: t.role, en: t.en, vi: viText });
                    }
                    customDialogueObj = {
                        title: `HỘI THOẠI THỰC TẾ: ${rawTopic.toUpperCase()}`,
                        turns: turnsFull,
                        vocab: [{ word: "procedure", ipa: "/prəˈsiː.dʒɚ/", mean: "thủ tục, quy trình" }],
                        grammar: {
                            title: "Mẫu câu Đề nghị Hỗ trợ Lịch sự",
                            rule: "Could you guide me through + Noun?",
                            example: `Could you clarify the requirements for ${enTopic}?`
                        }
                    };
                    renderVideoLesson();
                } finally {
                    btn.innerText = "Tạo hội thoại thực tế";
                    btn.disabled = false;
                }
            }

            function playFullDialogue(rate) {
                if (!('speechSynthesis' in window)) return;
                stopClip();
                let scene = customDialogueObj ? customDialogueObj : DIALOGUE_BANK[currentTopicKey][currentClipIndex];
                let turns = scene.turns;
                let wave = document.getElementById('wave-indicator');
                let status = document.getElementById('player-status');
                isPlayingSequence = true;
                wave.classList.add('playing');
                let index = 0;

                function speakNextTurn() {
                    if (!isPlayingSequence || index >= turns.length) {
                        wave.classList.remove('playing');
                        status.innerText = "Đã phát xong đoạn hội thoại.";
                        isPlayingSequence = false;
                        return;
                    }
                    status.innerText = `Đang đọc lượt ${index + 1}/${turns.length} (${rate}x)...`;
                    let utterance = new SpeechSynthesisUtterance(turns[index].en);
                    utterance.lang = 'en-US';
                    utterance.rate = rate;
                    utterance.pitch = index % 2 === 0 ? 0.95 : 1.15;
                    utterance.onend = function() {
                        index++;
                        setTimeout(speakNextTurn, 350);
                    };
                    window.speechSynthesis.speak(utterance);
                }
                speakNextTurn();
            }

            function stopClip() {
                isPlayingSequence = false;
                if ('speechSynthesis' in window) window.speechSynthesis.cancel();
                let wave = document.getElementById('wave-indicator');
                let status = document.getElementById('player-status');
                if (wave) wave.classList.remove('playing');
                if (status) status.innerText = "Đã dừng phát.";
            }

            function toggleSubtitle() {
                isSubVisible = !isSubVisible;
                let btn = document.getElementById('btn-toggle-sub');
                document.querySelectorAll('.sub-en, .sub-vi').forEach(el => {
                    if (isSubVisible) el.classList.remove('sub-hidden');
                    else el.classList.add('sub-hidden');
                });
                btn.innerText = isSubVisible ? "Ẩn phụ đề" : "Hiện phụ đề";
            }

            renderVideoLesson();

            function speakText(text, rate = 1.0) {
                stopClip();
                if ('speechSynthesis' in window) {
                    let utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = 'en-US';
                    utterance.rate = rate;
                    window.speechSynthesis.speak(utterance);
                }
            }

            async function translateText(text, sl, tl) {
                try {
                    let res = await fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=${sl}&tl=${tl}&q=${encodeURIComponent(text)}`);
                    if (res.ok) {
                        let data = await res.json();
                        return Array.isArray(data) ? data.join(" ") : data;
                    }
                } catch(e) {}
                return "";
            }

            async function lookupWord() {
                let word = document.getElementById('dict-input').value.trim();
                if (!word) return;
                let resDiv = document.getElementById('dict-result');
                resDiv.innerHTML = "<p>Đang tra cứu dữ liệu từ điển...</p>";
                let viMeaning = await translateText(word, 'en', 'vi');
                let phonetic = "";
                let defHtml = "";
                try {
                    let dictRes = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(word)}`);
                    if (dictRes.ok) {
                        let dictData = await dictRes.json();
                        let entry = dictData[0];
                        phonetic = entry.phonetic || (entry.phonetics.find(p => p.text) || {}).text || "";
                        entry.meanings.slice(0, 2).forEach(m => {
                            let def = m.definitions[0];
                            defHtml += `<div style="margin-bottom: 8px;"><span style="background:#e7f1ff; color:#0d6efd; padding:2px 6px; border-radius:4px; font-size:12px; font-weight:bold;">${m.partOfSpeech}</span><span> ${def.definition}</span>${def.example ? `<div style="color:#084298; font-style:italic; margin-top:3px;">Ví dụ: "${def.example}"</div>` : ''}</div>`;
                        });
                    }
                } catch(e) {}
                resDiv.innerHTML = `<div class="word-header">${word} <button class="btn-blue" style="padding:5px 12px; font-size:12px;" onclick="speakText('${word.replace(/'/g, "\\'")}', 0.95)">Đọc chuẩn</button> <button class="btn-outline-blue" style="padding:5px 12px; font-size:12px;" onclick="speakText('${word.replace(/'/g, "\\'")}', 0.65)">Đọc chậm</button></div>${phonetic ? `<div class="phonetic">${phonetic}</div>` : ''}<div class="meaning-box"><b>Nghĩa tiếng Việt:</b> <span style="font-size:16px; color:#0d6efd; font-weight:bold;">${viMeaning}</span></div>${defHtml ? `<div><b>Giải nghĩa & Ngữ cảnh Anh - Anh:</b><div style="margin-top:8px;">${defHtml}</div></div>` : ''}`;
                speakText(word, 0.95);
            }

            const SENTENCE_BANK = {
                immigration: [
                    { en: "Here is my passport and return ticket. I am here for an international medical conference.", vi: "Đây là hộ chiếu và vé khứ hồi của tôi. Tôi đến đây để tham dự một hội nghị y khoa quốc tế." },
                    { en: "I have nothing to declare, only personal belongings and prescribed medication.", vi: "Tôi không có gì cần khai báo, chỉ có đồ dùng cá nhân và thuốc kê đơn." }
                ],
                medical: [
                    { en: "The one-sample t-test compares the mean of a single sample to a known population mean.", vi: "Kiểm định t một mẫu so sánh giá trị trung bình của một mẫu đơn lẻ với giá trị trung bình quần thể đã biết." },
                    { en: "Statistical thinking is essential for evidence-based medical research.", vi: "Tư duy thống kê là yếu tố thiết yếu cho nghiên cứu y học dựa trên bằng chứng." }
                ],
                academic: [
                    { en: "Thank you for the opportunity to present our latest research findings today.", vi: "Cảm ơn vì cơ hội được trình bày những phát hiện nghiên cứu mới nhất của chúng tôi hôm nay." },
                    { en: "As shown in the figure, there is a strong correlation between the two variables.", vi: "Như được thể hiện trong biểu đồ, có một mối tương quan chặt chẽ giữa hai biến số." }
                ]
            };

            let currentIdx = 0;
            function loadNextSentence() {
                let topic = document.getElementById('topic-select').value;
                let list = SENTENCE_BANK[topic];
                currentIdx = (currentIdx + 1) % list.length;
                document.getElementById('target-sentence').innerText = list[currentIdx].en;
                document.getElementById('target-vi').innerText = "(" + list[currentIdx].vi + ")";
                document.getElementById('speak-feedback').innerHTML = "";
            }

            function startPronunciationCheck() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) { alert("Vui lòng dùng Google Chrome để sử dụng micro!"); return; }
                let btn = document.getElementById('btn-record-eval');
                let targetText = document.getElementById('target-sentence').innerText;
                let rec = new SpeechRecognition();
                rec.lang = 'en-US';
                btn.innerText = "ĐANG NGHE... HÃY ĐỌC TO CÂU MẪU...";
                btn.style.backgroundColor = "#084298";
                rec.onresult = function(event) { evaluateSpeech(targetText, event.results[0][0].transcript); };
                rec.onerror = function(e) { document.getElementById('speak-feedback').innerHTML = `<div style="color:#dc3545;">Lỗi micro (${e.error}). Hãy thử lại!</div>`; };
                rec.onend = function() { btn.innerText = "BẤM ĐỂ ĐỌC CÂU TRÊN VÀ CHẤM ĐIỂM AI"; btn.style.backgroundColor = "#0d6efd"; };
                rec.start();
            }

            function evaluateSpeech(target, spoken) {
                let cleanTarget = target.toLowerCase().replace(/[.,!?]/g, "").split(/\s+/);
                let cleanSpoken = spoken.toLowerCase().replace(/[.,!?]/g, "").split(/\s+/);
                let matchCount = 0;
                let highlightedHtml = "";
                cleanTarget.forEach(w => {
                    if (cleanSpoken.includes(w)) { matchCount++; highlightedHtml += `<span class="word-correct">${w}</span> `; }
                    else { highlightedHtml += `<span class="word-wrong">${w}</span> `; }
                });
                let score = Math.round((matchCount / cleanTarget.length) * 100);
                let badgeColor = score >= 80 ? "#cfe2ff; color:#084298" : (score >= 50 ? "#fff3cd; color:#664d03" : "#f8d7da; color:#842029");
                let comment = score >= 80 ? "Xuất sắc! Phát âm rất chuẩn xác." : (score >= 50 ? "Khá tốt! Chú ý các từ gạch đỏ." : "Cần luyện thêm! Hãy bấm 'Nghe chậm' và đọc lại.");
                document.getElementById('speak-feedback').innerHTML = `<div style="background:#f8f9fa; border:1px solid #dee2e6; border-radius:8px; padding:15px;"><div><b>AI nghe được:</b> <i>"${spoken}"</i></div><div style="margin-top:8px;"><b>Đối chiếu:</b> ${highlightedHtml}</div><div class="score-circle" style="background:${badgeColor};">Điểm phát âm: ${score}/100</div><div style="margin-top:8px; font-size:14px;"><b>Nhận xét:</b> ${comment}</div></div>`;
            }

            async function sendTutorMessage() {
                let inputEl = document.getElementById('chat-input');
                let text = inputEl.value.trim();
                if (!text) return;
                let chatBox = document.getElementById('chat-box');
                chatBox.innerHTML += `<div class="msg-user">${text}</div>`;
                inputEl.value = "";
                chatBox.scrollTop = chatBox.scrollHeight;
                let isVietnamese = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(text);
                if (isVietnamese) {
                    let enTrans = await translateText(text, 'vi', 'en');
                    chatBox.innerHTML += `<div class="msg-ai"><b>Diễn đạt Tiếng Anh tự nhiên:</b><br><span style="color:#0d6efd; font-weight:bold; font-size:15px;">"${enTrans}"</span> <button class="btn-outline-blue" style="padding:3px 10px; font-size:12px;" onclick="speakText('${enTrans.replace(/'/g, "\\'")}', 0.95)">Nghe</button></div>`;
                    speakText(enTrans, 0.95);
                } else {
                    let viMeaning = await translateText(text, 'en', 'vi');
                    let polishedEn = await translateText(viMeaning, 'vi', 'en');
                    chatBox.innerHTML += `<div class="msg-ai"><b>Phân tích câu của bạn:</b><br>• <b>Nghĩa tiếng Việt:</b> ${viMeaning}<br>• <b>Gợi ý mượt hơn:</b> <span style="color:#084298; font-weight:bold;">"${polishedEn}"</span> <button class="btn-outline-blue" style="padding:3px 10px; font-size:12px;" onclick="speakText('${polishedEn.replace(/'/g, "\\'")}', 0.95)">Nghe mẫu</button></div>`;
                    speakText(polishedEn, 0.95);
                }
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    components.html(english_tutor_html, height=850, scrolling=True)
