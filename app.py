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
    .stTabs button[data-baseweb="tab"] p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
        font-weight: bold !important;
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
    st.title("🔒 Đăng nhập Hệ thống Cabin Phiên dịch")
    pwd_input = st.text_input("Nhập mật khẩu truy cập:", type="password")
    if st.button("Đăng nhập"):
        if pwd_input:
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

tab1, tab2, tab3 = st.tabs([
    "💬 Dịch văn bản & Hội thoại", 
    "🎙 Cabin Phiên dịch Trực tiếp",
    "🎓 Học Tiếng Anh cùng AI"
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
                st.download_button("📥 Tải xuống file MP3", data=audio_bytes, file_name="phien_dich_ai.mp3", mime="audio/mp3", key="download_mp3_btn")
            except Exception:
                pass

# ==============================================================================
# TAB 2: CABIN PHIÊN DỊCH TRỰC TIẾP (DÙNG CHUỖI THƯỜNG AN TOÀN CÚ PHÁP)
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
            .btn-start { background-color: #28a745; }
            .btn-stop { background-color: #dc3545; }
            #status-badge { font-family: 'Times New Roman', Times, serif !important; margin-top: 10px; font-weight: bold; font-size: 13px !important; color: #28a745; }
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
            transSegments.push("[⚡...]");
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
                let color = t.includes("[⚡") ? "#888888" : "#28a745";
                let weight = t.includes("[⚡") ? "normal" : "bold";
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
# TAB 3: HỌC TIẾNG ANH CÙNG AI
# ==============================================================================
with tab3:
    st.subheader("Trợ lý Học Tiếng Anh Thông minh (AI English Tutor)")

    english_tutor_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f8f9fa; margin: 0; padding: 10px; color: #212529; }
            .tutor-nav { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
            .nav-btn { padding: 10px 18px; border: none; border-radius: 8px; background-color: #e9ecef; color: #495057; font-weight: bold; cursor: pointer; font-size: 14px; transition: 0.2s; }
            .nav-btn.active { background-color: #0d6efd; color: white; box-shadow: 0 2px 5px rgba(13,110,253,0.3); }
            .section-card { background: #ffffff; border: 1px solid #dee2e6; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); display: none; }
            .section-card.active { display: block; }
            .input-group { display: flex; gap: 10px; margin-bottom: 15px; }
            input[type="text"], select { flex: 1; padding: 10px 14px; border: 1px solid #ced4da; border-radius: 8px; font-size: 15px; }
            .action-btn { padding: 10px 20px; border: none; border-radius: 8px; background-color: #198754; color: white; font-weight: bold; cursor: pointer; font-size: 14px; }
            .speak-btn { background-color: #0dcaf0; color: #000; border: none; border-radius: 6px; padding: 6px 12px; font-weight: bold; cursor: pointer; font-size: 13px; margin-left: 8px; }
            .word-header { font-size: 24px; font-weight: bold; color: #0d6efd; margin-bottom: 5px; }
            .phonetic { color: #6c757d; font-size: 16px; font-family: monospace; margin-bottom: 12px; }
            .meaning-box { background: #f1f8ff; border-left: 4px solid #0d6efd; padding: 12px; border-radius: 6px; margin-bottom: 12px; }
            .sample-sentence-box { background: #fff3cd; border: 1px solid #ffe69c; padding: 15px; border-radius: 8px; font-size: 18px; font-weight: 500; margin-bottom: 15px; line-height: 1.5; }
            .score-circle { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 16px; margin-top: 10px; }
            .word-correct { color: #198754; font-weight: bold; }
            .word-wrong { color: #dc3545; text-decoration: line-through; }
            .chat-window { height: 320px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; background: #fdfdfd; margin-bottom: 12px; }
            .msg-user { background: #0d6efd; color: white; padding: 10px 14px; border-radius: 14px 14px 2px 14px; max-width: 80%; margin-left: auto; margin-bottom: 10px; font-size: 14px; }
            .msg-ai { background: #e9ecef; color: #212529; padding: 10px 14px; border-radius: 14px 14px 14px 2px; max-width: 85%; margin-right: auto; margin-bottom: 10px; font-size: 14px; line-height: 1.5; }
        </style>
    </head>
    <body>
        <div class="tutor-nav">
            <button class="nav-btn active" onclick="switchTab('dict', this)">📖 Từ điển AI & Phát âm</button>
            <button class="nav-btn" onclick="switchTab('speak', this)">🎤 Luyện Nói & Chấm điểm</button>
            <button class="nav-btn" onclick="switchTab('chat', this)">🤖 Gia sư Hội thoại Song ngữ</button>
        </div>

        <div id="sec-dict" class="section-card active">
            <div class="input-group">
                <input type="text" id="dict-input" placeholder="Nhập từ vựng hoặc thuật ngữ tiếng Anh (VD: epidemiology, hypothesis)..." onkeypress="if(event.key==='Enter') lookupWord()">
                <button class="action-btn" onclick="lookupWord()">Tra cứu</button>
            </div>
            <div id="dict-result">
                <p style="color: #6c757d; font-style: italic;">Nhập một từ tiếng Anh bất kỳ để xem nghĩa tiếng Việt, phiên âm quốc tế (IPA), ví dụ ngữ cảnh và nghe giọng đọc bản xứ.</p>
            </div>
        </div>

        <div id="sec-speak" class="section-card">
            <div class="input-group">
                <select id="topic-select" onchange="loadNextSentence()">
                    <option value="medical">Chủ đề: Y khoa & Nghiên cứu Khoa học</option>
                    <option value="academic">Chủ đề: Hội thảo & Thuyết trình Quốc tế</option>
                    <option value="daily">Chủ đề: Giao tiếp Công việc & Đời sống</option>
                </select>
                <button class="action-btn" style="background-color: #6c757d;" onclick="loadNextSentence()">Đổi câu khác ↻</button>
            </div>
            <div class="sample-sentence-box">
                <div style="font-size: 12px; color: #664d03; margin-bottom: 4px;">CÂU MẪU LUYỆN ĐỌC:</div>
                <span id="target-sentence">Statistical thinking is essential for evidence-based medical research.</span>
                <button class="speak-btn" onclick="speakText(document.getElementById('target-sentence').innerText, 0.9)">🔊 Nghe mẫu</button>
                <button class="speak-btn" style="background-color: #ffc107;" onclick="speakText(document.getElementById('target-sentence').innerText, 0.6)">🐢 Nghe chậm</button>
                <div id="target-vi" style="font-size: 14px; color: #555; margin-top: 6px; font-weight: normal; font-style: italic;">
                    (Tư duy thống kê là yếu tố thiết yếu cho nghiên cứu y học dựa trên bằng chứng.)
                </div>
            </div>
            <button id="btn-record-eval" class="action-btn" style="background-color: #dc3545; width: 100%; padding: 14px; font-size: 15px;" onclick="startPronunciationCheck()">
                🎙 BẤM ĐỂ ĐỌC CÂU TRÊN VÀ CHẤM ĐIỂM AI
            </button>
            <div id="speak-feedback" style="margin-top: 15px;"></div>
        </div>

        <div id="sec-chat" class="section-card">
            <div class="chat-window" id="chat-box">
                <div class="msg-ai">
                    <b>AI English Tutor:</b> Hello! Nhập một câu tiếng Việt bạn muốn diễn đạt sang tiếng Anh tự nhiên, hoặc viết một câu tiếng Anh để tôi kiểm tra ngữ pháp và gợi ý cách diễn đạt học thuật hơn nhé!
                </div>
            </div>
            <div class="input-group">
                <input type="text" id="chat-input" placeholder="Nhập câu tiếng Việt cần diễn đạt hoặc câu tiếng Anh cần sửa..." onkeypress="if(event.key==='Enter') sendTutorMessage()">
                <button class="action-btn" onclick="sendTutorMessage()">Gửi AI</button>
            </div>
        </div>

        <script>
            function switchTab(tabId, btn) {
                document.querySelectorAll('.section-card').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
                document.getElementById('sec-' + tabId).classList.add('active');
                btn.classList.add('active');
            }

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
                            defHtml += `<div style="margin-bottom: 8px;"><span style="background:#e2e3e5; padding:2px 6px; border-radius:4px; font-size:12px; font-weight:bold;">${m.partOfSpeech}</span><span> ${def.definition}</span>${def.example ? `<div style="color:#198754; font-style:italic; margin-top:3px;">VD: "${def.example}"</div>` : ''}</div>`;
                        });
                    }
                } catch(e) {}
                resDiv.innerHTML = `<div class="word-header">${word} <button class="speak-btn" onclick="speakText('${word.replace(/'/g, "\\'")}', 0.95)">🔊 Đọc chuẩn</button><button class="speak-btn" style="background:#ffc107;" onclick="speakText('${word.replace(/'/g, "\\'")}', 0.6)">🐢 Đọc chậm</button></div>${phonetic ? `<div class="phonetic">${phonetic}</div>` : ''}<div class="meaning-box"><b>Nghĩa tiếng Việt:</b> <span style="font-size:17px; color:#0d6efd; font-weight:bold;">${viMeaning}</span></div>${defHtml ? `<div><b>Giải nghĩa & Ngữ cảnh Anh - Anh:</b><div style="margin-top:8px;">${defHtml}</div></div>` : ''}`;
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
                btn.innerText = "🔴 ĐANG NGHE... HÃY ĐỌC TO CÂU MẪU...";
                btn.style.backgroundColor = "#fd7e14";
                rec.onresult = function(event) { evaluateSpeech(targetText, event.results[0][0].transcript); };
                rec.onerror = function(e) { document.getElementById('speak-feedback').innerHTML = `<div style="color:#dc3545;">Lỗi micro (${e.error}). Hãy thử lại!</div>`; };
                rec.onend = function() { btn.innerText = "🎙 BẤM ĐỂ ĐỌC CÂU TRÊN VÀ CHẤM ĐIỂM AI"; btn.style.backgroundColor = "#dc3545"; };
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
                let badgeColor = score >= 80 ? "#d1e7dd; color:#0f5132" : (score >= 50 ? "#fff3cd; color:#664d03" : "#f8d7da; color:#842029");
                let comment = score >= 80 ? "Xuất sắc! Phát âm rất chuẩn xác." : (score >= 50 ? "Khá tốt! Chú ý các từ gạch đỏ." : "Cần luyện thêm! Hãy bấm 'Nghe chậm' và đọc lại.");
                document.getElementById('speak-feedback').innerHTML = `<div style="background:#f8f9fa; border:1px solid #dee2e6; border-radius:8px; padding:15px;"><div><b>AI nghe được:</b> <i>"${spoken}"</i></div><div style="margin-top:8px;"><b>Đối chiếu:</b> ${highlightedHtml}</div><div class="score-circle" style="background:${badgeColor};">Điểm phát âm: ${score}/100</div><div style="margin-top:8px; font-size:14px;">💡 ${comment}</div></div>`;
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
                    chatBox.innerHTML += `<div class="msg-ai"><b>Diễn đạt Tiếng Anh tự nhiên:</b><br><span style="color:#0d6efd; font-weight:bold; font-size:15px;">"${enTrans}"</span> <button class="speak-btn" onclick="speakText('${enTrans.replace(/'/g, "\\'")}', 0.95)">🔊 Nghe</button></div>`;
                    speakText(enTrans, 0.95);
                } else {
                    let viMeaning = await translateText(text, 'en', 'vi');
                    let polishedEn = await translateText(viMeaning, 'vi', 'en');
                    chatBox.innerHTML += `<div class="msg-ai"><b>Phân tích câu của bạn:</b><br>• <b>Nghĩa tiếng Việt:</b> ${viMeaning}<br>• <b>Gợi ý mượt hơn:</b> <span style="color:#198754; font-weight:bold;">"${polishedEn}"</span> <button class="speak-btn" onclick="speakText('${polishedEn.replace(/'/g, "\\'")}', 0.95)">🔊 Nghe mẫu</button></div>`;
                    speakText(polishedEn, 0.95);
                }
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    components.html(english_tutor_html, height=620)
