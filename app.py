import io
import os
import re
import time
import json
import base64
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
    html, body, [data-testid="stAppViewContainer"] {
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    h1, h2, h3, h4, h5, h6, 
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
    }
    
    .stSelectbox label p, .stTextArea label p, .stSlider label p, .stFileUploader label p, .stTextInput label p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
        font-weight: bold !important;
    }
    
    .stButton button p {
        font-family: 'Times New Roman', Times, serif !important;
        font-size: 13px !important;
    }

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

    .dialogue-turn-male {
        background-color: #f0f7ff;
        border-left: 4px solid #0d6efd;
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 8px;
    }

    .dialogue-turn-female {
        background-color: #fff0f6;
        border-left: 4px solid #d63384;
        padding: 10px 14px;
        border-radius: 6px;
        margin-bottom: 8px;
    }

    .lecture-container {
        max-height: 450px;
        overflow-y: auto;
        border: 1px solid #b6d4fe;
        border-radius: 8px;
        padding: 16px;
        background-color: #ffffff;
        font-family: 'Times New Roman', Times, serif;
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

# Video công khai ổn định hỗ trợ CORS/HTML5 trực tiếp (Google Cloud Storage)
SAMPLE_VIDEOS = {
    "Hội nghị & Thảo luận học thuật": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "Du lịch, Sân bay & Giao thông": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    "Công việc & Đời sống hàng ngày": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"
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

# --- HÀM TẠO AUDIO ĐA GIỌNG NAM/NỮ THẬT BẰNG EDGE-TTS CHO ĐIỆN THOẠI & PC ---
async def build_dialogue_audio_async(turns, speed_rate=1.0, swap_gender=False):
    percent = int((speed_rate - 1.0) * 100)
    rate_str = f"+{percent}%" if percent >= 0 else f"{percent}%"
    combined_bytes = bytearray()

    for idx, turn in enumerate(turns):
        gender = turn.get("gender", "male" if idx % 2 == 0 else "female").lower()
        if swap_gender:
            gender = "female" if gender == "male" else "male"
        voice_id = "en-US-GuyNeural" if gender == "male" else "en-US-JennyNeural"
        
        communicate = edge_tts.Communicate(turn["en"], voice_id, rate=rate_str)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                combined_bytes.extend(chunk["data"])
    return bytes(combined_bytes)

def generate_dialogue_mp3_bytes(turns, speed_rate=1.0, swap_gender=False):
    try:
        return asyncio.run(build_dialogue_audio_async(turns, speed_rate, swap_gender))
    except Exception:
        return None

def extract_text_from_doc_or_pdf(uploaded_file):
    file_name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()
    text_content = ""
    if file_name.endswith(".docx"):
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
        except Exception:
            text_content = ""
    return text_content.strip()

# --- HÀM GỌI GEMINI AI TẠO SINH THỰC THỤ (TEXT + VISION PNG) ---
def get_gemini_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return os.environ.get("GEMINI_API_KEY", st.session_state.get("user_gemini_key", ""))

def generate_ai_learning_content(topic_prompt="", uploaded_file=None, mode="dialogue"):
    api_key = get_gemini_api_key()
    if not api_key:
        return None, "Chưa cấu hình GEMINI_API_KEY. Vui lòng nhập API Key ở mục cấu hình bên trên để AI tạo sinh nội dung thực tế."

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        contents = []

        if uploaded_file is not None:
            fname = uploaded_file.name.lower()
            raw_bytes = uploaded_file.getvalue()
            if fname.endswith(".png"):
                contents.append(types.Part.from_bytes(data=raw_bytes, mime_type="image/png"))
                contents.append("Hãy quan sát kỹ hình ảnh đính kèm, nhận diện bối cảnh, nhân vật, văn bản hoặc tình huống trong ảnh.")
            else:
                extracted = extract_text_from_doc_or_pdf(uploaded_file)
                if not extracted:
                    return None, "Không trích xuất được nội dung văn bản từ file đã tải lên."
                contents.append(f"Dựa trên nội dung tài liệu sau đây:\n{extracted[:4000]}")

        if topic_prompt.strip():
            contents.append(f"Chủ đề yêu cầu: {topic_prompt}")

        if mode == "dialogue":
            prompt_instruction = """
            Hãy đóng vai chuyên gia ngôn ngữ Anh - Việt, tạo sinh một kịch bản HỘI THOẠI THỰC TẾ, TỰ NHIÊN, DÀI VÀ CHUYÊN SÂU (từ 8 đến 10 lượt đối đáp qua lại) giữa ít nhất 2 nhân vật (1 Nam - gender: "male", 1 Nữ - gender: "female").
            Nếu có hình ảnh hoặc tài liệu đính kèm, kịch bản phải bám sát 100% bối cảnh trong hình ảnh/tài liệu đó.
            Trả về kết quả STRICT JSON (không bọc markdown ```json) theo đúng cấu trúc:
            {
              "title": "Tiêu đề tình huống bằng tiếng Việt & tiếng Anh",
              "video_category": "Chọn 1 trong 3 giá trị chính xác: 'Hội nghị & Thảo luận học thuật' hoặc 'Du lịch, Sân bay & Giao thông' hoặc 'Công việc & Đời sống hàng ngày'",
              "turns": [
                {"role": "Tên vai nhân vật (VD: Nhân viên Hải quan)", "gender": "male", "en": "Câu thoại tiếng Anh tự nhiên", "vi": "Bản dịch tiếng Việt sát nghĩa"}
              ],
              "vocab": [
                {"word": "từ/cụm từ đắt giá trong bài", "ipa": "/phiên âm IPA/", "mean": "nghĩa tiếng Việt"}
              ],
              "grammar": {
                "title": "Tên cấu trúc ngữ pháp nổi bật trong bài",
                "rule": "Công thức cấu trúc",
                "example": "Câu ví dụ minh họa tiếng Anh"
              }
            }
            """
        else:
            prompt_instruction = """
            Hãy biên soạn một BÀI VIẾT / KỊCH BẢN GIẢNG BÀI TIẾNG ANH HỌC THUẬT HOẶC THỰC TẾ HOÀN CHỈNH, CHI TIẾT (4 phần rõ ràng: Mở đầu, Nội dung cốt lõi, Ví dụ phân tích, Tổng kết) kèm bản dịch tiếng Việt chuẩn xác.
            Nếu có hình ảnh hoặc tài liệu đính kèm, hãy phân tích và xây dựng bài giảng dựa trên chính nội dung đó.
            Trả về kết quả STRICT JSON (không bọc markdown ```json) theo đúng cấu trúc:
            {
              "title": "TIÊU ĐỀ BÀI GIẢNG / BÀI VIẾT",
              "sections": [
                {"heading": "1. Tiêu đề phần", "en": "Đoạn văn tiếng Anh chi tiết", "vi": "Bản dịch tiếng Việt tương ứng"}
              ],
              "vocab": [
                {"word": "Thuật ngữ trọng tâm", "mean": "Nghĩa tiếng Việt"}
              ]
            }
            """

        contents.append(prompt_instruction)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        raw_text = response.text.strip()
        raw_text = re.sub(r'^```json\s*', '', raw_text)
        raw_text = re.sub(r'\s*```$', '', raw_text)
        parsed = json.loads(raw_text)
        return parsed, None
    except Exception as e:
        return None, f"Lỗi khi gọi AI tạo sinh: {str(e)}"

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
# TAB 3: HỌC TIẾNG ANH CÙNG AI (AI TẠO SINH THỰC THỤ + GIỌNG NAM/NỮ EDGE-TTS)
# ==============================================================================
with tab3:
    st.subheader("Hệ thống Học Tiếng Anh Tương tác cùng AI")

    if not get_gemini_api_key():
        with st.expander("Cấu hình Gemini API Key để kích hoạt AI Tạo sinh & Nhận diện Hình ảnh", expanded=True):
            key_in = st.text_input("Nhập Gemini API Key:", type="password", key="input_gem_key")
            if st.button("Lưu API Key"):
                st.session_state["user_gemini_key"] = key_in
                st.rerun()

    # Mục tải tài liệu Word / PDF / PNG (bỏ chữ "để tạo bài học tự động")
    with st.expander("Tải tài liệu lên (Word / PDF / PNG)", expanded=False):
        uploaded_file_t3 = st.file_uploader("Chọn file Word (.docx), PDF (.pdf) hoặc Hình ảnh (.png):", type=["docx", "pdf", "png"], key="t3_file_uploader")
        if uploaded_file_t3 is not None:
            if uploaded_file_t3.name.lower().endswith(".png"):
                st.image(uploaded_file_t3, caption="Hình ảnh đã tải lên", width=300)
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                if st.button("Tạo Hội thoại Nam/Nữ từ tài liệu/ảnh này", type="primary", use_container_width=True):
                    with st.spinner("AI đang phân tích hình ảnh/tài liệu và biên soạn hội thoại thực tế..."):
                        data, err = generate_ai_learning_content(uploaded_file=uploaded_file_t3, mode="dialogue")
                        if data:
                            st.session_state["ai_dialogue_data"] = data
                            st.session_state["ai_dialogue_audio"] = None
                            st.success("Đã tạo xong hội thoại!")
                        else:
                            st.error(err)
            with col_u2:
                if st.button("Tạo Bài viết / Kịch bản giảng từ tài liệu/ảnh này", use_container_width=True):
                    with st.spinner("AI đang biên soạn bài giảng chi tiết..."):
                        data, err = generate_ai_learning_content(uploaded_file=uploaded_file_t3, mode="lecture")
                        if data:
                            st.session_state["ai_lecture_data"] = data
                            st.success("Đã tạo xong bài viết!")
                        else:
                            st.error(err)

    # Thanh chọn chức năng con trong Tab 3
    sub_mode = st.radio(
        "Chọn chức năng học tập:",
        ["Video & Hội thoại Nam/Nữ (AI Tạo sinh)", "Bài viết & Kịch bản Giảng bài (Xuất Word)", "Từ điển & Luyện Nói AI"],
        horizontal=True,
        key="t3_sub_mode"
    )

    st.markdown("---")

    # --------------------------------------------------------------------------
    # CHỨC NĂNG 3.1: VIDEO & HỘI THOẠI ĐA VAI NAM / NỮ DO AI TẠO SINH
    # --------------------------------------------------------------------------
    if sub_mode == "Video & Hội thoại Nam/Nữ (AI Tạo sinh)":
        col_topic, col_btn = st.columns([3, 1])
        with col_topic:
            custom_scene_prompt = st.text_input(
                "Nhập tình huống thực tế bất kỳ để AI tạo hội thoại dài (VD: làm thủ tục nhập cảnh sân bay, mua vé tàu metro, khám bệnh...):",
                placeholder="Nhập chủ đề hoặc tình huống giao tiếp...",
                key="scene_prompt_input"
            )
        with col_btn:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            gen_scene_btn = st.button("AI Tạo Hội thoại", type="primary", use_container_width=True)

        if gen_scene_btn:
            if custom_scene_prompt.strip():
                with st.spinner("AI đang sáng tạo kịch bản hội thoại thực tế 8-10 lượt lời..."):
                    res_data, err = generate_ai_learning_content(topic_prompt=custom_scene_prompt, mode="dialogue")
                    if res_data:
                        st.session_state["ai_dialogue_data"] = res_data
                        st.session_state["ai_dialogue_audio"] = None
                    else:
                        st.error(err)
            else:
                st.warning("Vui lòng nhập tình huống hội thoại.")

        # Dữ liệu khởi tạo ban đầu nếu chưa bấm tạo mới
        if "ai_dialogue_data" not in st.session_state:
            st.session_state["ai_dialogue_data"] = {
                "title": "Hội thoại Thực tế: Thủ tục Nhập cảnh & Hải quan Sân bay",
                "video_category": "Du lịch, Sân bay & Giao thông",
                "turns": [
                    {"role": "Immigration Officer (Nhân viên An ninh)", "gender": "male", "en": "Good morning. May I see your passport and boarding pass, please?", "vi": "Chào buổi sáng. Vui lòng cho tôi xem hộ chiếu và thẻ lên máy bay của bà."},
                    {"role": "Passenger (Hành khách)", "gender": "female", "en": "Good morning, officer. Here are my passport, visa, and return ticket.", "vi": "Chào buổi sáng. Đây là hộ chiếu, thị thực và vé khứ hồi của tôi."},
                    {"role": "Immigration Officer (Nhân viên An ninh)", "gender": "male", "en": "What is the main purpose of your visit, and how long do you intend to stay?", "vi": "Mục đích chính chuyến đi của bà là gì, và bà dự định lưu trú bao lâu?"},
                    {"role": "Passenger (Hành khách)", "gender": "female", "en": "I am attending an international medical symposium at the university for five days.", "vi": "Tôi đến tham dự một hội nghị chuyên đề y khoa quốc tế tại trường đại học trong 5 ngày."},
                    {"role": "Immigration Officer (Nhân viên An ninh)", "gender": "male", "en": "Where will you be staying during your conference?", "vi": "Bà sẽ lưu trú ở đâu trong suốt thời gian diễn ra hội nghị?"},
                    {"role": "Passenger (Hành khách)", "gender": "female", "en": "I have a confirmed reservation at the Grand Central Hotel. Here is the booking confirmation.", "vi": "Tôi đã đặt phòng xác nhận tại khách sạn Grand Central. Đây là giấy xác nhận đặt phòng."},
                    {"role": "Immigration Officer (Nhân viên An ninh)", "gender": "male", "en": "Do you have any restricted items, food, or currency exceeding ten thousand dollars to declare?", "vi": "Bà có mang theo vật phẩm hạn chế, thực phẩm hay tiền mặt vượt quá 10.000 đô la cần khai báo không?"},
                    {"role": "Passenger (Hành khách)", "gender": "female", "en": "No, nothing to declare. I only have personal belongings and prescribed medication.", "vi": "Không, tôi không có gì cần khai báo. Tôi chỉ mang đồ dùng cá nhân và thuốc kê đơn."},
                    {"role": "Immigration Officer (Nhân viên An ninh)", "gender": "male", "en": "Everything looks in order. Please look at the camera for a quick photo. Welcome and enjoy your conference.", "vi": "Mọi thứ đều hợp lệ. Vui lòng nhìn vào camera để chụp ảnh. Chào mừng bà và chúc hội nghị thành công."}
                ],
                "vocab": [
                    {"word": "symposium", "ipa": "/sɪmˈpoʊ.zi.əm/", "mean": "hội nghị chuyên đề khoa học"},
                    {"word": "confirmed reservation", "ipa": "/kənˈfɝːmd ˌrez.ɚˈveɪ.ʃən/", "mean": "đặt phòng đã được xác nhận"},
                    {"word": "restricted items", "ipa": "/rɪˈstrɪk.tɪd ˈaɪ.t̬əmz/", "mean": "vật phẩm hạn chế nhập cảnh"}
                ],
                "grammar": {
                    "title": "Thì Hiện tại Tiếp diễn diễn tả kế hoạch đã sắp xếp trước",
                    "rule": "S + am/is/are + V-ing + (thời gian / địa điểm cụ thể)",
                    "example": "I am attending an international symposium and staying downtown for five days."
                }
            }

        dlg = st.session_state["ai_dialogue_data"]
        st.markdown(f"#### {dlg.get('title', 'Hội thoại Thực tế')}")

        col_vid, col_side = st.columns([1.4, 1])

        with col_vid:
            # Chọn video bối cảnh trực quan phát mượt 100% trên mọi thiết bị
            cat_default = dlg.get("video_category", "Du lịch, Sân bay & Giao thông")
            cat_keys = list(SAMPLE_VIDEOS.keys())
            default_idx = cat_keys.index(cat_default) if cat_default in cat_keys else 0
            selected_vid_cat = st.selectbox("Video bối cảnh minh họa:", cat_keys, index=default_idx, key="vid_cat_sel")
            st.video(SAMPLE_VIDEOS[selected_vid_cat])

            # Điều khiển Audio đa giọng Nam & Nữ chuẩn Edge-TTS (Chạy mượt trên điện thoại!)
            st.markdown("**Trình phát Hội thoại Giọng Nam & Nữ Bản xứ:**")
            c_aud1, c_aud2, c_aud3, c_aud4 = st.columns(4)
            with c_aud1:
                play_norm = st.button("Nghe Nam/Nữ (1.0x)", type="primary", use_container_width=True)
            with c_aud2:
                play_slow = st.button("Nghe chậm (0.7x)", use_container_width=True)
            with c_aud3:
                swap_g = st.checkbox("Đảo Nam/Nữ", key="swap_gender_chk")
            with c_aud4:
                show_sub = st.checkbox("Hiện phụ đề", value=True, key="show_sub_chk")

            if play_norm or play_slow:
                rate_val = 0.7 if play_slow else 1.0
                with st.spinner("Đang tổng hợp giọng đọc Nam & Nữ bản xứ..."):
                    mp3_bytes = generate_dialogue_mp3_bytes(dlg["turns"], speed_rate=rate_val, swap_gender=swap_g)
                    if mp3_bytes:
                        st.session_state["ai_dialogue_audio"] = mp3_bytes

            if st.session_state.get("ai_dialogue_audio"):
                st.audio(st.session_state["ai_dialogue_audio"], format="audio/mp3", autoplay=True)

            # Hiển thị kịch bản đối đáp từng vai
            st.markdown("---")
            for idx, turn in enumerate(dlg["turns"]):
                g = turn.get("gender", "male" if idx % 2 == 0 else "female").lower()
                if swap_g:
                    g = "female" if g == "male" else "male"
                css_cls = "dialogue-turn-male" if g == "male" else "dialogue-turn-female"
                g_label = "Giọng Nam" if g == "male" else "Giọng Nữ"
                
                if show_sub:
                    st.markdown(f"""
                    <div class="{css_cls}">
                        <div style="font-size:12px; font-weight:bold; color:#084298;">{turn['role']} ({g_label})</div>
                        <div style="font-size:15px; font-weight:bold; color:#111; margin-top:3px;">{turn['en']}</div>
                        <div style="font-size:13.5px; color:#555; font-style:italic; margin-top:3px;">{turn['vi']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="{css_cls}">
                        <div style="font-size:12px; font-weight:bold; color:#084298;">{turn['role']} ({g_label})</div>
                        <div style="font-size:14px; color:#888; font-style:italic;">[Đang ẩn phụ đề để luyện nghe]</div>
                    </div>
                    """, unsafe_allow_html=True)

        with col_side:
            st.markdown("**Từ vựng trọng tâm trong bài:**")
            for v in dlg.get("vocab", []):
                st.markdown(f"""
                <div style="background:#f8f9fa; border-left:4px solid #0d6efd; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                    <div style="font-weight:bold; color:#0d6efd; font-size:15px;">{v.get('word', '')} <span style="font-family:monospace; color:#6c757d; font-size:12px;">{v.get('ipa', '')}</span></div>
                    <div style="font-size:13.5px; color:#212529;">Nghĩa: <b>{v.get('mean', '')}</b></div>
                </div>
                """, unsafe_allow_html=True)

            gram = dlg.get("grammar", {})
            if gram:
                st.markdown("**Chủ điểm Ngữ pháp liên quan:**")
                st.markdown(f"""
                <div style="background:#e7f1ff; border:1px solid #b6d4fe; padding:12px; border-radius:6px;">
                    <div style="font-weight:bold; color:#084298; font-size:14px;">{gram.get('title', '')}</div>
                    <div style="background:#fff; padding:5px 8px; border-radius:4px; font-family:monospace; font-size:12px; color:#d63384; margin:6px 0;">{gram.get('rule', '')}</div>
                    <div style="font-size:13px;"><b>Ví dụ:</b> <i>"{gram.get('example', '')}"</i></div>
                </div>
                """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # CHỨC NĂNG 3.2: BÀI VIẾT & KỊCH BẢN GIẢNG BÀI + XUẤT FILE WORD (.DOC)
    # --------------------------------------------------------------------------
    elif sub_mode == "Bài viết & Kịch bản Giảng bài (Xuất Word)":
        col_l1, col_l2 = st.columns([3, 1])
        with col_l1:
            lec_prompt = st.text_input(
                "Nhập chủ đề bài giảng hoặc bài viết (VD: bài giảng kiểm định t-test 1 mẫu, quy trình tại ga metro...):",
                placeholder="Nhập chủ đề bất kỳ...",
                key="lec_prompt_input"
            )
        with col_l2:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            gen_lec_btn = st.button("AI Soạn Bài giảng", type="primary", use_container_width=True)

        if gen_lec_btn:
            if lec_prompt.strip():
                with st.spinner("AI đang biên soạn bài viết / kịch bản giảng dạy chi tiết..."):
                    res_lec, err = generate_ai_learning_content(topic_prompt=lec_prompt, mode="lecture")
                    if res_lec:
                        st.session_state["ai_lecture_data"] = res_lec
                    else:
                        st.error(err)
            else:
                st.warning("Vui lòng nhập chủ đề bài giảng.")

        if "ai_lecture_data" not in st.session_state:
            st.session_state["ai_lecture_data"] = {
                "title": "BÀI GIẢNG: KIỂM ĐỊNH T 1 MẪU (ONE-SAMPLE T-TEST IN BIOSTATISTICS)",
                "sections": [
                    {
                        "heading": "1. Opening & Purpose (Mở đầu & Mục đích kiểm định)",
                        "en": "Good morning everyone. Today we will discuss the One-Sample t-Test, a fundamental parametric test used to determine whether the mean of a single sample differs significantly from a known or hypothesized population mean.",
                        "vi": "Chào buổi sáng tất cả các bạn. Hôm nay chúng ta sẽ thảo luận về Kiểm định t một mẫu, một kiểm định tham số cơ bản dùng để xác định xem trung bình của một mẫu đơn lẻ có khác biệt có ý nghĩa thống kê so với trung bình quần thể giả định hay không."
                    },
                    {
                        "heading": "2. Key Assumptions & Formula (Giả định cốt lõi & Công thức)",
                        "en": "Before applying this test, ensure the dependent variable is continuous, observations are independent, and data are approximately normally distributed. The t-statistic is computed as the difference between the sample mean and hypothesized mean divided by the standard error.",
                        "vi": "Trước khi áp dụng kiểm định này, hãy đảm bảo biến phụ thuộc là biến liên tục, các quan sát độc lập và dữ liệu phân phối xấp xỉ chuẩn. Trị số thống kê t được tính bằng hiệu số giữa trung bình mẫu và trung bình giả định chia cho sai số chuẩn."
                    }
                ],
                "vocab": [
                    {"word": "One-Sample t-Test", "mean": "Kiểm định t một mẫu"},
                    {"word": "Standard error (SE)", "mean": "Sai số chuẩn"}
                ]
            }

        lec = st.session_state["ai_lecture_data"]

        # Tạo nội dung file Word chuẩn tải về ngay lập tức
        word_body = f"<h2 style='text-align:center; color:#084298; font-family:\"Times New Roman\", serif;'>{lec.get('title', '')}</h2><hr/>"
        for s in lec.get("sections", []):
            word_body += f"""
                <p style='font-weight:bold; color:#0d6efd; font-size:13pt;'>{s.get('heading', '')}</p>
                <p style='font-size:12pt; line-height:1.5;'>{s.get('en', '')}</p>
                <p style='font-size:11.5pt; font-style:italic; color:#333;'><i>(Dịch nghĩa: {s.get('vi', '')})</i></p>
            """
        if lec.get("vocab"):
            word_body += "<p style='font-weight:bold; color:#084298; font-size:13pt;'>THUẬT NGỮ TRỌNG TÂM:</p><ul>"
            for v in lec["vocab"]:
                word_body += f"<li style='font-size:12pt;'><b>{v.get('word', '')}:</b> {v.get('mean', '')}</li>"
            word_body += "</ul>"

        full_word_html = f"<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><style>body{{font-family:'Times New Roman',serif;}}</style></head><body>{word_body}</body></html>"

        col_w1, col_w2, col_w3 = st.columns([1.2, 1.2, 1])
        with col_w1:
            st.download_button(
                label="Tải về file Word (.doc)",
                data=full_word_html.encode("utf-8"),
                file_name="Kich_Ban_Bai_Giang_AI.doc",
                mime="application/msword",
                type="primary",
                use_container_width=True
            )
        with col_w2:
            if st.button("Nghe toàn bộ bài giảng (Giọng Nam)", use_container_width=True):
                full_en = " ".join([s.get("en", "") for s in lec.get("sections", [])])
                if create_mp3(full_en, "us Nam - Anh-Mỹ (Guy - Trầm ấm)", 1.0, "lecture_audio.mp3"):
                    with open("lecture_audio.mp3", "rb") as f:
                        st.session_state["lec_mp3"] = f.read()
        with col_w3:
            show_lec_vi = st.checkbox("Hiện bản dịch Việt", value=True, key="chk_lec_vi")

        if st.session_state.get("lec_mp3"):
            st.audio(st.session_state["lec_mp3"], format="audio/mp3")

        # Khung hiển thị bài viết có thanh cuộn dọc và tự co giãn ngang trên điện thoại
        display_html = f"<div class='lecture-container'><h4 style='color:#084298; border-bottom:2px solid #0d6efd; padding-bottom:6px;'>{lec.get('title', '')}</h4>"
        for s in lec.get("sections", []):
            vi_block = f"<div style='color:#495057; font-style:italic; margin-top:6px; border-top:1px dashed #ced4da; padding-top:4px;'>{s.get('vi', '')}</div>" if show_lec_vi else ""
            display_html += f"""
            <div style='background:#f8f9fa; border-left:4px solid #0d6efd; padding:10px 12px; margin-bottom:12px; border-radius:4px;'>
                <div style='font-weight:bold; color:#0d6efd; margin-bottom:4px;'>{s.get('heading', '')}</div>
                <div style='color:#111; line-height:1.55;'>{s.get('en', '')}</div>
                {vi_block}
            </div>
            """
        if lec.get("vocab"):
            display_html += "<div style='background:#e7f1ff; padding:10px; border-radius:6px;'><b>Từ vựng & Thuật ngữ trọng tâm:</b><ul>"
            for v in lec["vocab"]:
                display_html += f"<li><b>{v.get('word', '')}:</b> {v.get('mean', '')}</li>"
            display_html += "</ul></div>"
        display_html += "</div>"

        st.markdown(display_html, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # CHỨC NĂNG 3.3: TỪ ĐIỂN & LUYỆN PHÁT ÂM AI
    # --------------------------------------------------------------------------
    else:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown("**Tra cứu Từ điển & Phát âm Chuẩn**")
            dict_word = st.text_input("Nhập từ vựng tiếng Anh:", placeholder="VD: hypothesis, immigration, platform...", key="dict_w_in")
            if st.button("Tra cứu từ vựng", type="primary"):
                if dict_word.strip():
                    vi_res = translate_stable(dict_word, "en", "vi")
                    st.success(f"**{dict_word}**: {vi_res}")
                    if create_mp3(dict_word, "us Nữ - Anh-Mỹ (Jenny - Truyền cảm)", 0.95, "dict_word.mp3"):
                        with open("dict_word.mp3", "rb") as f:
                            st.audio(f.read(), format="audio/mp3")
        with col_d2:
            st.markdown("**Gia sư Chỉnh sửa Câu Song ngữ**")
            tutor_q = st.text_input("Nhập câu tiếng Việt cần diễn đạt hoặc câu tiếng Anh cần AI sửa:", key="tutor_q_in")
            if st.button("Hỏi Gia sư AI"):
                if tutor_q.strip():
                    is_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', tutor_q, re.I))
                    if is_vi:
                        en_out = translate_stable(tutor_q, "vi", "en")
                        st.info(f"**Diễn đạt Tiếng Anh tự nhiên:** {en_out}")
                        if create_mp3(en_out, "us Nam - Anh-Mỹ (Guy - Trầm ấm)", 0.95, "tutor_out.mp3"):
                            with open("tutor_out.mp3", "rb") as f:
                                st.audio(f.read(), format="audio/mp3")
                    else:
                        vi_out = translate_stable(tutor_q, "en", "vi")
                        st.info(f"**Nghĩa tiếng Việt:** {vi_out}")
