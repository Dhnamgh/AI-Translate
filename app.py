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
    /* Font chữ chuẩn Times New Roman 13px */
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

    /* Thiết kế thanh Tab Menu màu xanh chuyên nghiệp, xổ nội dung mượt */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0d6efd;
        padding: 6px 10px 0px 10px;
        border-radius: 8px 8px 0px 0px;
        gap: 6px;
        border-bottom: 2px solid #0a58ca;
    }

    .stTabs button[data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.15);
        color: #ffffff !important;
        border-radius: 6px 6px 0px 0px;
        padding: 10px 20px;
        border: none !important;
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
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        animation: slideDown 0.25s ease-out;
    }

    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-6px); }
        to { opacity: 1; transform: translateY(0); }
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
            .cabin-panel { flex: 1; background: #ffffff; border: 1px solid #ced4da; border-radius: 8px; padding: 15px; text-align: left; height: 500px; overflow-y: auto; box-shadow: inset 0 0 5px rgba(0,0,0,0.05); }
            .panel-title { font-family: 'Times New Roman', Times, serif !important; font-weight: bold; font-size: 14px !important; margin-bottom: 10px; border-bottom: 1px solid #e9ecef; padding-bottom: 5px; }
            .panel-content { font-size: 16px; line-height: 1.6; word-wrap: break-word; }
            @media (max-width: 768px) { .cabin-grid { flex-direction: column; } .cabin-panel { height: 350px; } }
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
    components.html(cabin_html_code, height=750)

# ==============================================================================
# TAB 3: HỌC TIẾNG ANH CÙNG AI (NHIỀU CHỦ ĐỀ + TỰ NHẬP CHỦ ĐỀ BẤT KỲ)
# ==============================================================================
with tab3:
    st.subheader("Hệ thống Học Tiếng Anh Tương tác cùng AI")

    english_tutor_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #f4f6f9;
                margin: 0;
                padding: 12px;
                color: #212529;
            }
            .blue-menu-bar {
                display: flex;
                background-color: #0d6efd;
                border-radius: 8px;
                padding: 5px;
                gap: 6px;
                margin-bottom: 15px;
                box-shadow: 0 3px 8px rgba(13, 110, 253, 0.25);
                flex-wrap: wrap;
            }
            .menu-item {
                flex: 1;
                min-width: 160px;
                padding: 12px 15px;
                border: none;
                border-radius: 6px;
                background-color: transparent;
                color: #ffffff;
                font-weight: bold;
                cursor: pointer;
                font-size: 14px;
                text-align: center;
                transition: all 0.25s ease;
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
            .arrow-icon { font-size: 11px; transition: transform 0.25s ease; }
            .menu-item.active .arrow-icon { transform: rotate(180deg); }

            .dropdown-panel {
                background: #ffffff;
                border: 1px solid #cfe2ff;
                border-top: 4px solid #0d6efd;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                display: none;
                animation: expandPanel 0.3s ease-out;
            }
            .dropdown-panel.active { display: block; }
            @keyframes expandPanel {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .topic-control-box {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 14px;
                margin-bottom: 16px;
            }
            .input-group { display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
            .input-group:last-child { margin-bottom: 0; }
            input[type="text"], select {
                flex: 1;
                min-width: 220px;
                padding: 10px 14px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
            }
            .btn-blue {
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                background-color: #0d6efd;
                color: white;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
                transition: 0.2s;
            }
            .btn-blue:hover { background-color: #0b5ed7; }
            .btn-outline-blue {
                padding: 8px 14px;
                border: 1px solid #0d6efd;
                border-radius: 6px;
                background-color: #ffffff;
                color: #0d6efd;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
            }
            .btn-outline-blue:hover { background-color: #e7f1ff; }
            .btn-dark-blue {
                padding: 8px 14px;
                border: none;
                border-radius: 6px;
                background-color: #084298;
                color: #ffffff;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
            }

            .video-layout { display: flex; gap: 20px; flex-wrap: wrap; }
            .video-main { flex: 1.3; min-width: 300px; }
            .video-sidebar {
                flex: 1;
                min-width: 280px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                max-height: 580px;
                overflow-y: auto;
            }
            .media-screen {
                background: linear-gradient(135deg, #0a2540 0%, #0d6efd 100%);
                color: white;
                border-radius: 10px;
                padding: 25px 20px;
                text-align: center;
                position: relative;
                box-shadow: 0 4px 10px rgba(0,0,0,0.15);
            }
            .wave-bars { display: flex; justify-content: center; align-items: center; gap: 5px; height: 36px; margin-bottom: 12px; }
            .bar { width: 5px; height: 12px; background: #6ea8fe; border-radius: 3px; transition: height 0.2s; }
            .playing .bar { animation: soundWave 0.6s infinite alternate; }
            .playing .bar:nth-child(2) { animation-delay: 0.1s; }
            .playing .bar:nth-child(3) { animation-delay: 0.2s; }
            .playing .bar:nth-child(4) { animation-delay: 0.3s; }
            .playing .bar:nth-child(5) { animation-delay: 0.4s; }
            @keyframes soundWave {
                from { height: 8px; background: #6ea8fe; }
                to { height: 34px; background: #ffffff; }
            }

            .subtitle-box {
                background: rgba(0, 0, 0, 0.45);
                border-radius: 8px;
                padding: 15px;
                margin-top: 15px;
                min-height: 95px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .sub-en { font-size: 16px; font-weight: bold; color: #ffffff; line-height: 1.5; }
            .sub-vi { font-size: 14px; color: #cfe2ff; margin-top: 6px; font-style: italic; }
            .sub-hidden { filter: blur(6px); user-select: none; opacity: 0.4; }
            .controls-row { display: flex; gap: 8px; justify-content: center; margin-top: 15px; flex-wrap: wrap; }

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
                margin-top: 12px;
            }

            .word-header { font-size: 22px; font-weight: bold; color: #0d6efd; margin-bottom: 4px; }
            .phonetic { color: #6c757d; font-size: 15px; font-family: monospace; margin-bottom: 10px; }
            .meaning-box { background: #f1f8ff; border-left: 4px solid #0d6efd; padding: 12px; border-radius: 6px; margin-bottom: 12px; }
            .sample-sentence-box { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px; font-size: 17px; font-weight: 500; margin-bottom: 15px; line-height: 1.5; }
            .score-circle { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 15px; margin-top: 10px; }
            .word-correct { color: #198754; font-weight: bold; }
            .word-wrong { color: #dc3545; text-decoration: line-through; }
            .chat-window { height: 300px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; background: #fdfdfd; margin-bottom: 12px; }
            .msg-user { background: #0d6efd; color: white; padding: 10px 14px; border-radius: 14px 14px 2px 14px; max-width: 80%; margin-left: auto; margin-bottom: 10px; font-size: 14px; }
            .msg-ai { background: #e9ecef; color: #212529; padding: 10px 14px; border-radius: 14px 14px 14px 2px; max-width: 85%; margin-right: auto; margin-bottom: 10px; font-size: 14px; line-height: 1.5; }
        </style>
    </head>
    <body>
        <div class="blue-menu-bar">
            <button class="menu-item active" onclick="openPanel('video', this)">
                <span>Xem Video & Luyện Nghe</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('dict', this)">
                <span>Từ điển AI & Phát âm</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('speak', this)">
                <span>Luyện Nói & Chấm điểm</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('chat', this)">
                <span>Gia sư Hội thoại Song ngữ</span>
                <span class="arrow-icon">▼</span>
            </button>
        </div>

        <!-- PANEL 1: XEM VIDEO / NGHE HỘI THOẠI + CHỌN HOẶC TỰ NHẬP CHỦ ĐỀ -->
        <div id="panel-video" class="dropdown-panel active">
            <div class="topic-control-box">
                <div class="input-group">
                    <select id="video-topic-select" onchange="changeVideoLesson()">
                        <option value="biostat">Chủ đề 1: Thống kê Y sinh & Nghiên cứu Lâm sàng</option>
                        <option value="pharma">Chủ đề 2: Dược lâm sàng & Thử nghiệm Thuốc mới</option>
                        <option value="conference">Chủ đề 3: Báo cáo tại Hội nghị Khoa học Quốc tế</option>
                        <option value="admin">Chủ đề 4: Điều hành & Quản trị Chuyển đổi số</option>
                        <option value="ai_tech">Chủ đề 5: Trí tuệ Nhân tạo (AI) trong Y tế & Giáo dục</option>
                        <option value="negotiation">Chủ đề 6: Đàm phán & Ký kết Hợp tác Quốc tế</option>
                        <option value="travel">Chủ đề 7: Giao tiếp Sân bay, Khách sạn & Công tác Nước ngoài</option>
                        <option value="daily">Chủ đề 8: Giao tiếp Công sở & Thảo luận Nhóm</option>
                    </select>
                    <button class="btn-outline-blue" onclick="nextClipInTopic()">Đổi đoạn hội thoại khác</button>
                </div>

                <div class="input-group">
                    <input type="text" id="custom-topic-input" placeholder="Hoặc tự nhập chủ đề bạn quan tâm (VD: Chronic urticaria, Phỏng vấn xin học bổng, Thuyết trình luận án...)" onkeypress="if(event.key==='Enter') generateCustomTopic()">
                    <button class="btn-blue" id="btn-gen-topic" onclick="generateCustomTopic()">Tạo bài học AI theo chủ đề</button>
                </div>
            </div>

            <div class="video-layout">
                <div class="video-main">
                    <div class="media-screen" id="media-player-box">
                        <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #9ec5fe; margin-bottom: 8px;" id="clip-badge">
                            BÀI NGHE THỰC TẾ 01
                        </div>
                        <div class="wave-bars" id="wave-indicator">
                            <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
                        </div>
                        <div style="font-size: 13px; color: #e2e3e5;" id="player-status">Sẵn sàng phát nội dung bài nghe</div>

                        <div class="subtitle-box" id="subtitle-container">
                            <div class="sub-en" id="clip-en"></div>
                            <div class="sub-vi" id="clip-vi"></div>
                        </div>

                        <div class="controls-row">
                            <button class="btn-blue" style="background-color: #198754;" onclick="playCurrentClip(1.0)">Nghe bình thường (1.0x)</button>
                            <button class="btn-dark-blue" onclick="playCurrentClip(0.65)">Nghe chậm (0.65x)</button>
                            <button class="btn-blue" style="background-color: #dc3545;" onclick="stopClip()">Dừng phát</button>
                            <button class="btn-outline-blue" id="btn-toggle-sub" onclick="toggleSubtitle()">Ẩn phụ đề</button>
                        </div>
                    </div>
                </div>

                <div class="video-sidebar">
                    <div style="font-weight: bold; color: #0d6efd; font-size: 15px; margin-bottom: 10px; border-bottom: 1px solid #dee2e6; padding-bottom: 6px;">
                        Từ vựng trọng tâm trong bài
                    </div>
                    <div id="related-vocab-list"></div>

                    <div style="font-weight: bold; color: #084298; font-size: 15px; margin-top: 16px; margin-bottom: 8px; border-bottom: 1px solid #dee2e6; padding-bottom: 6px;">
                        Chủ điểm Ngữ pháp liên quan
                    </div>
                    <div id="related-grammar-box"></div>
                </div>
            </div>
        </div>

        <!-- PANEL 2: TỪ ĐIỂN AI & PHÁT ÂM -->
        <div id="panel-dict" class="dropdown-panel">
            <div class="input-group">
                <input type="text" id="dict-input" placeholder="Nhập từ vựng hoặc thuật ngữ tiếng Anh (VD: epidemiology, hypothesis)..." onkeypress="if(event.key==='Enter') lookupWord()">
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
                    <option value="medical">Chủ đề: Y khoa & Nghiên cứu Khoa học</option>
                    <option value="academic">Chủ đề: Hội thảo & Thuyết trình Quốc tế</option>
                    <option value="daily">Chủ đề: Giao tiếp Công việc & Đời sống</option>
                </select>
                <button class="btn-outline-blue" onclick="loadNextSentence()">Đổi câu mẫu khác</button>
            </div>
            <div class="sample-sentence-box">
                <div style="font-size: 12px; color: #0d6efd; font-weight: bold; margin-bottom: 4px;">CÂU MẪU LUYỆN ĐỌC:</div>
                <span id="target-sentence">Statistical thinking is essential for evidence-based medical research.</span>
                <div style="margin-top: 10px;">
                    <button class="btn-blue" onclick="speakText(document.getElementById('target-sentence').innerText, 0.95)">Nghe mẫu chuẩn</button>
                    <button class="btn-outline-blue" onclick="speakText(document.getElementById('target-sentence').innerText, 0.65)">Nghe chậm</button>
                </div>
                <div id="target-vi" style="font-size: 14px; color: #555; margin-top: 8px; font-weight: normal; font-style: italic;">
                    (Tư duy thống kê là yếu tố thiết yếu cho nghiên cứu y học dựa trên bằng chứng.)
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
                    <b>AI English Tutor:</b> Xin chào! Hãy nhập một câu tiếng Việt bạn muốn diễn đạt sang tiếng Anh tự nhiên, hoặc viết một câu tiếng Anh để tôi kiểm tra ngữ pháp và gợi ý cách diễn đạt học thuật hơn.
                </div>
            </div>
            <div class="input-group">
                <input type="text" id="chat-input" placeholder="Nhập câu tiếng Việt cần diễn đạt hoặc câu tiếng Anh cần sửa..." onkeypress="if(event.key==='Enter') sendTutorMessage()">
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

            const LESSON_DATA = {
                biostat: [
                    {
                        en: "In biomedical research, selecting an appropriate statistical test is crucial to avoid false-positive conclusions and ensure the validity of clinical findings.",
                        vi: "Trong nghiên cứu y sinh, việc lựa chọn kiểm định thống kê phù hợp là rất quan trọng để tránh các kết luận dương tính giả và đảm bảo tính giá trị của các phát hiện lâm sàng.",
                        vocab: [
                            { word: "biomedical", ipa: "/ˌbaɪ.oʊˈmed.ɪ.kəl/", mean: "thuộc về y sinh học" },
                            { word: "crucial", ipa: "/ˈkruː.ʃəl/", mean: "quan trọng, cốt yếu" },
                            { word: "false-positive", ipa: "/ˌfɔːls ˈpɑː.zə.tɪv/", mean: "dương tính giả" },
                            { word: "validity", ipa: "/vəˈlɪd.ə.t̬i/", mean: "tính giá trị, độ xác thực" }
                        ],
                        grammar: {
                            title: "Danh động từ (Gerund) làm chủ ngữ & Mệnh đề chỉ mục đích",
                            rule: "V-ing (Selecting...) + is + Adj + to V-infinitive (to avoid...)",
                            example: "Selecting the right sample size is essential to achieve adequate statistical power."
                        }
                    },
                    {
                        en: "Although multivariate logistic regression adjusts for potential confounding variables, researchers must still verify the goodness-of-fit of the final model.",
                        vi: "Mặc dù hồi quy logistic đa biến hiệu chỉnh cho các biến gây nhiễu tiềm ẩn, các nhà nghiên cứu vẫn phải kiểm tra độ phù hợp của mô hình cuối cùng.",
                        vocab: [
                            { word: "multivariate", ipa: "/ˌmʌl.tiˈver.i.ət/", mean: "đa biến" },
                            { word: "confounding variable", ipa: "/kənˈfaʊn.dɪŋ ˈver.i.ə.bəl/", mean: "biến gây nhiễu" },
                            { word: "goodness-of-fit", ipa: "/ˌɡʊd.nəs əv ˈfɪt/", mean: "độ phù hợp của mô hình" }
                        ],
                        grammar: {
                            title: "Mệnh đề nhượng bộ với Although & Động từ khuyết thiếu Must",
                            rule: "Although + S + V, S + must + V-bare",
                            example: "Although the p-value is significant, we must evaluate the clinical relevance."
                        }
                    }
                ],
                pharma: [
                    {
                        en: "Randomized controlled trials remain the gold standard for evaluating the efficacy and safety profile of novel pharmaceutical formulations before regulatory approval.",
                        vi: "Các thử nghiệm ngẫu nhiên có đối chứng vẫn là tiêu chuẩn vàng để đánh giá hiệu quả và hồ sơ an toàn của các công thức dược phẩm mới trước khi được cơ quan quản lý phê duyệt.",
                        vocab: [
                            { word: "efficacy", ipa: "/ˈef.ə.kə.si/", mean: "hiệu lực, hiệu quả điều trị" },
                            { word: "formulation", ipa: "/ˌfɔːr.mjəˈleɪ.ʃən/", mean: "công thức bào chế" },
                            { word: "regulatory approval", ipa: "/ˈreɡ.jə.lə.tɔːr.i əˈpruː.vəl/", mean: "sự phê duyệt của cơ quan quản lý" }
                        ],
                        grammar: {
                            title: "Giới từ đi kèm Danh động từ (Preposition + V-ing)",
                            rule: "Noun + for + V-ing (evaluating...)",
                            example: "This protocol is designed for monitoring adverse drug reactions in patients."
                        }
                    }
                ],
                conference: [
                    {
                        en: "Distinguished guests and colleagues, it is my great honor to present our institution's latest longitudinal study on chronic disease management.",
                        vi: "Kính thưa quý vị đại biểu và các đồng nghiệp, tôi rất vinh dự được trình bày nghiên cứu theo dõi dọc mới nhất của đơn vị chúng tôi về quản lý bệnh mạn tính.",
                        vocab: [
                            { word: "distinguished", ipa: "/dɪˈstɪŋ.ɡwɪʃt/", mean: "ưu tú, lỗi lạc, kính mến" },
                            { word: "longitudinal study", ipa: "/ˌlɑːn.dʒəˈtuː.dən.əl ˈstʌd.i/", mean: "nghiên cứu theo dõi dọc" },
                            { word: "chronic", ipa: "/ˈkrɑː.nɪk/", mean: "mạn tính, kéo dài" }
                        ],
                        grammar: {
                            title: "Chủ ngữ giả 'It' trong văn phong trang trọng hội nghị",
                            rule: "It is + my great honor / a privilege + to V-infinitive",
                            example: "It is a privilege to welcome international scholars to our university."
                        }
                    }
                ],
                admin: [
                    {
                        en: "Implementing a centralized data governance framework allows the university to streamline administrative workflows and enhance decision-making efficiency.",
                        vi: "Việc triển khai khung quản trị dữ liệu tập trung cho phép trường đại học tinh gọn quy trình hành chính và nâng cao hiệu quả ra quyết định.",
                        vocab: [
                            { word: "centralized", ipa: "/ˈsen.trə.laɪzd/", mean: "tập trung hóa" },
                            { word: "governance", ipa: "/ˈɡʌv.ɚ.nəns/", mean: "sự quản trị, điều hành" },
                            { word: "streamline", ipa: "/ˈstriːm.laɪn/", mean: "tinh gọn, hợp lý hóa" }
                        ],
                        grammar: {
                            title: "Cấu trúc cho phép / tạo điều kiện (Allow + Object + to V)",
                            rule: "S + allow(s) + O + to V1 + and + V2",
                            example: "Digital transformation allows staff to save time and reduce paperwork."
                        }
                    }
                ],
                ai_tech: [
                    {
                        en: "Artificial intelligence algorithms are increasingly integrated into diagnostic imaging to assist clinicians in detecting subtle pathological anomalies.",
                        vi: "Các thuật toán trí tuệ nhân tạo ngày càng được tích hợp vào chẩn đoán hình ảnh nhằm hỗ trợ các bác sĩ lâm sàng phát hiện những bất thường bệnh lý tinh vi.",
                        vocab: [
                            { word: "algorithm", ipa: "/ˈæl.ɡə.rɪ.ðəm/", mean: "thuật toán" },
                            { word: "clinician", ipa: "/klɪˈnɪʃ.ən/", mean: "bác sĩ lâm sàng" },
                            { word: "anomaly", ipa: "/əˈnɑː.mə.li/", mean: "sự bất thường, dị thường" }
                        ],
                        grammar: {
                            title: "Thể bị động hiện tại tiếp diễn với Trạng từ bổ nghĩa",
                            rule: "S + are + Adv (increasingly) + V3/ed (integrated) + into + N",
                            example: "Machine learning models are widely applied in predictive healthcare analytics."
                        }
                    }
                ],
                negotiation: [
                    {
                        en: "We are keen to establish a mutually beneficial partnership that fosters academic exchange and joint research initiatives between our two institutions.",
                        vi: "Chúng tôi mong muốn thiết lập mối quan hệ đối tác cùng có lợi nhằm thúc đẩy trao đổi học thuật và các sáng kiến nghiên cứu chung giữa hai đơn vị.",
                        vocab: [
                            { word: "mutually beneficial", ipa: "/ˈmjuː.tʃu.ə.li ˌben.əˈfɪʃ.əl/", mean: "cùng có lợi" },
                            { word: "foster", ipa: "/ˈfɑː.stɚ/", mean: "thúc đẩy, bồi dưỡng" },
                            { word: "initiative", ipa: "/ɪˈnɪʃ.ə.t̬ɪv/", mean: "sáng kiến, chương trình" }
                        ],
                        grammar: {
                            title: "Mệnh đề quan hệ xác định dùng 'That'",
                            rule: "Noun + that + V (fosters) + O",
                            example: "We signed a memorandum of understanding that promotes faculty mobility."
                        }
                    }
                ],
                travel: [
                    {
                        en: "Excuse me, could you direct me to the international transfer desk? My connecting flight was delayed due to inclement weather conditions.",
                        vi: "Xin lỗi, bạn có thể chỉ cho tôi đường đến quầy nối chuyến quốc tế không? Chuyến bay nối chuyến của tôi bị hoãn do điều kiện thời tiết xấu.",
                        vocab: [
                            { word: "connecting flight", ipa: "/kəˈnek.tɪŋ flaɪt/", mean: "chuyến bay nối chuyến" },
                            { word: "inclement", ipa: "/ɪnˈklem.ənt/", mean: "khắc nghiệt, xấu (thời tiết)" },
                            { word: "transfer desk", ipa: "/ˈtræns.fɝː desk/", mean: "quầy làm thủ tục chuyển tiếp" }
                        ],
                        grammar: {
                            title: "Câu hỏi đề nghị lịch sự với 'Could you' & Cụm giới từ 'Due to'",
                            rule: "Could you + V-bare...? / S + was V3 + due to + Noun Phrase",
                            example: "Could you confirm my reservation? The schedule changed due to heavy traffic."
                        }
                    }
                ],
                daily: [
                    {
                        en: "Let us review the agenda items briefly so that everyone is aligned on the key deliverables before the end of this week.",
                        vi: "Hãy cùng xem lướt qua các mục trong chương trình nghị sự để mọi người thống nhất về các đầu việc chính trước cuối tuần này.",
                        vocab: [
                            { word: "agenda", ipa: "/əˈdʒen.də/", mean: "chương trình nghị sự, nội dung họp" },
                            { word: "aligned", ipa: "/əˈlaɪnd/", mean: "thống nhất, đồng thuận" },
                            { word: "deliverable", ipa: "/dɪˈlɪv.ɚ.ə.bəl/", mean: "sản phẩm/kết quả đầu ra cần bàn giao" }
                        ],
                        grammar: {
                            title: "Cấu trúc rủ rê 'Let us' & Mệnh đề chỉ mục đích 'So that'",
                            rule: "Let us + V-bare + so that + S + V",
                            example: "Let us finalize the logistics checklist so that the event runs smoothly."
                        }
                    }
                ]
            };

            let currentTopicKey = "biostat";
            let currentClipIndex = 0;
            let isSubVisible = true;
            let customClipsList = null;

            function renderLessonObject(clip, badgeText) {
                document.getElementById('clip-badge').innerText = badgeText;
                document.getElementById('clip-en').innerText = clip.en;
                document.getElementById('clip-vi').innerText = clip.vi;

                let vocabHtml = "";
                clip.vocab.forEach(v => {
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
                        <div style="font-weight:bold; color:#084298; font-size:14px; margin-bottom:5px;">${clip.grammar.title}</div>
                        <div style="background:#ffffff; padding:6px 8px; border-radius:4px; font-family:monospace; font-size:12px; color:#d63384; margin-bottom:6px;">
                            ${clip.grammar.rule}
                        </div>
                        <div style="font-size:13px; color:#333;">
                            <b>Ví dụ mở rộng:</b> <i>"${clip.grammar.example}"</i>
                            <button class="btn-outline-blue" style="padding:2px 7px; font-size:11px; margin-left:5px;" onclick="speakText('${clip.grammar.example.replace(/'/g, "\\'")}', 0.95)">Nghe</button>
                        </div>
                    </div>
                `;
            }

            function renderVideoLesson() {
                let clips = customClipsList ? customClipsList : LESSON_DATA[currentTopicKey];
                let clip = clips[currentClipIndex];
                let badge = customClipsList ? `CHỦ ĐỀ TỰ CHỌN - ĐOẠN 0${currentClipIndex + 1} / 0${clips.length}` : `BÀI NGHE THỰC TẾ 0${currentClipIndex + 1} / 0${clips.length}`;
                renderLessonObject(clip, badge);
            }

            function changeVideoLesson() {
                stopClip();
                customClipsList = null;
                currentTopicKey = document.getElementById('video-topic-select').value;
                currentClipIndex = 0;
                renderVideoLesson();
            }

            function nextClipInTopic() {
                stopClip();
                let clips = customClipsList ? customClipsList : LESSON_DATA[currentTopicKey];
                currentClipIndex = (currentClipIndex + 1) % clips.length;
                renderVideoLesson();
            }

            // Tự động tạo bài học AI từ bất kỳ chủ đề nào người dùng nhập vào
            async function generateCustomTopic() {
                let rawTopic = document.getElementById('custom-topic-input').value.trim();
                if (!rawTopic) {
                    alert("Vui lòng nhập chủ đề bạn muốn học vào ô trống!");
                    return;
                }
                stopClip();
                let btn = document.getElementById('btn-gen-topic');
                btn.innerText = "Đang tạo dữ liệu...";
                btn.disabled = true;

                try {
                    // Dịch chủ đề sang tiếng Anh nếu người dùng gõ tiếng Việt
                    let enTopic = rawTopic;
                    if (/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(rawTopic)) {
                        enTopic = await translateText(rawTopic, 'vi', 'en');
                    }

                    // Tìm kiếm đoạn văn học thuật/thực tế liên quan từ Wikipedia API
                    let enParagraph = "";
                    try {
                        let searchRes = await fetch(`https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(enTopic)}&format=json&origin=*`);
                        let searchData = await searchRes.json();
                        if (searchData.query && searchData.query.search.length > 0) {
                            let pageTitle = searchData.query.search[0].title;
                            let summaryRes = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(pageTitle)}`);
                            let summaryData = await summaryRes.json();
                            if (summaryData.extract) {
                                // Lấy 2 câu đầu tiên súc tích nhất
                                let sentences = summaryData.extract.match(/[^.!?]+[.!?]+/g) || [summaryData.extract];
                                enParagraph = sentences.slice(0, 2).join(" ").trim();
                            }
                        }
                    } catch(e) {}

                    // Dự phòng nếu chủ đề mang tính hội thoại đời thường không có trên Wiki
                    if (!enParagraph) {
                        enParagraph = `In today's session, we will focus on practical communication and specialized terminology regarding ${enTopic}. Mastering these expressions will significantly improve your fluency and confidence in professional discussions.`;
                    }

                    let viParagraph = await translateText(enParagraph, 'en', 'vi');

                    // Trích xuất các từ khóa dài (> 6 ký tự) để làm danh sách từ vựng trọng tâm
                    let words = enParagraph.replace(/[^a-zA-Z\s]/g, "").split(/\s+/);
                    let uniqueLongWords = [...new Set(words.filter(w => w.length >= 7))].slice(0, 4);
                    if (uniqueLongWords.length === 0) uniqueLongWords = enTopic.split(/\s+/).slice(0, 3);

                    let vocabItems = [];
                    for (let w of uniqueLongWords) {
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
                        vocabItems.push({ word: cleanW, ipa: ipaStr, mean: meanVi });
                    }

                    // Phân tích ngữ pháp tự động dựa trên câu vừa tạo
                    let grammarInfo = {
                        title: "Cấu trúc Câu phức Học thuật & Cụm danh từ chuyên ngành",
                        rule: "Prepositional Phrase + S + V (Present/Future) + Object",
                        example: `Understanding the core principles of ${enTopic} is essential for effective communication.`
                    };
                    if (enParagraph.includes(" which ") || enParagraph.includes(" that ")) {
                        grammarInfo = {
                            title: "Mệnh đề quan hệ mở rộng thông tin (Relative Clauses)",
                            rule: "Noun + which / that + V + O",
                            example: `We examined the factors that influence ${enTopic} in real-world settings.`
                        };
                    } else if (/\b(is|are|was|were)\s+\w+ed\b/.test(enParagraph)) {
                        grammarInfo = {
                            title: "Câu bị động khách quan trong văn phong khoa học (Passive Voice)",
                            rule: "S + to be + V3/ed (Past Participle)",
                            example: `Various methodologies are applied when analyzing ${enTopic}.`
                        };
                    }

                    customClipsList = [{
                        en: enParagraph,
                        vi: viParagraph,
                        vocab: vocabItems,
                        grammar: grammarInfo
                    }];
                    currentClipIndex = 0;
                    renderLessonObject(customClipsList[0], `CHỦ ĐỀ TỰ CHỌN: ${rawTopic.toUpperCase()}`);
                } catch (err) {
                    alert("Có lỗi khi kết nối dữ liệu chủ đề, vui lòng thử lại!");
                } finally {
                    btn.innerText = "Tạo bài học AI theo chủ đề";
                    btn.disabled = false;
                }
            }

            function playCurrentClip(rate) {
                let text = document.getElementById('clip-en').innerText;
                let wave = document.getElementById('wave-indicator');
                let status = document.getElementById('player-status');
                
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                    let utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = 'en-US';
                    utterance.rate = rate;
                    
                    utterance.onstart = function() {
                        wave.classList.add('playing');
                        status.innerText = rate === 1.0 ? "Đang phát tốc độ chuẩn (1.0x)..." : "Đang phát tốc độ chậm (0.65x) để luyện nghe rõ từng âm...";
                    };
                    utterance.onend = function() {
                        wave.classList.remove('playing');
                        status.innerText = "Đã phát xong đoạn hội thoại.";
                    };
                    window.speechSynthesis.speak(utterance);
                }
            }

            function stopClip() {
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
                let subBox = document.getElementById('subtitle-container');
                let btn = document.getElementById('btn-toggle-sub');
                if (isSubVisible) {
                    subBox.classList.remove('sub-hidden');
                    btn.innerText = "Ẩn phụ đề";
                } else {
                    subBox.classList.add('sub-hidden');
                    btn.innerText = "Hiện phụ đề";
                }
            }

            renderVideoLesson();

            function speakText(text, rate = 1.0) {
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
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
                medical: [
                    { en: "Statistical thinking is essential for evidence-based medical research.", vi: "Tư duy thống kê là yếu tố thiết yếu cho nghiên cứu y học dựa trên bằng chứng." },
                    { en: "The clinical trial demonstrated a significant improvement in patient outcomes.", vi: "Thử nghiệm lâm sàng đã chứng minh sự cải thiện đáng kể về kết quả điều trị của bệnh nhân." },
                    { en: "Multivariate logistic regression was performed to identify independent risk factors.", vi: "Hồi quy logistic đa biến đã được thực hiện để xác định các yếu tố nguy cơ độc lập." }
                ],
                academic: [
                    { en: "Thank you for the opportunity to present our latest research findings today.", vi: "Cảm ơn vì cơ hội được trình bày những phát hiện nghiên cứu mới nhất của chúng tôi hôm nay." },
                    { en: "As shown in the figure, there is a strong correlation between the two variables.", vi: "Như được thể hiện trong biểu đồ, có một mối tương quan chặt chẽ giữa hai biến số." }
                ],
                daily: [
                    { en: "Could you please share the presentation slides before the meeting starts?", vi: "Bạn có thể vui lòng chia sẻ các trang trình bày trước khi cuộc họp bắt đầu không?" },
                    { en: "Let us schedule a follow-up discussion next week to finalize the plan.", vi: "Hãy lên lịch thảo luận tiếp theo vào tuần tới để hoàn thiện kế hoạch." }
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
    components.html(english_tutor_html, height=720)
