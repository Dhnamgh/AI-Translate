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
# TAB 3: HỌC TIẾNG ANH CÙNG AI (HỘI THOẠI NHẬP VAI THỰC TẾ + RESPONSIVE MOBILE)
# ==============================================================================
with tab3:
    st.subheader("Hệ thống Học Tiếng Anh Tương tác cùng AI")

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
            /* Menu xanh responsive trên cả máy tính và điện thoại */
            .blue-menu-bar {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                background-color: #0d6efd;
                border-radius: 8px;
                padding: 5px;
                gap: 5px;
                margin-bottom: 12px;
                box-shadow: 0 3px 8px rgba(13, 110, 253, 0.25);
            }
            @media (max-width: 768px) {
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

            /* Bố cục Video Hội thoại + Từ vựng + Ngữ pháp */
            .video-layout { display: flex; gap: 15px; flex-direction: row; }
            @media (max-width: 768px) {
                .video-layout { flex-direction: column; }
            }
            .video-main { flex: 1.35; }
            .video-sidebar {
                flex: 1;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 14px;
            }

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

            /* Khung hội thoại 2 vai trực quan */
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
            .turn-box.role-b {
                background: rgba(255, 255, 255, 0.2);
                border-left: 3px solid #ffc107;
            }
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

            .vocab-card {
                background: #ffffff;
                border-left: 4px solid #0d6efd;
                border-radius: 6px;
                padding: 10px 12px;
                margin-bottom: 10px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            }
            .grammar-card {
                background: #e7f1ff;
                border: 1px solid #b6d4fe;
                border-radius: 6px;
                padding: 12px;
                margin-top: 10px;
            }

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
        <!-- THANH MENU MÀU XANH CO GIÃN ĐẦY ĐỦ TRÊN ĐIỆN THOẠI & MÁY TÍNH -->
        <div class="blue-menu-bar">
            <button class="menu-item active" onclick="openPanel('video', this)">
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

        <!-- PANEL 1: XEM VIDEO / NGHE HỘI THOẠI NHẬP VAI THỰC TẾ -->
        <div id="panel-video" class="dropdown-panel active">
            <div class="topic-control-box">
                <div class="input-group">
                    <select id="video-topic-select" onchange="changeVideoLesson()">
                        <option value="immigration">Chủ đề 1: Thủ tục Nhập cảnh & Hải quan Sân bay</option>
                        <option value="biostat">Chủ đề 2: Thống kê Y sinh & Nghiên cứu Lâm sàng</option>
                        <option value="pharma">Chủ đề 3: Dược lâm sàng & Tư vấn Thuốc</option>
                        <option value="conference">Chủ đề 4: Báo cáo tại Hội nghị Khoa học Quốc tế</option>
                        <option value="hotel">Chủ đề 5: Nhận phòng Khách sạn & Lưu trú Công tác</option>
                        <option value="admin">Chủ đề 6: Điều hành & Quản trị Chuyển đổi số</option>
                    </select>
                    <button class="btn-outline-blue" onclick="nextClipInTopic()">Đổi tình huống khác</button>
                </div>

                <div class="input-group">
                    <input type="text" id="custom-topic-input" placeholder="Tự nhập tình huống bất kỳ (VD: khai báo hải quan, khám bệnh, phỏng vấn...)" onkeypress="if(event.key==='Enter') generateCustomDialogue()">
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

                        <div class="dialogue-container" id="subtitle-container">
                            <!-- Các lượt đối thoại A - B sẽ render tại đây -->
                        </div>

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

        <!-- PANEL 2: TỪ ĐIỂN AI & PHÁT ÂM -->
        <div id="panel-dict" class="dropdown-panel">
            <div class="input-group">
                <input type="text" id="dict-input" placeholder="Nhập từ vựng tiếng Anh (VD: immigration, customs, declaration)..." onkeypress="if(event.key==='Enter') lookupWord()">
                <button class="btn-blue" onclick="lookupWord()">Tra cứu</button>
            </div>
            <div id="dict-result">
                <p style="color: #6c757d; font-style: italic;">Nhập một từ tiếng Anh bất kỳ để xem nghĩa tiếng Việt, phiên âm quốc tế (IPA), ví dụ ngữ cảnh và nghe giọng đọc chuẩn.</p>
            </div>
        </div>

        <!-- PANEL 3: LUYỆN NÓI & CHẤM ĐIỂM PHÁT ÂM -->
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
                <span id="target-sentence">Here is my passport and return ticket. I am here for an international medical conference.</span>
                <div style="margin-top: 10px;">
                    <button class="btn-blue" onclick="speakText(document.getElementById('target-sentence').innerText, 0.95)">Nghe mẫu chuẩn</button>
                    <button class="btn-outline-blue" onclick="speakText(document.getElementById('target-sentence').innerText, 0.65)">Nghe chậm</button>
                </div>
                <div id="target-vi" style="font-size: 14px; color: #555; margin-top: 8px; font-weight: normal; font-style: italic;">
                    (Đây là hộ chiếu và vé khứ hồi của tôi. Tôi đến đây để tham dự một hội nghị y khoa quốc tế.)
                </div>
            </div>
            <button id="btn-record-eval" class="btn-blue" style="width: 100%; padding: 13px; font-size: 14px;" onclick="startPronunciationCheck()">
                BẤM ĐỂ ĐỌC CÂU TRÊN VÀ CHẤM ĐIỂM AI
            </button>
            <div id="speak-feedback" style="margin-top: 15px;"></div>
        </div>

        <!-- PANEL 4: GIA SƯ HỘI THOẠI SONG NGỮ -->
        <div id="panel-chat" class="dropdown-panel">
            <div class="chat-window" id="chat-box">
                <div class="msg-ai">
                    <b>AI English Tutor:</b> Xin chào! Hãy nhập câu tiếng Việt bạn muốn nói với hải quan, đồng nghiệp quốc tế... hoặc nhập câu tiếng Anh để tôi kiểm tra và chỉnh sửa tự nhiên hơn.
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

            // KHO DỮ LIỆU HỘI THOẠI ĐỐI ĐÁP 2 VAI (ROLEPLAY) THỰC TẾ
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
                            { word: "reservation", ipa: "/ˌrez.ɚˈveɪ.ʃən/", mean: "sự đặt chỗ trước (khách sạn/vé)" }
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
                            { role: "Passenger (Người nhập cảnh)", en: "No, I only have personal belongings and my prescribed medication with a doctor's note.", vi: "Không, tôi chỉ mang đồ dùng cá nhân và thuốc kê đơn có giấy xác nhận của bác sĩ." },
                            { role: "Customs Officer (Nhân viên Hải quan)", en: "Alright. Please place your carry-on bag on the scanner belt. Thank you, welcome to our country.", vi: "Được rồi. Vui lòng đặt hành lý xách tay lên băng chuyền máy soi. Cảm ơn, chào mừng đến đất nước chúng tôi." }
                        ],
                        vocab: [
                            { word: "declare", ipa: "/dɪˈkler/", mean: "khai báo (hải quan)" },
                            { word: "personal belongings", ipa: "/ˈpɝː.sən.əl bɪˈlɑːŋ.ɪŋz/", mean: "đồ dùng cá nhân" },
                            { word: "prescribed medication", ipa: "/prɪˈskraɪbd ˌmed.əˈkeɪ.ʃən/", mean: "thuốc được kê đơn" }
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
                            { word: "significance level", ipa: "/sɪɡˈnɪf.ə.kəns ˈlev.əl/", mean: "mức ý nghĩa thống kê" },
                            { word: "dropout rate", ipa: "/ˈdrɑːp.aʊt reɪt/", mean: "tỷ lệ bệnh nhân bỏ cuộc/mất dấu" }
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
                            { role: "Patient", en: "Can I take this medication alongside my blood pressure pills?", vi: "Tôi có thể uống thuốc này cùng với thuốc huyết áp của tôi không?" },
                            { role: "Pharmacist", en: "Yes, there are no known drug interactions between them, but space them two hours apart.", vi: "Được, không có tương tác thuốc nào được ghi nhận giữa chúng, nhưng hãy uống cách nhau 2 giờ." }
                        ],
                        vocab: [
                            { word: "drowsiness", ipa: "/ˈdraʊ.zi.nəs/", mean: "cơn buồn ngủ, sự lơ mơ" },
                            { word: "drug interaction", ipa: "/drʌɡ ˌɪn.t̬ɚˈæk.ʃən/", mean: "tương tác thuốc" },
                            { word: "space apart", ipa: "/speɪs əˈpɑːrt/", mean: "chia khoảng cách thời gian" }
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
                            { word: "illustrate", ipa: "/ˈɪl.ə.streɪt/", mean: "minh họa, làm rõ" },
                            { word: "elaborate on", ipa: "/iˈlæb.ə.reɪt ɑːn/", mean: "trình bày chi tiết, nói rõ thêm về" },
                            { word: "limitation", ipa: "/ˌlɪm.əˈteɪ.ʃən/", mean: "hạn chế, điểm giới hạn" }
                        ],
                        grammar: {
                            title: "Cấu trúc bị động so sánh trong báo cáo kết quả",
                            rule: "S + was/were + Adv (significantly) + Comparative Adj + in + Group",
                            example: "The incidence rate was markedly lower in the vaccinated cohort."
                        }
                    }
                ],
                hotel: [
                    {
                        title: "Làm thủ tục Nhận phòng Khách sạn (Check-in)",
                        turns: [
                            { role: "Receptionist", en: "Welcome to Grand Hotel. Do you have a reservation under your name?", vi: "Chào mừng đến khách sạn Grand. Quý khách có đặt phòng trước dưới tên mình không ạ?" },
                            { role: "Guest", en: "Yes, my name is Nam Dao. I booked a deluxe room for four nights through the conference organizers.", vi: "Vâng, tên tôi là Nam Đào. Tôi đã đặt một phòng deluxe cho 4 đêm thông qua ban tổ chức hội nghị." }
                        ],
                        vocab: [
                            { word: "deluxe room", ipa: "/dəˈlʌks ruːm/", mean: "phòng cao cấp" },
                            { word: "organizer", ipa: "/ˈɔːr.ɡən.aɪ.zɚ/", mean: "ban tổ chức, người tổ chức" }
                        ],
                        grammar: {
                            title: "Thì Quá khứ đơn diễn tả hành động đặt chỗ đã hoàn tất",
                            rule: "S + booked / reserved + Object + for + Duration",
                            example: "I reserved an airport shuttle for tomorrow morning at seven."
                        }
                    }
                ],
                admin: [
                    {
                        title: "Họp triển khai Hệ thống Quản lý Số",
                        turns: [
                            { role: "Director", en: "How is the rollout of the new event management portal progressing?", vi: "Việc triển khai cổng thông tin quản lý sự kiện mới đang tiến triển thế nào rồi?" },
                            { role: "Manager", en: "We have completed user testing and will launch the live system across all departments next Monday.", vi: "Chúng tôi đã hoàn tất kiểm thử người dùng và sẽ vận hành chính thức trên toàn bộ các phòng ban vào thứ Hai tới." }
                        ],
                        vocab: [
                            { word: "rollout", ipa: "/ˈroʊl.aʊt/", mean: "sự triển khai, ra mắt hệ thống" },
                            { word: "progress", ipa: "/prəˈɡres/", mean: "tiến triển, phát triển" }
                        ],
                        grammar: {
                            title: "Kết hợp Hiện tại Hoàn thành & Tương lai Đơn",
                            rule: "S + have/has + V3/ed + and + will + V-bare",
                            example: "We have finalized the schedule and will distribute it to all delegates."
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

                // Render Từ vựng
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

                // Render Ngữ pháp
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
                if (customDialogueObj) {
                    customDialogueObj = null;
                }
                let list = DIALOGUE_BANK[currentTopicKey];
                currentClipIndex = (currentClipIndex + 1) % list.length;
                renderVideoLesson();
            }

            // TẠO HỘI THOẠI NHẬP VAI THỰC TẾ THEO CHỦ ĐỀ NGƯỜI DÙNG NHẬP
            async function generateCustomDialogue() {
                let rawTopic = document.getElementById('custom-topic-input').value.trim();
                if (!rawTopic) {
                    alert("Vui lòng nhập tình huống hội thoại bạn muốn học!");
                    return;
                }
                stopClip();
                let btn = document.getElementById('btn-gen-topic');
                btn.innerText = "Đang tạo hội thoại...";
                btn.disabled = true;

                try {
                    let lower = rawTopic.toLowerCase();
                    // Nếu từ khóa liên quan đến nhập cảnh / sân bay / hải quan -> Nạp ngay tình huống nhập cảnh chuẩn xác
                    if (lower.includes("nhập cảnh") || lower.includes("hải quan") || lower.includes("sân bay") || lower.includes("hộ chiếu") || lower.includes("immigration") || lower.includes("customs")) {
                        customDialogueObj = DIALOGUE_BANK["immigration"][0];
                        renderDialogueScene(customDialogueObj, `TÌNH HUỐNG TỰ CHỌN: ${rawTopic.toUpperCase()}`);
                        return;
                    }

                    // Với bất kỳ tình huống nào khác, dịch chủ đề sang tiếng Anh và dựng hội thoại đối đáp 2 vai tự nhiên
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

                    // Tạo từ vựng liên quan từ chủ đề
                    let topicWords = enTopic.replace(/[^a-zA-Z\s]/g, "").split(/\s+/).filter(w => w.length >= 4);
                    let vocabList = [];
                    for (let w of topicWords.slice(0, 3)) {
                        let cleanW = w.toLowerCase();
                        let meanVi = await translateText(cleanW, 'en', 'vi');
                        let ipaStr = "";
                        try {
                            let dRes = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${cleanW}`);
                            if (dRes.ok) {
                                let dData = await dRes.json();
                                ipaStr = dData[0].phonetic || (dData[0].phonetics.find(p => p.text) || {}).text || "";
                            }
                        } catch(e) {}
                        vocabList.push({ word: cleanW, ipa: ipaStr, mean: meanVi });
                    }
                    vocabList.push({ word: "procedure", ipa: "/prəˈsiː.dʒɚ/", mean: "thủ tục, quy trình" });

                    customDialogueObj = {
                        title: `HỘI THOẠI THỰC TẾ: ${rawTopic.toUpperCase()}`,
                        turns: turnsFull,
                        vocab: vocabList,
                        grammar: {
                            title: "Mẫu câu Đề nghị Hỗ trợ Lịch sự trong Giao tiếp Thực tế",
                            rule: "Could you guide me through + Noun? / How can I assist you regarding + Noun?",
                            example: `Could you clarify the requirements for ${enTopic}?`
                        }
                    };
                    renderVideoLesson();
                } catch (err) {
                    alert("Có lỗi kết nối khi tạo hội thoại, vui lòng thử lại!");
                } finally {
                    btn.innerText = "Tạo hội thoại thực tế";
                    btn.disabled = false;
                }
            }

            // Phát lần lượt từng câu đối thoại 2 vai
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
                    // Đổi cao độ giọng nhẹ giữa vai A và vai B cho sinh động
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
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                }
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
                    { en: "Statistical thinking is essential for evidence-based medical research.", vi: "Tư duy thống kê là yếu tố thiết yếu cho nghiên cứu y học dựa trên bằng chứng." },
                    { en: "The clinical trial demonstrated a significant improvement in patient outcomes.", vi: "Thử nghiệm lâm sàng đã chứng minh sự cải thiện đáng kể về kết quả điều trị của bệnh nhân." }
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
