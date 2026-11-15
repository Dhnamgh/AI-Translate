import io
import re
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
    /* Chống tràn ngang toàn trang trên điện thoại */
    html, body, [data-testid="stAppViewContainer"] {
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    h1, h2, h3, h4, h5, h6, 
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
    }
    
    .stSelectbox label p, .stTextArea label p, .stSlider label p, .stFileUploader label p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
        font-weight: bold !important;
    }
    
    .stButton button p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
    }

    /* Thanh Tab Menu màu xanh đồng bộ, tự co giãn trên mọi màn hình */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0d6efd;
        padding: 6px 6px 0px 6px;
        border-radius: 8px 8px 0px 0px;
        gap: 4px;
        border-bottom: 2px solid #0a58ca;
        display: flex;
        flex-wrap: wrap;
    }

    .stTabs button[data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.15);
        color: #ffffff !important;
        border-radius: 6px 6px 0px 0px;
        padding: 8px 12px;
        border: none !important;
        flex: 1 1 auto;
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
        font-size: 13px !important;
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
        padding: 12px;
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
        word-wrap: break-word;
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

def extract_uploaded_document(uploaded_file):
    if uploaded_file is None:
        return ""
    file_name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()
    text_content = ""

    if file_name.endswith(".txt"):
        text_content = raw_bytes.decode("utf-8", errors="ignore")
    elif file_name.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(raw_bytes))
            text_content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except ImportError:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                paragraphs = []
                for elem in tree.iter():
                    if elem.tag.endswith('}p'):
                        texts = [t.text for t in elem.iter() if t.tag.endswith('}t') and t.text]
                        if texts:
                            paragraphs.append("".join(texts))
                text_content = "\n".join(paragraphs)
    elif file_name.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            text_content = "\n".join(pages)
        except ImportError:
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
                pages = [page.extract_text() or "" for page in reader.pages]
                text_content = "\n".join(pages)
            except ImportError:
                return "[Vui lòng thêm thư viện pypdf vào requirements.txt để đọc file PDF]"
    return text_content.strip()

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
# TAB 1: BỐ CỤC 2 CỘT NGANG HÀNG (KHÓA CỨNG)
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
# TAB 2: CABIN PHIÊN DỊCH TRỰC TIẾP (KHÓA CỨNG)
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
            * { box-sizing: border-box; }
            .cabin-box { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 12px; padding: 12px; text-align: center; width: 100%; }
            .btn-control { font-family: 'Times New Roman', Times, serif !important; padding: 10px 18px; font-size: 14px !important; font-weight: bold; border-radius: 8px; border: none; cursor: pointer; margin: 4px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .btn-start { background-color: #0d6efd; }
            .btn-stop { background-color: #dc3545; }
            #status-badge { font-family: 'Times New Roman', Times, serif !important; margin-top: 8px; font-weight: bold; font-size: 13px !important; color: #0d6efd; }
            .cabin-grid { display: flex; flex-direction: row; gap: 12px; margin-top: 12px; }
            .cabin-panel { flex: 1; background: #ffffff; border: 1px solid #ced4da; border-radius: 8px; padding: 12px; text-align: left; height: 460px; overflow-y: auto; box-shadow: inset 0 0 5px rgba(0,0,0,0.05); }
            .panel-title { font-family: 'Times New Roman', Times, serif !important; font-weight: bold; font-size: 14px !important; margin-bottom: 10px; border-bottom: 1px solid #e9ecef; padding-bottom: 5px; }
            .panel-content { font-size: 15px; line-height: 1.6; word-wrap: break-word; }
            @media (max-width: 768px) { .cabin-grid { flex-direction: column; } .cabin-panel { height: 260px; } }
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
    components.html(cabin_html_code, height=700, scrolling=True)

# ==============================================================================
# TAB 3: HỌC TIẾNG ANH CÙNG AI (TRÌNH CHIẾU VIDEO + PHÂN VAI GIỌNG NAM / NỮ)
# ==============================================================================
with tab3:
    st.subheader("Hệ thống Học Tiếng Anh & Soạn Bài giảng từ Tài liệu")

    with st.expander("Tải tài liệu lên (Word .docx / PDF .pdf / TXT) để tạo bài học tự động", expanded=False):
        uploaded_doc = st.file_uploader("Chọn file bài giảng, bài báo hoặc tài liệu giao tiếp:", type=["docx", "pdf", "txt"], key="t3_doc_upload")
        if uploaded_doc is not None:
            if st.button("Phân tích & Tạo bài học từ file đã tải lên", type="primary", key="btn_process_doc"):
                with st.spinner("Đang đọc tài liệu và trích xuất nội dung học tập..."):
                    extracted = extract_uploaded_document(uploaded_doc)
                    if extracted and not extracted.startswith("[Vui lòng"):
                        clean_doc = re.sub(r'\n+', '\n', extracted)[:2500]
                        raw_paras = [p.strip() for p in clean_doc.split('\n') if len(p.strip()) > 15][:5]
                        is_vi_doc = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', clean_doc, re.I))
                        
                        doc_sections = []
                        all_en_text = ""
                        for idx, p in enumerate(raw_paras):
                            if is_vi_doc:
                                en_p = translate_stable(p, "vi", "en")
                                vi_p = p
                            else:
                                en_p = p
                                vi_p = translate_stable(p, "en", "vi")
                            all_en_text += " " + en_p
                            doc_sections.append({
                                "heading": f"Phần {idx + 1}: Nội dung trích xuất từ tài liệu",
                                "en": en_p,
                                "vi": vi_p
                            })

                        words = re.findall(r'\b[a-zA-Z]{7,}\b', all_en_text)
                        unique_words = list(dict.fromkeys([w.lower() for w in words]))[:6]
                        vocab_extracted = []
                        for w in unique_words:
                            mean_w = translate_stable(w, "en", "vi")
                            vocab_extracted.append({"word": w, "mean": mean_w})

                        st.session_state["uploaded_lecture_json"] = json.dumps({
                            "title": f"BÀI HỌC TỪ TÀI LIỆU: {uploaded_doc.name.upper()}",
                            "sections": doc_sections,
                            "vocab": vocab_extracted
                        }, ensure_ascii=False)
                        st.success("Đã tạo xong bài học từ tài liệu! Xem nội dung chi tiết ở khung bên dưới.")
                    else:
                        st.warning(extracted or "Không tìm thấy văn bản trong file.")

    uploaded_json_str = st.session_state.get("uploaded_lecture_json", "null")

    english_tutor_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            * { box-sizing: border-box; }
            html, body {
                width: 100%;
                max-width: 100%;
                overflow-x: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #f4f6f9;
                margin: 0;
                padding: 4px;
                color: #212529;
            }
            .blue-menu-bar {
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                background-color: #0d6efd;
                border-radius: 8px;
                padding: 4px;
                gap: 4px;
                margin-bottom: 10px;
                width: 100%;
            }
            @media (max-width: 850px) {
                .blue-menu-bar { grid-template-columns: repeat(2, 1fr); }
            }
            .menu-item {
                padding: 9px 8px;
                border: none;
                border-radius: 6px;
                background-color: transparent;
                color: #ffffff;
                font-weight: bold;
                cursor: pointer;
                font-size: 12px;
                text-align: center;
                transition: all 0.2s ease;
                display: flex;
                justify-content: space-between;
                align-items: center;
                word-break: break-word;
            }
            .menu-item:hover { background-color: rgba(255, 255, 255, 0.2); }
            .menu-item.active {
                background-color: #ffffff;
                color: #0d6efd;
                box-shadow: 0 2px 5px rgba(0,0,0,0.12);
            }
            .arrow-icon { font-size: 9px; margin-left: 4px; flex-shrink: 0; }
            .menu-item.active .arrow-icon { transform: rotate(180deg); }

            .dropdown-panel {
                background: #ffffff;
                border: 1px solid #cfe2ff;
                border-top: 4px solid #0d6efd;
                border-radius: 8px;
                padding: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                display: none;
                width: 100%;
            }
            .dropdown-panel.active { display: block; }

            .topic-control-box {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 12px;
                width: 100%;
            }
            .input-group { display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; width: 100%; }
            .input-group:last-child { margin-bottom: 0; }
            input[type="text"], select {
                flex: 1 1 200px;
                width: 100%;
                max-width: 100%;
                padding: 9px 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
            }
            .btn-blue, .btn-outline-blue, .btn-dark-blue, .btn-word {
                padding: 9px 12px;
                border-radius: 6px;
                font-weight: bold;
                cursor: pointer;
                font-size: 12px;
                flex-shrink: 0;
            }
            .btn-blue { border: none; background-color: #0d6efd; color: white; }
            .btn-outline-blue { border: 1px solid #0d6efd; background-color: #ffffff; color: #0d6efd; }
            .btn-dark-blue { border: none; background-color: #084298; color: #ffffff; }
            .btn-word { border: none; background-color: #198754; color: #ffffff; }

            /* Khung hiển thị bài viết */
            .lecture-scroll-box {
                width: 100%;
                max-width: 100%;
                height: 440px;
                overflow-y: auto;
                overflow-x: hidden;
                border: 1px solid #b6d4fe;
                border-radius: 8px;
                background-color: #ffffff;
                padding: 14px;
                box-shadow: inset 0 0 6px rgba(0,0,0,0.04);
                font-family: 'Times New Roman', Times, serif;
            }
            .lecture-inner-content { width: 100%; max-width: 100%; line-height: 1.6; font-size: 15px; word-wrap: break-word; overflow-wrap: break-word; }
            .lecture-title { font-size: 16px; font-weight: bold; color: #084298; border-bottom: 2px solid #0d6efd; padding-bottom: 6px; margin-bottom: 12px; text-transform: uppercase; }
            .lecture-section { margin-bottom: 14px; padding: 10px; background: #f8f9fa; border-left: 4px solid #0d6efd; border-radius: 4px; }
            .sec-heading { font-weight: bold; color: #0d6efd; font-size: 14px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }
            .sec-en { color: #111111; font-size: 14.5px; margin-bottom: 6px; }
            .sec-vi { color: #495057; font-style: italic; font-size: 13.5px; border-top: 1px dashed #ced4da; padding-top: 5px; }

            /* Bố cục Video + Hội thoại đa vai Nam/Nữ */
            .video-layout { display: flex; gap: 12px; flex-direction: row; width: 100%; }
            @media (max-width: 768px) { .video-layout { flex-direction: column; } }
            .video-main { flex: 1.4; width: 100%; }
            .video-sidebar { flex: 1; width: 100%; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; }

            .media-screen {
                background: linear-gradient(135deg, #0a2540 0%, #0d6efd 100%);
                color: white;
                border-radius: 10px;
                padding: 14px 12px;
                width: 100%;
            }
            .video-frame-wrapper {
                width: 100%;
                border-radius: 8px;
                overflow: hidden;
                background: #000000;
                margin-bottom: 10px;
                border: 2px solid rgba(255,255,255,0.25);
                position: relative;
            }
            .video-frame-wrapper video {
                width: 100%;
                height: 220px;
                object-fit: cover;
                display: block;
            }
            .video-overlay-caption {
                background: rgba(0, 0, 0, 0.75);
                padding: 8px 12px;
                text-align: center;
                border-top: 1px solid rgba(255,255,255,0.15);
            }
            .wave-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid rgba(255,255,255,0.2);
                padding-bottom: 8px;
                margin-bottom: 10px;
                flex-wrap: wrap;
                gap: 4px;
            }
            .wave-bars { display: flex; align-items: center; gap: 4px; height: 18px; }
            .bar { width: 4px; height: 8px; background: #6ea8fe; border-radius: 2px; }
            .playing .bar { animation: soundWave 0.5s infinite alternate; }
            @keyframes soundWave { from { height: 6px; } to { height: 18px; background: #fff; } }

            .dialogue-container {
                background: rgba(0, 0, 0, 0.35);
                border-radius: 8px;
                padding: 10px;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .turn-box {
                background: rgba(255, 255, 255, 0.12);
                border-left: 4px solid #38bdf8;
                padding: 8px 10px;
                border-radius: 6px;
                text-align: left;
                word-wrap: break-word;
                transition: all 0.2s ease;
            }
            .turn-box.role-female {
                background: rgba(255, 255, 255, 0.18);
                border-left: 4px solid #f472b6;
            }
            .turn-box.speaking-active {
                background: rgba(255, 255, 255, 0.35) !important;
                box-shadow: 0 0 10px rgba(255, 255, 255, 0.4);
                transform: scale(1.01);
            }
            .role-label { font-size: 11px; font-weight: bold; color: #7dd3fc; margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px; }
            .role-female .role-label { color: #fbcfe8; }
            .sub-en { font-size: 14px; font-weight: bold; color: #ffffff; line-height: 1.45; }
            .sub-vi { font-size: 13px; color: #cfe2ff; margin-top: 4px; font-style: italic; }
            .sub-hidden { filter: blur(5px); user-select: none; opacity: 0.35; }
            .controls-row { display: flex; gap: 6px; justify-content: center; margin-top: 12px; flex-wrap: wrap; }

            .vocab-card { background: #ffffff; border-left: 4px solid #0d6efd; border-radius: 6px; padding: 8px 10px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
            .grammar-card { background: #e7f1ff; border: 1px solid #b6d4fe; border-radius: 6px; padding: 10px; margin-top: 8px; word-wrap: break-word; }
            .word-header { font-size: 18px; font-weight: bold; color: #0d6efd; margin-bottom: 4px; }
            .phonetic { color: #6c757d; font-size: 13px; font-family: monospace; margin-bottom: 8px; }
            .meaning-box { background: #f1f8ff; border-left: 4px solid #0d6efd; padding: 10px; border-radius: 6px; margin-bottom: 10px; }
            .sample-sentence-box { background: #f8f9fa; border: 1px solid #dee2e6; padding: 12px; border-radius: 8px; font-size: 15px; font-weight: 500; margin-bottom: 12px; line-height: 1.5; word-wrap: break-word; }
            .score-circle { display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; margin-top: 8px; }
            .word-correct { color: #198754; font-weight: bold; }
            .word-wrong { color: #dc3545; text-decoration: line-through; }
            .chat-window { height: 260px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; background: #fdfdfd; margin-bottom: 10px; }
            .msg-user { background: #0d6efd; color: white; padding: 8px 12px; border-radius: 12px 12px 2px 12px; max-width: 85%; margin-left: auto; margin-bottom: 8px; font-size: 13.5px; word-wrap: break-word; }
            .msg-ai { background: #e9ecef; color: #212529; padding: 8px 12px; border-radius: 12px 12px 12px 2px; max-width: 90%; margin-right: auto; margin-bottom: 8px; font-size: 13.5px; line-height: 1.45; word-wrap: break-word; }
        </style>
    </head>
    <body>
        <div class="blue-menu-bar">
            <button class="menu-item active" onclick="openPanel('video', this)">
                <span>Video & Hội thoại</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('lecture', this)">
                <span>Bài viết & Kịch bản</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('dict', this)">
                <span>Từ điển & Phát âm</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('speak', this)">
                <span>Luyện Nói AI</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="openPanel('chat', this)">
                <span>Gia sư Song ngữ</span>
                <span class="arrow-icon">▼</span>
            </button>
        </div>

        <!-- PANEL 1: XEM VIDEO & HỘI THOẠI PHÂN VAI NAM / NỮ -->
        <div id="panel-video" class="dropdown-panel active">
            <div class="topic-control-box">
                <div class="input-group">
                    <select id="video-topic-select" onchange="changeVideoLesson()">
                        <option value="immigration">Video 1: Thủ tục Nhập cảnh & Hải quan Sân bay (Nam & Nữ)</option>
                        <option value="metro_conv">Video 2: Mua vé & Hỏi đường tại Ga tàu điện ngầm Metro (Nam & Nữ)</option>
                        <option value="biostat">Video 3: Thảo luận Thống kê Y sinh & Nghiên cứu Lâm sàng (Nam & Nữ)</option>
                        <option value="pharma">Video 4: Dược lâm sàng & Tư vấn Thuốc tại Bệnh viện (Nam & Nữ)</option>
                        <option value="conference">Video 5: Báo cáo & Phản biện tại Hội nghị Quốc tế (Nam & Nữ)</option>
                    </select>
                    <button class="btn-outline-blue" onclick="nextClipInTopic()">Đổi tình huống</button>
                </div>

                <div class="input-group">
                    <input type="text" id="custom-topic-input" placeholder="Tự nhập tình huống hội thoại (VD: tại ga metro, khai báo hải quan...)" onkeypress="if(event.key==='Enter') generateCustomDialogue()">
                    <button class="btn-blue" id="btn-gen-topic" onclick="generateCustomDialogue()">Tạo hội thoại Nam/Nữ</button>
                </div>
            </div>

            <div class="video-layout">
                <div class="video-main">
                    <div class="media-screen" id="media-player-box">
                        <div class="wave-header">
                            <span style="font-size: 11px; font-weight: bold; color: #9ec5fe;" id="clip-badge">TÌNH HUỐNG 01</span>
                            <div class="wave-bars" id="wave-indicator">
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
                            </div>
                            <span style="font-size: 11px; color: #e2e3e5;" id="player-status">Sẵn sàng</span>
                        </div>

                        <!-- KHUNG TRÌNH CHIẾU VIDEO BỐI CẢNH THỰC TẾ -->
                        <div class="video-frame-wrapper">
                            <video id="scene-video-player" muted loop playsinline controls>
                                <source id="scene-video-source" src="" type="video/mp4">
                            </video>
                            <div class="video-overlay-caption" id="live-video-caption">
                                <div style="font-size: 13px; font-weight: bold; color: #ffffff;" id="overlay-en">Bấm "Phát Video & Hội thoại" để xem và nghe đối đáp Nam - Nữ</div>
                                <div style="font-size: 12px; color: #9ec5fe; font-style: italic;" id="overlay-vi"></div>
                            </div>
                        </div>

                        <!-- KHUNG LỜI THOẠI PHÂN VAI NAM / NỮ -->
                        <div class="dialogue-container" id="subtitle-container"></div>

                        <div class="controls-row">
                            <button class="btn-blue" style="background-color: #198754;" onclick="playFullDialogue(1.0)">Phát Video & Hội thoại (1.0x)</button>
                            <button class="btn-dark-blue" onclick="playFullDialogue(0.65)">Nghe chậm (0.65x)</button>
                            <button class="btn-blue" style="background-color: #dc3545;" onclick="stopClip()">Dừng</button>
                            <button class="btn-outline-blue" onclick="swapGenders()">Đảo giọng Nam/Nữ</button>
                            <button class="btn-outline-blue" id="btn-toggle-sub" onclick="toggleSubtitle()">Ẩn phụ đề</button>
                        </div>
                    </div>
                </div>

                <div class="video-sidebar">
                    <div style="font-weight: bold; color: #0d6efd; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid #dee2e6; padding-bottom: 5px;">
                        Từ vựng trọng tâm
                    </div>
                    <div id="related-vocab-list"></div>

                    <div style="font-weight: bold; color: #084298; font-size: 14px; margin-top: 14px; margin-bottom: 6px; border-bottom: 1px solid #dee2e6; padding-bottom: 5px;">
                        Ngữ pháp & Mẫu câu
                    </div>
                    <div id="related-grammar-box"></div>
                </div>
            </div>
        </div>

        <!-- PANEL 2: BÀI VIẾT / KỊCH BẢN GIẢNG BÀI -->
        <div id="panel-lecture" class="dropdown-panel">
            <div class="topic-control-box">
                <div class="input-group">
                    <select id="preset-lecture-select" onchange="loadPresetLecture()">
                        <option value="ttest1">Mẫu 1 (Học thuật): Bài giảng Kiểm định t-test 1 mẫu (One-Sample t-Test)</option>
                        <option value="metro">Mẫu 2 (Đời sống): Giao tiếp & Hướng dẫn tại Ga tàu điện ngầm (Metro Station)</option>
                        <option value="logistic">Mẫu 3 (Học thuật): Bài giảng Hồi quy Logistic Đa biến</option>
                    </select>
                </div>
                <div class="input-group">
                    <input type="text" id="custom-lecture-topic" placeholder="Nhập chủ đề bất kỳ (VD: Tại ga metro, bài giảng t-test 1 mẫu, đặt phòng khách sạn...)" onkeypress="if(event.key==='Enter') generateLectureScript()">
                    <button class="btn-blue" id="btn-gen-lecture" onclick="generateLectureScript()">Soạn bài viết / Kịch bản</button>
                </div>
            </div>

            <div style="display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; align-items: center;">
                <button class="btn-word" onclick="downloadLectureWord()">Tải về file Word (.doc)</button>
                <button class="btn-blue" onclick="playFullLecture(1.0)">Nghe kịch bản (1.0x)</button>
                <button class="btn-dark-blue" onclick="playFullLecture(0.65)">Nghe chậm (0.65x)</button>
                <button class="btn-blue" style="background-color: #dc3545;" onclick="stopClip()">Dừng đọc</button>
                <button class="btn-outline-blue" id="btn-toggle-lec-vi" onclick="toggleLectureVi()">Ẩn tiếng Việt</button>
            </div>

            <div class="lecture-scroll-box" id="lecture-display-area"></div>
        </div>

        <!-- PANEL 3: TỪ ĐIỂN AI & PHÁT ÂM -->
        <div id="panel-dict" class="dropdown-panel">
            <div class="input-group">
                <input type="text" id="dict-input" placeholder="Nhập từ vựng tiếng Anh (VD: platform, transfer, hypothesis)..." onkeypress="if(event.key==='Enter') lookupWord()">
                <button class="btn-blue" onclick="lookupWord()">Tra cứu</button>
            </div>
            <div id="dict-result">
                <p style="color: #6c757d; font-style: italic; font-size: 13px;">Nhập một từ tiếng Anh để xem nghĩa tiếng Việt, phiên âm IPA, ví dụ và nghe giọng đọc chuẩn.</p>
            </div>
        </div>

        <!-- PANEL 4: LUYỆN NÓI & CHẤM ĐIỂM -->
        <div id="panel-speak" class="dropdown-panel">
            <div class="input-group">
                <select id="topic-select" onchange="loadNextSentence()">
                    <option value="metro">Chủ đề: Tại Ga Metro & Giao thông</option>
                    <option value="immigration">Chủ đề: Nhập cảnh & Hải quan</option>
                    <option value="medical">Chủ đề: Y khoa & Thống kê</option>
                </select>
                <button class="btn-outline-blue" onclick="loadNextSentence()">Đổi câu mẫu</button>
            </div>
            <div class="sample-sentence-box">
                <div style="font-size: 11px; color: #0d6efd; font-weight: bold; margin-bottom: 4px;">CÂU MẪU LUYỆN ĐỌC:</div>
                <span id="target-sentence">Excuse me, which metro line goes to the city center, and where can I buy a ticket?</span>
                <div style="margin-top: 8px; display: flex; gap: 6px; flex-wrap: wrap;">
                    <button class="btn-blue" onclick="speakText(document.getElementById('target-sentence').innerText, 0.95, 'female')">Nghe giọng Nữ</button>
                    <button class="btn-blue" style="background-color:#084298;" onclick="speakText(document.getElementById('target-sentence').innerText, 0.95, 'male')">Nghe giọng Nam</button>
                    <button class="btn-outline-blue" onclick="speakText(document.getElementById('target-sentence').innerText, 0.65, 'female')">Nghe chậm</button>
                </div>
                <div id="target-vi" style="font-size: 13px; color: #555; margin-top: 6px; font-style: italic;">
                    (Xin lỗi, tuyến metro nào đi đến trung tâm thành phố và tôi có thể mua vé ở đâu?)
                </div>
            </div>
            <button id="btn-record-eval" class="btn-blue" style="width: 100%; padding: 12px; font-size: 13px;" onclick="startPronunciationCheck()">
                BẤM ĐỂ ĐỌC CÂU TRÊN VÀ CHẤM ĐIỂM AI
            </button>
            <div id="speak-feedback" style="margin-top: 12px;"></div>
        </div>

        <!-- PANEL 5: GIA SƯ SONG NGỮ -->
        <div id="panel-chat" class="dropdown-panel">
            <div class="chat-window" id="chat-box">
                <div class="msg-ai">
                    <b>AI English Tutor:</b> Xin chào! Hãy nhập câu tiếng Việt bạn muốn nói hoặc câu tiếng Anh cần chỉnh sửa tự nhiên hơn.
                </div>
            </div>
            <div class="input-group">
                <input type="text" id="chat-input" placeholder="Nhập câu tiếng Việt hoặc tiếng Anh..." onkeypress="if(event.key==='Enter') sendTutorMessage()">
                <button class="btn-blue" onclick="sendTutorMessage()">Gửi AI</button>
            </div>
        </div>

        <script>
            const UPLOADED_DOC_DATA = __UPLOADED_DOC_JSON__;

            // =========================================================================
            // BỘ CHỌN GIỌNG NAM & GIỌNG NỮ TỰ ĐỘNG TRÊN TRÌNH DUYỆT
            // =========================================================================
            let maleVoice = null;
            let femaleVoice = null;

            function loadVoicesList() {
                if (!('speechSynthesis' in window)) return;
                let voices = window.speechSynthesis.getVoices();
                let enVoices = voices.filter(v => v.lang.startsWith('en'));
                if (enVoices.length === 0) enVoices = voices;

                // Nhận diện giọng Nam chuẩn
                maleVoice = enVoices.find(v => /david|mark|guy|daniel|james|george|alex|male|man|christopher|eric|ryan/i.test(v.name)) || enVoices[0] || null;
                // Nhận diện giọng Nữ chuẩn (khác với giọng Nam)
                femaleVoice = enVoices.find(v => /zira|jenny|aria|samantha|victoria|karen|hazel|susan|female|woman|emma|olivia/i.test(v.name) && v !== maleVoice) || enVoices[1] || enVoices[0] || null;
            }

            if ('speechSynthesis' in window) {
                loadVoicesList();
                window.speechSynthesis.onvoiceschanged = loadVoicesList;
            }

            function applyGenderVoice(utterance, gender) {
                loadVoicesList();
                if (gender === 'male') {
                    if (maleVoice) utterance.voice = maleVoice;
                    utterance.pitch = 0.88; // Trầm ấm giọng nam
                } else {
                    if (femaleVoice) utterance.voice = femaleVoice;
                    utterance.pitch = 1.15; // Thanh thoát giọng nữ
                }
            }

            function openPanel(panelId, btn) {
                document.querySelectorAll('.dropdown-panel').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));
                document.getElementById('panel-' + panelId).classList.add('active');
                btn.classList.add('active');
                stopClip();
            }

            // =========================================================================
            // PHẦN 1: VIDEO & HỘI THOẠI ĐỐI ĐÁP NAM / NỮ
            // =========================================================================
            const DIALOGUE_BANK = {
                immigration: [
                    {
                        title: "Tình huống 1: Kiểm tra Hộ chiếu & Mục đích nhập cảnh",
                        videoUrl: "https://assets.mixkit.co/videos/preview/mixkit-passengers-walking-through-an-airport-terminal-43525-large.mp4",
                        turns: [
                            { role: "Immigration Officer", gender: "male", en: "Good morning. May I see your passport and boarding pass, please? What is the purpose of your visit?", vi: "Chào buổi sáng. Vui lòng cho tôi xem hộ chiếu và thẻ lên máy bay. Mục đích chuyến đi của bà là gì?" },
                            { role: "Passenger", gender: "female", en: "Good morning. Here you are. I am attending an international medical conference at the university for five days.", vi: "Chào buổi sáng. Đây ạ. Tôi đến tham dự một hội nghị y khoa quốc tế tại trường đại học trong 5 ngày." },
                            { role: "Immigration Officer", gender: "male", en: "Where will you be staying, and do you have a return flight ticket?", vi: "Bà sẽ lưu trú ở đâu và đã có vé máy bay khứ hồi chưa?" },
                            { role: "Passenger", gender: "female", en: "I am staying at the Grand Hotel downtown. Here is my hotel reservation and return ticket.", vi: "Tôi ở tại khách sạn Grand ở trung tâm thành phố. Đây là xác nhận đặt phòng và vé khứ hồi của tôi." }
                        ],
                        vocab: [
                            { word: "immigration", ipa: "/ˌɪm.əˈɡreɪ.ʃən/", mean: "nhập cảnh, di trú" },
                            { word: "boarding pass", ipa: "/ˈbɔːr.dɪŋ pæs/", mean: "thẻ lên máy bay" },
                            { word: "reservation", ipa: "/ˌrez.ɚˈveɪ.ʃən/", mean: "sự đặt chỗ trước" }
                        ],
                        grammar: {
                            title: "Thì Hiện tại Tiếp diễn diễn tả kế hoạch đã định sẵn",
                            rule: "S + am/is/are + V-ing + (thời gian/địa điểm)",
                            example: "I am staying at a hotel near the airport and returning on Friday."
                        }
                    },
                    {
                        title: "Tình huống 2: Khai báo Hải quan & Hành lý",
                        videoUrl: "https://assets.mixkit.co/videos/preview/mixkit-man-walking-with-his-luggage-at-the-airport-43528-large.mp4",
                        turns: [
                            { role: "Customs Officer", gender: "female", en: "Do you have anything to declare, such as restricted medications, food, or more than ten thousand dollars in cash?", vi: "Ông có hàng hóa gì cần khai báo không, như thuốc hạn chế, thực phẩm, hoặc hơn 10.000 đô la tiền mặt?" },
                            { role: "Passenger", gender: "male", en: "No, I only have personal belongings and my prescribed medication with a doctor's note.", vi: "Không, tôi chỉ mang đồ dùng cá nhân và thuốc kê đơn có giấy xác nhận của bác sĩ." }
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
                metro_conv: [
                    {
                        title: "Tình huống: Mua vé & Hỏi tuyến tàu tại Ga Metro",
                        videoUrl: "https://assets.mixkit.co/videos/preview/mixkit-subway-train-arriving-at-the-station-4248-large.mp4",
                        turns: [
                            { role: "Passenger", gender: "female", en: "Excuse me, does this metro line go directly to Ben Thanh Central Station?", vi: "Xin lỗi, tuyến metro này có đi thẳng đến Ga Trung tâm Bến Thành không ạ?" },
                            { role: "Station Staff", gender: "male", en: "Yes, it does. You need to take Line 1 heading south. You can buy a single-journey ticket at the blue vending machine over there.", vi: "Có ạ. Chị cần đi Tuyến số 1 hướng về phía Nam. Chị có thể mua vé một lượt tại máy bán vé tự động màu xanh đằng kia." },
                            { role: "Passenger", gender: "female", en: "Thank you. Which platform should I go to after tapping my ticket?", vi: "Cảm ơn anh. Tôi nên đi đến sân ga nào sau khi quẹt vé ạ?" },
                            { role: "Station Staff", gender: "male", en: "Go down the escalator to Platform 2. The next train arrives in three minutes.", vi: "Chị đi thang cuốn xuống Sân ga số 2 nhé. Chuyến tàu tiếp theo sẽ đến trong 3 phút nữa." }
                        ],
                        vocab: [
                            { word: "vending machine", ipa: "/ˈven.dɪŋ məˌʃiːn/", mean: "máy bán vé tự động" },
                            { word: "platform", ipa: "/ˈplæt.fɔːrm/", mean: "sân ga / ke ga" },
                            { word: "escalator", ipa: "/ˈes.kə.leɪ.t̬ɚ/", mean: "thang cuốn" }
                        ],
                        grammar: {
                            title: "Câu hỏi xác nhận tuyến đường & Chỉ dẫn vị trí",
                            rule: "Does this line go directly to + Place? / Take Line X heading + Direction",
                            example: "Does this train stop at the university station? Take the escalator to Platform 1."
                        }
                    }
                ],
                biostat: [
                    {
                        title: "Thảo luận thiết kế nghiên cứu & Cỡ mẫu",
                        videoUrl: "https://assets.mixkit.co/videos/preview/mixkit-scientists-working-in-a-laboratory-4733-large.mp4",
                        turns: [
                            { role: "Principal Investigator", gender: "male", en: "How did we calculate the required sample size for this clinical trial?", vi: "Chúng ta đã tính toán cỡ mẫu cần thiết cho thử nghiệm lâm sàng này như thế nào?" },
                            { role: "Biostatistician", gender: "female", en: "We based it on an eighty percent statistical power and a five percent significance level, accounting for a ten percent dropout rate.", vi: "Chúng tôi dựa trên lực thống kê 80% và mức ý nghĩa 5%, có tính đến tỷ lệ bỏ cuộc 10%." }
                        ],
                        vocab: [
                            { word: "statistical power", ipa: "/stəˈtɪs.tɪ.kəl ˈpaʊ.ɚ/", mean: "lực thống kê" },
                            { word: "significance level", ipa: "/sɪɡˈnɪf.ə.kəns ˈlev.əl/", mean: "mức ý nghĩa thống kê" }
                        ],
                        grammar: {
                            title: "Cấu trúc bị động thì Quá khứ đơn",
                            rule: "S + was/were + V3/ed + based on...",
                            example: "The sample size was calculated based on previous pilot data."
                        }
                    }
                ],
                pharma: [
                    {
                        title: "Tư vấn sử dụng thuốc & Tác dụng phụ",
                        videoUrl: "https://assets.mixkit.co/videos/preview/mixkit-doctor-explaining-medicine-to-a-patient-42764-large.mp4",
                        turns: [
                            { role: "Pharmacist", gender: "female", en: "Take one tablet twice daily after meals. Avoid driving if you experience drowsiness.", vi: "Uống một viên hai lần mỗi ngày sau bữa ăn. Tránh lái xe nếu anh cảm thấy buồn ngủ." },
                            { role: "Patient", gender: "male", en: "Can I take this medication alongside my blood pressure pills?", vi: "Tôi có thể uống thuốc này cùng với thuốc huyết áp của tôi không?" }
                        ],
                        vocab: [
                            { word: "drowsiness", ipa: "/ˈdraʊ.zi.nəs/", mean: "cơn buồn ngủ" }
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
                        title: "Trình bày kết quả tại Hội nghị Quốc tế",
                        videoUrl: "https://assets.mixkit.co/videos/preview/mixkit-business-people-attending-a-conference-42833-large.mp4",
                        turns: [
                            { role: "Speaker", gender: "male", en: "As illustrated in the figure, overall survival was significantly higher in the treatment group.", vi: "Như minh họa trong biểu đồ, tỷ lệ sống còn toàn bộ cao hơn đáng kể ở nhóm điều trị." },
                            { role: "Moderator", gender: "female", en: "Thank you for a clear presentation. Could you elaborate on the limitations of your study?", vi: "Cảm ơn bài trình bày rõ ràng. Ông có thể nói rõ hơn về những hạn chế của nghiên cứu không?" }
                        ],
                        vocab: [
                            { word: "elaborate on", ipa: "/iˈlæb.ə.reɪt ɑːn/", mean: "trình bày chi tiết thêm" }
                        ],
                        grammar: {
                            title: "Cấu trúc bị động so sánh trong báo cáo kết quả",
                            rule: "S + was/were + Adv + Comparative Adj",
                            example: "The incidence rate was markedly lower in the vaccinated cohort."
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
                
                // Cập nhật nguồn Video bối cảnh thực tế
                let videoEl = document.getElementById('scene-video-player');
                let sourceEl = document.getElementById('scene-video-source');
                let newVideoUrl = sceneObj.videoUrl || "https://assets.mixkit.co/videos/preview/mixkit-passengers-walking-through-an-airport-terminal-43525-large.mp4";
                if (sourceEl.src !== newVideoUrl) {
                    sourceEl.src = newVideoUrl;
                    videoEl.load();
                }

                document.getElementById('overlay-en').innerText = sceneObj.turns[0].en;
                document.getElementById('overlay-vi').innerText = sceneObj.turns[0].vi;

                let container = document.getElementById('subtitle-container');
                let html = "";

                sceneObj.turns.forEach((turn, idx) => {
                    let isFemale = turn.gender === "female";
                    let roleClass = isFemale ? "turn-box role-female" : "turn-box";
                    let genderTag = isFemale ? "Giọng Nữ" : "Giọng Nam";
                    let blurClass = isSubVisible ? "" : "sub-hidden";
                    html += `
                        <div class="${roleClass}" id="turn-card-${idx}">
                            <div class="role-label">
                                <span>${turn.role} (${genderTag})</span>
                                <button class="btn-outline-blue" style="padding:2px 8px; font-size:11px; background:rgba(255,255,255,0.9);" onclick="speakText('${turn.en.replace(/'/g, "\\'")}', 0.95, '${turn.gender}')">Nghe vai này</button>
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
                                <span style="font-weight:bold; color:#0d6efd; font-size:14px;">${v.word}</span>
                                <button class="btn-outline-blue" style="padding:2px 8px; font-size:11px;" onclick="speakText('${v.word.replace(/'/g, "\\'")}', 0.9, 'female')">Nghe</button>
                            </div>
                            ${v.ipa ? `<div style="font-family:monospace; color:#6c757d; font-size:12px;">${v.ipa}</div>` : ''}
                            <div style="color:#212529; font-size:13px; margin-top:2px;">Nghĩa: <b>${v.mean}</b></div>
                        </div>
                    `;
                });
                document.getElementById('related-vocab-list').innerHTML = vocabHtml;

                document.getElementById('related-grammar-box').innerHTML = `
                    <div class="grammar-card">
                        <div style="font-weight:bold; color:#084298; font-size:13.5px; margin-bottom:4px;">${sceneObj.grammar.title}</div>
                        <div style="background:#ffffff; padding:5px 7px; border-radius:4px; font-family:monospace; font-size:11.5px; color:#d63384; margin-bottom:5px;">
                            ${sceneObj.grammar.rule}
                        </div>
                        <div style="font-size:13px; color:#333;">
                            <b>Ví dụ:</b> <i>"${sceneObj.grammar.example}"</i>
                            <button class="btn-outline-blue" style="padding:2px 6px; font-size:11px; margin-left:4px;" onclick="speakText('${sceneObj.grammar.example.replace(/'/g, "\\'")}', 0.95, 'male')">Nghe</button>
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

            // Hoán đổi giới tính Nam <-> Nữ cho toàn bộ các vai trong cuộc hội thoại
            function swapGenders() {
                stopClip();
                let scene = customDialogueObj ? customDialogueObj : DIALOGUE_BANK[currentTopicKey][currentClipIndex];
                scene.turns.forEach(t => {
                    t.gender = (t.gender === "male") ? "female" : "male";
                });
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
                    if (lower.includes("metro") || lower.includes("tàu điện") || lower.includes("nhà ga")) {
                        customDialogueObj = JSON.parse(JSON.stringify(DIALOGUE_BANK["metro_conv"][0]));
                        renderDialogueScene(customDialogueObj, `TÌNH HUỐNG: ${rawTopic.toUpperCase()}`);
                        return;
                    }
                    if (lower.includes("nhập cảnh") || lower.includes("hải quan") || lower.includes("sân bay")) {
                        customDialogueObj = JSON.parse(JSON.stringify(DIALOGUE_BANK["immigration"][0]));
                        renderDialogueScene(customDialogueObj, `TÌNH HUỐNG: ${rawTopic.toUpperCase()}`);
                        return;
                    }
                    let enTopic = rawTopic;
                    if (/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(rawTopic)) {
                        enTopic = await translateText(rawTopic, 'vi', 'en');
                    }
                    let turnsEn = [
                        { role: "Staff / Officer (Nhân viên)", gender: "male", en: `Good morning! How can I assist you today regarding ${enTopic}?` },
                        { role: "Visitor / Guest (Khách)", gender: "female", en: `Hello! I need some guidance about ${enTopic}. Could you explain the procedure to me?` },
                        { role: "Staff / Officer (Nhân viên)", gender: "male", en: `Certainly. Please follow the signs to the main counter and present your ID card.` },
                        { role: "Visitor / Guest (Khách)", gender: "female", en: `Thank you very much for your clear explanation and help!` }
                    ];
                    let turnsFull = [];
                    for (let t of turnsEn) {
                        let viText = await translateText(t.en, 'en', 'vi');
                        turnsFull.push({ role: t.role, gender: t.gender, en: t.en, vi: viText });
                    }
                    customDialogueObj = {
                        title: `HỘI THOẠI: ${rawTopic.toUpperCase()}`,
                        videoUrl: "https://assets.mixkit.co/videos/preview/mixkit-business-people-attending-a-conference-42833-large.mp4",
                        turns: turnsFull,
                        vocab: [{ word: "procedure", ipa: "/prəˈsiː.dʒɚ/", mean: "thủ tục, quy trình" }],
                        grammar: {
                            title: "Mẫu câu Đề nghị Hướng dẫn Lịch sự",
                            rule: "Could you explain + Noun + to me?",
                            example: `Could you explain the steps for ${enTopic} to me?`
                        }
                    };
                    renderVideoLesson();
                } finally {
                    btn.innerText = "Tạo hội thoại Nam/Nữ";
                    btn.disabled = false;
                }
            }

            // Phát Video đồng thời đọc luân phiên đúng giọng Nam & Nữ theo từng vai
            function playFullDialogue(rate) {
                if (!('speechSynthesis' in window)) return;
                stopClip();
                let scene = customDialogueObj ? customDialogueObj : DIALOGUE_BANK[currentTopicKey][currentClipIndex];
                let turns = scene.turns;
                let wave = document.getElementById('wave-indicator');
                let status = document.getElementById('player-status');
                let videoEl = document.getElementById('scene-video-player');

                isPlayingSequence = true;
                wave.classList.add('playing');
                if (videoEl) {
                    videoEl.play().catch(() => {});
                }

                let index = 0;

                function speakNextTurn() {
                    document.querySelectorAll('.turn-box').forEach(el => el.classList.remove('speaking-active'));

                    if (!isPlayingSequence || index >= turns.length) {
                        wave.classList.remove('playing');
                        status.innerText = "Đã phát xong video hội thoại.";
                        if (videoEl) videoEl.pause();
                        isPlayingSequence = false;
                        return;
                    }

                    let currentTurn = turns[index];
                    let genderLabel = currentTurn.gender === "male" ? "Giọng Nam" : "Giọng Nữ";
                    status.innerText = `Lượt ${index + 1}/${turns.length}: ${currentTurn.role} (${genderLabel})`;

                    // Làm nổi bật câu đang đọc và cập nhật phụ đề trên màn hình video
                    let activeCard = document.getElementById(`turn-card-${index}`);
                    if (activeCard) activeCard.classList.add('speaking-active');
                    
                    document.getElementById('overlay-en').innerText = isSubVisible ? `${currentTurn.role}: "${currentTurn.en}"` : "[Đang ẩn phụ đề]";
                    document.getElementById('overlay-vi').innerText = isSubVisible ? currentTurn.vi : "";

                    let utterance = new SpeechSynthesisUtterance(currentTurn.en);
                    utterance.lang = 'en-US';
                    utterance.rate = rate;
                    applyGenderVoice(utterance, currentTurn.gender);

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
                let videoEl = document.getElementById('scene-video-player');
                document.querySelectorAll('.turn-box').forEach(el => el.classList.remove('speaking-active'));
                if (videoEl) videoEl.pause();
                if (wave) wave.classList.remove('playing');
                if (status) status.innerText = "Đã dừng.";
            }

            function toggleSubtitle() {
                isSubVisible = !isSubVisible;
                let btn = document.getElementById('btn-toggle-sub');
                document.querySelectorAll('.sub-en, .sub-vi').forEach(el => {
                    if (isSubVisible) el.classList.remove('sub-hidden');
                    else el.classList.add('sub-hidden');
                });
                let overlayEn = document.getElementById('overlay-en');
                let overlayVi = document.getElementById('overlay-vi');
                if (!isSubVisible) {
                    overlayEn.classList.add('sub-hidden');
                    overlayVi.classList.add('sub-hidden');
                } else {
                    overlayEn.classList.remove('sub-hidden');
                    overlayVi.classList.remove('sub-hidden');
                }
                btn.innerText = isSubVisible ? "Ẩn phụ đề" : "Hiện phụ đề";
            }

            renderVideoLesson();

            // =========================================================================
            // PHẦN 2: BÀI VIẾT & KỊCH BẢN GIẢNG BÀI + XUẤT WORD
            // =========================================================================
            const LECTURE_BANK = {
                ttest1: {
                    title: "LECTURE SCRIPT: ONE-SAMPLE T-TEST IN BIOSTATISTICS (BÀI GIẢNG KIỂM ĐỊNH T 1 MẪU)",
                    sections: [
                        {
                            heading: "1. Opening & Purpose (Mở đầu & Mục đích kiểm định)",
                            en: "Good morning everyone. Today, we will explore the One-Sample t-Test, one of the most fundamental parametric hypothesis tests in biostatistics. We use a one-sample t-test when we want to determine whether the mean of a single sample differs significantly from a known or hypothesized population mean (mu-zero).",
                            vi: "Chào buổi sáng tất cả các bạn. Hôm nay, chúng ta sẽ tìm hiểu về Kiểm định t một mẫu (One-Sample t-Test), một trong những kiểm định giả thuyết tham số cơ bản nhất trong thống kê y sinh. Chúng ta sử dụng kiểm định này khi muốn xác định liệu trung bình của một mẫu đơn lẻ có khác biệt có ý nghĩa thống kê so với trung bình quần thể giả định (mu-0) hay không."
                        },
                        {
                            heading: "2. Key Assumptions (Các giả định cốt lõi)",
                            en: "Before running this test, we must verify three critical assumptions: First, the dependent variable must be continuous. Second, the observations must be independent. Third, the data should follow an approximately normal distribution, especially when the sample size is small (n < 30).",
                            vi: "Trước khi chạy kiểm định này, chúng ta phải kiểm tra ba giả định quan trọng: Thứ nhất, biến phụ thuộc phải là biến liên tục. Thứ hai, các quan sát phải độc lập. Thứ ba, dữ liệu cần tuân theo phân phối xấp xỉ chuẩn, đặc biệt khi cỡ mẫu nhỏ (n < 30)."
                        },
                        {
                            heading: "3. Hypotheses & Interpretation (Giả thuyết & Diễn giải kết quả)",
                            en: "The null hypothesis (H0) states that the sample mean equals the population mean, while the alternative hypothesis (H1) states that there is a significant difference. If our calculated p-value is less than 0.05, we reject H0 and conclude a statistically significant difference.",
                            vi: "Giả thuyết không (H0) phát biểu rằng trung bình mẫu bằng trung bình quần thể, trong khi giả thuyết đối (H1) cho rằng có sự khác biệt có ý nghĩa. Nếu trị số p tính được nhỏ hơn 0.05, chúng ta bác bỏ H0 và kết luận có sự khác biệt có ý nghĩa thống kê."
                        }
                    ],
                    vocab: [
                        { word: "One-Sample t-Test", mean: "Kiểm định t một mẫu" },
                        { word: "Hypothesized population mean", mean: "Giá trị trung bình quần thể giả định" },
                        { word: "Null hypothesis (H0)", mean: "Giả thuyết không" },
                        { word: "Degrees of freedom (df)", mean: "Bậc tự do" }
                    ]
                },
                metro: {
                    title: "PRACTICAL GUIDE: AT THE METRO STATION (GIAO TIẾP TẠI GA TÀU ĐIỆN NGẦM)",
                    sections: [
                        {
                            heading: "1. Buying Tickets & Checking the Route Map (Mua vé & Xem bản đồ tuyến)",
                            en: "When arriving at a metro station, passengers first check the transit map to identify the correct line and final destination. You can purchase a single-journey ticket or a rechargeable smart card at the automatic ticket vending machines or the customer service counter.",
                            vi: "Khi đến ga tàu điện ngầm, hành khách trước tiên cần xem bản đồ tuyến để xác định đúng tuyến tàu và ga đích cuối cùng. Bạn có thể mua vé lượt hoặc thẻ thông minh nạp tiền tại các máy bán vé tự động hoặc quầy dịch vụ khách hàng."
                        },
                        {
                            heading: "2. Passing Ticket Gates & Finding the Platform (Qua cổng soát vé & Tìm sân ga)",
                            en: "After getting your ticket, tap your card on the sensor at the automatic fare gate to enter the paid area. Follow the overhead directional signs indicating the platform number and the direction of travel, then stand behind the yellow safety line while waiting for the train.",
                            vi: "Sau khi có vé, hãy chạm thẻ vào đầu đọc cảm biến tại cổng soát vé tự động để vào khu vực sân ga. Đi theo các biển chỉ dẫn treo phía trên ghi số sân ga và hướng di chuyển của tàu, sau đó đứng sau vạch an toàn màu vàng trong khi chờ tàu đến."
                        }
                    ],
                    vocab: [
                        { word: "Ticket vending machine", mean: "Máy bán vé tự động" },
                        { word: "Automatic fare gate", mean: "Cổng soát vé tự động" },
                        { word: "Platform", mean: "Sân ga / Ke ga" }
                    ]
                },
                logistic: {
                    title: "LECTURE SCRIPT: MULTIVARIATE LOGISTIC REGRESSION (BÀI GIẢNG HỒI QUY LOGISTIC ĐA BIẾN)",
                    sections: [
                        {
                            heading: "1. Introduction & When to Use (Mở đầu & Khi nào sử dụng)",
                            en: "Binary logistic regression is used when our dependent variable is dichotomous—meaning it has only two possible outcomes, such as cured versus not cured, or disease present versus absent.",
                            vi: "Hồi quy logistic nhị phân được sử dụng khi biến phụ thuộc của chúng ta là biến nhị giá—nghĩa là chỉ có hai kết cục có thể xảy ra, chẳng hạn như khỏi bệnh so với không khỏi bệnh, hoặc có bệnh so với không bệnh."
                        },
                        {
                            heading: "2. Adjusted Odds Ratio (Tỷ số chênh hiệu chỉnh aOR)",
                            en: "The primary advantage of a multivariate model is its ability to adjust for multiple confounding variables simultaneously. We interpret the Adjusted Odds Ratio (aOR) along with its 95% confidence interval.",
                            vi: "Ưu điểm chính của mô hình đa biến là khả năng hiệu chỉnh đồng thời cho nhiều biến gây nhiễu. Chúng ta diễn giải Tỷ số chênh hiệu chỉnh (aOR) cùng với khoảng tin cậy 95% của nó."
                        }
                    ],
                    vocab: [
                        { word: "Dichotomous outcome", mean: "Kết cục nhị giá (2 giá trị)" },
                        { word: "Adjusted Odds Ratio (aOR)", mean: "Tỷ số chênh đã hiệu chỉnh" }
                    ]
                }
            };

            let currentLectureObj = UPLOADED_DOC_DATA ? UPLOADED_DOC_DATA : LECTURE_BANK["ttest1"];
            let isLectureViVisible = true;

            function renderLecture(lecObj) {
                currentLectureObj = lecObj;
                let area = document.getElementById('lecture-display-area');
                let viStyle = isLectureViVisible ? "" : "display: none;";

                let html = `<div class="lecture-inner-content">
                    <div class="lecture-title">${lecObj.title}</div>`;

                lecObj.sections.forEach((sec) => {
                    html += `
                        <div class="lecture-section">
                            <div class="sec-heading">
                                <span>${sec.heading}</span>
                                <button class="btn-outline-blue" style="padding:2px 8px; font-size:11px;" onclick="speakText('${sec.en.replace(/'/g, "\\'")}', 0.95, 'male')">Nghe phần này</button>
                            </div>
                            <div class="sec-en">${sec.en}</div>
                            <div class="sec-vi lec-vi-text" style="${viStyle}">${sec.vi}</div>
                        </div>
                    `;
                });

                if (lecObj.vocab && lecObj.vocab.length > 0) {
                    html += `<div style="margin-top:12px; padding:10px; background:#e7f1ff; border-radius:6px;">
                        <b style="color:#084298; font-size:14px;">Từ vựng & Thuật ngữ trọng tâm:</b>
                        <ul style="margin:6px 0 0 18px; padding:0; font-size:13.5px;">`;
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
                if (!rawTopic) { alert("Vui lòng nhập chủ đề bài viết hoặc bài giảng!"); return; }
                stopClip();
                let btn = document.getElementById('btn-gen-lecture');
                btn.innerText = "Đang soạn...";
                btn.disabled = true;

                try {
                    let lower = rawTopic.toLowerCase();
                    if (lower.includes("metro") || lower.includes("tàu điện") || lower.includes("nhà ga")) {
                        renderLecture(LECTURE_BANK["metro"]);
                        return;
                    }
                    if ((lower.includes("t test") || lower.includes("t-test")) && (lower.includes("1") || lower.includes("một") || lower.includes("one"))) {
                        renderLecture(LECTURE_BANK["ttest1"]);
                        return;
                    }
                    if (lower.includes("logistic")) {
                        renderLecture(LECTURE_BANK["logistic"]);
                        return;
                    }

                    let enTopic = rawTopic;
                    if (/[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(rawTopic)) {
                        enTopic = await translateText(rawTopic, 'vi', 'en');
                    }

                    const academicKeywords = ["nghiên cứu", "thống kê", "kiểm định", "hồi quy", "lâm sàng", "y học", "dược", "luận án", "luận văn", "khoa học", "phân tích", "bài giảng", "test", "regression", "clinical", "study", "analysis", "lecture", "research", "method"];
                    let isAcademic = academicKeywords.some(kw => lower.includes(kw));

                    let rawSections = [];
                    if (isAcademic) {
                        rawSections = [
                            {
                                heading: "1. Introduction & Lecture Objectives (Mở đầu & Mục tiêu bài giảng)",
                                en: `Good morning colleagues and students. In today's lecture, we will examine ${enTopic}. Understanding the theoretical principles and practical applications of ${enTopic} is essential for rigorous research and evidence-based decision-making.`
                            },
                            {
                                heading: "2. Core Methodology & Assumptions (Phương pháp luận & Giả định cốt lõi)",
                                en: `When applying ${enTopic}, researchers must carefully define study variables, verify underlying statistical assumptions, and ensure data accuracy so that the analytical findings are valid and reproducible.`
                            },
                            {
                                heading: "3. Practical Interpretation & Conclusion (Diễn giải kết quả & Kết luận)",
                                en: `In summary, ${enTopic} provides a systematic framework for analyzing data. Remember to evaluate both statistical significance and practical relevance when reporting your results.`
                            }
                        ];
                    } else {
                        rawSections = [
                            {
                                heading: "1. Common Situation & Useful Expressions (Tình huống thực tế & Mẫu câu thông dụng)",
                                en: `When you are ${enTopic}, knowing clear and polite English expressions makes communication smooth and stress-free. Start by greeting the staff politely and stating what you need clearly, such as: "Excuse me, could you help me with..." or "Where can I find..."`
                            },
                            {
                                heading: "2. Key Steps & Practical Interaction (Các bước giao tiếp & Xử lý tình huống)",
                                en: `While ${enTopic}, pay close attention to signs, announcements, and instructions from the staff. If someone speaks too quickly, say: "Could you please speak a little slower?" to make sure you understand every detail accurately.`
                            },
                            {
                                heading: "3. Polite Closing & Cultural Tips (Kết thúc lịch sự & Lưu ý giao tiếp)",
                                en: `Once your request is completed ${enTopic}, always thank the person who assisted you with a warm "Thank you very much for your help." Practicing these everyday phrases will help you feel confident anywhere.`
                            }
                        ];
                    }

                    let fullSections = [];
                    for (let s of rawSections) {
                        let viText = await translateText(s.en, 'en', 'vi');
                        fullSections.push({ heading: s.heading, en: s.en, vi: viText });
                    }

                    renderLecture({
                        title: `${isAcademic ? 'LECTURE SCRIPT' : 'PRACTICAL ENGLISH GUIDE'}: ${enTopic.toUpperCase()} (${rawTopic.toUpperCase()})`,
                        sections: fullSections,
                        vocab: []
                    });
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
                btn.innerText = isLectureViVisible ? "Ẩn tiếng Việt" : "Hiện tiếng Việt";
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
                    applyGenderVoice(u, 'male');
                    u.onend = function() {
                        idx++;
                        setTimeout(speakNextSec, 400);
                    };
                    window.speechSynthesis.speak(u);
                }
                speakNextSec();
            }

            function downloadLectureWord() {
                if (!currentLectureObj) return;
                let lec = currentLectureObj;
                let bodyHtml = `<h2 style="text-align:center; color:#084298; font-family:'Times New Roman', serif;">${lec.title}</h2><hr/>`;
                lec.sections.forEach(sec => {
                    bodyHtml += `
                        <p style="font-weight:bold; color:#0d6efd; font-size:13pt; margin-top:12pt; margin-bottom:4pt;">${sec.heading}</p>
                        <p style="font-size:12pt; line-height:1.5; text-align:justify; margin-bottom:4pt;">${sec.en}</p>
                        <p style="font-size:11.5pt; font-style:italic; color:#333333; line-height:1.4; text-align:justify; margin-bottom:10pt;"><i>(Dịch nghĩa: ${sec.vi})</i></p>
                    `;
                });
                if (lec.vocab && lec.vocab.length > 0) {
                    bodyHtml += `<p style="font-weight:bold; color:#084298; font-size:13pt; margin-top:14pt;">KEY VOCABULARY & TERMINOLOGY:</p><ul>`;
                    lec.vocab.forEach(v => {
                        bodyHtml += `<li style="font-size:12pt; margin-bottom:4pt;"><b>${v.word}:</b> ${v.mean}</li>`;
                    });
                    bodyHtml += `</ul>`;
                }
                let wordDocument = `<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><title>${lec.title}</title><style>body { font-family: 'Times New Roman', Times, serif; }</style></head><body>${bodyHtml}</body></html>`;
                let blob = new Blob(['\ufeff', wordDocument], { type: 'application/msword' });
                let url = URL.createObjectURL(blob);
                let link = document.createElement('a');
                link.href = url;
                link.download = 'Tai_Lieu_Hoc_Tieng_Anh_AI.doc';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }

            renderLecture(currentLectureObj);

            // =========================================================================
            // PHẦN 3: HÀM ĐỌC & TỪ ĐIỂN & LUYỆN NÓI & GIA SƯ
            // =========================================================================
            function speakText(text, rate = 1.0, gender = 'female') {
                stopClip();
                if ('speechSynthesis' in window) {
                    let utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = 'en-US';
                    utterance.rate = rate;
                    applyGenderVoice(utterance, gender);
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
                resDiv.innerHTML = "<p>Đang tra cứu...</p>";
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
                            defHtml += `<div style="margin-bottom: 8px;"><span style="background:#e7f1ff; color:#0d6efd; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold;">${m.partOfSpeech}</span><span> ${def.definition}</span>${def.example ? `<div style="color:#084298; font-style:italic; margin-top:3px;">Ví dụ: "${def.example}"</div>` : ''}</div>`;
                        });
                    }
                } catch(e) {}
                resDiv.innerHTML = `<div class="word-header">${word} <button class="btn-blue" style="padding:4px 10px; font-size:11px;" onclick="speakText('${word.replace(/'/g, "\\'")}', 0.95, 'female')">Giọng Nữ</button> <button class="btn-dark-blue" style="padding:4px 10px; font-size:11px;" onclick="speakText('${word.replace(/'/g, "\\'")}', 0.95, 'male')">Giọng Nam</button></div>${phonetic ? `<div class="phonetic">${phonetic}</div>` : ''}<div class="meaning-box"><b>Nghĩa tiếng Việt:</b> <span style="font-size:15px; color:#0d6efd; font-weight:bold;">${viMeaning}</span></div>${defHtml ? `<div><b>Giải nghĩa Anh - Anh:</b><div style="margin-top:6px;">${defHtml}</div></div>` : ''}`;
                speakText(word, 0.95, 'female');
            }

            const SENTENCE_BANK = {
                metro: [
                    { en: "Excuse me, which metro line goes to the city center, and where can I buy a ticket?", vi: "Xin lỗi, tuyến metro nào đi đến trung tâm thành phố và tôi có thể mua vé ở đâu?" },
                    { en: "Please tap your smart card at the fare gate and follow the signs to Platform 2.", vi: "Vui lòng chạm thẻ thông minh tại cổng soát vé và đi theo biển báo đến Sân ga số 2." }
                ],
                immigration: [
                    { en: "Here is my passport and return ticket. I am here for an international medical conference.", vi: "Đây là hộ chiếu và vé khứ hồi của tôi. Tôi đến đây để tham dự một hội nghị y khoa quốc tế." }
                ],
                medical: [
                    { en: "The one-sample t-test compares the mean of a single sample to a known population mean.", vi: "Kiểm định t một mẫu so sánh giá trị trung bình của một mẫu đơn lẻ với giá trị trung bình quần thể đã biết." }
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
                document.getElementById('speak-feedback').innerHTML = `<div style="background:#f8f9fa; border:1px solid #dee2e6; border-radius:8px; padding:12px;"><div><b>AI nghe được:</b> <i>"${spoken}"</i></div><div style="margin-top:6px;"><b>Đối chiếu:</b> ${highlightedHtml}</div><div class="score-circle" style="background:${badgeColor};">Điểm: ${score}/100</div><div style="margin-top:6px; font-size:13px;"><b>Nhận xét:</b> ${comment}</div></div>`;
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
                    chatBox.innerHTML += `<div class="msg-ai"><b>Diễn đạt Tiếng Anh tự nhiên:</b><br><span style="color:#0d6efd; font-weight:bold; font-size:14px;">"${enTrans}"</span> <button class="btn-outline-blue" style="padding:2px 8px; font-size:11px;" onclick="speakText('${enTrans.replace(/'/g, "\\'")}', 0.95, 'female')">Nghe</button></div>`;
                    speakText(enTrans, 0.95, 'female');
                } else {
                    let viMeaning = await translateText(text, 'en', 'vi');
                    let polishedEn = await translateText(viMeaning, 'vi', 'en');
                    chatBox.innerHTML += `<div class="msg-ai"><b>Phân tích câu của bạn:</b><br>• <b>Nghĩa tiếng Việt:</b> ${viMeaning}<br>• <b>Gợi ý mượt hơn:</b> <span style="color:#084298; font-weight:bold;">"${polishedEn}"</span> <button class="btn-outline-blue" style="padding:2px 8px; font-size:11px;" onclick="speakText('${polishedEn.replace(/'/g, "\\'")}', 0.95, 'male')">Nghe mẫu</button></div>`;
                    speakText(polishedEn, 0.95, 'male');
                }
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    english_tutor_html = english_tutor_template.replace("__UPLOADED_DOC_JSON__", uploaded_json_str)
    components.html(english_tutor_html, height=850, scrolling=True)
