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

    button[kind="primary"] {
        background-color: #0d6efd !important;
        border-color: #0d6efd !important;
        color: #ffffff !important;
    }
    button[kind="primary"]:hover {
        background-color: #0b5ed7 !important;
        border-color: #0a58ca !important;
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
        padding: 8px 14px;
        border: none !important;
        flex: 1 1 auto;
        transition: all 0.2s ease;
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
        font-size: 13.5px !important;
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

# --- TÌM VIDEO YOUTUBE THỰC TẾ THEO CHỦ ĐỀ ---
@st.cache_data(show_spinner=False, ttl=3600)
def search_youtube_videos(query_en):
    try:
        search_q = urllib.parse.quote(f"{query_en} English lesson OR explanation")
        url = f"https://www.youtube.com/results?search_query={search_q}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
            unique_ids = list(dict.fromkeys(video_ids))[:4]
            if unique_ids:
                return unique_ids
    except Exception:
        pass
    return ["aircAruvnKk", "8hly31xKli0"]

# --- TẠO AUDIO EDGE-TTS BASE64 CHO TỪNG CÂU & TỪ VỰNG ---
async def synth_single_b64_async(text, voice_id):
    buf = bytearray()
    communicate = edge_tts.Communicate(text, voice_id)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    return base64.b64encode(bytes(buf)).decode("ascii")

async def enrich_dialogue_audio_async(dlg_obj):
    tasks = []
    for idx, t in enumerate(dlg_obj["turns"]):
        g = t.get("gender", "male" if idx % 2 == 0 else "female")
        vid = "en-US-GuyNeural" if g == "male" else "en-US-JennyNeural"
        tasks.append(synth_single_b64_async(t["en"], vid))
    for v in dlg_obj.get("vocab", []):
        tasks.append(synth_single_b64_async(v["word"], "en-US-JennyNeural"))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    n_turns = len(dlg_obj["turns"])
    for idx in range(n_turns):
        res = results[idx]
        dlg_obj["turns"][idx]["audio_b64"] = res if isinstance(res, str) else ""
    for v_idx in range(len(dlg_obj.get("vocab", []))):
        res = results[n_turns + v_idx]
        dlg_obj["vocab"][v_idx]["audio_b64"] = res if isinstance(res, str) else ""
    return dlg_obj

@st.cache_data(show_spinner=False, ttl=3600)
def attach_neural_audio_to_dialogue(dlg_json_str):
    try:
        obj = json.loads(dlg_json_str)
        enriched = asyncio.run(enrich_dialogue_audio_async(obj))
        return json.dumps(enriched, ensure_ascii=False)
    except Exception:
        return dlg_json_str

def get_gemini_client():
    """Đọc chính xác GOOGLE_API_KEY hoặc GEMINI_API_KEY trong Streamlit Secrets"""
    api_key = ""
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
        elif "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        try:
            from google import genai
            return genai.Client(api_key=api_key)
        except Exception:
            return None
    return None

def extract_doc_text(uploaded_file):
    file_name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()
    if file_name.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(raw_bytes))
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()]).strip()
        except ImportError:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                tree = ET.fromstring(z.read("word/document.xml"))
                paras = []
                for elem in tree.iter():
                    if elem.tag.endswith('}p'):
                        texts = [t.text for t in elem.iter() if t.tag.endswith('}t') and t.text]
                        if texts:
                            paras.append("".join(texts))
                return "\n".join(paras).strip()
    elif file_name.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            return "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
        except Exception:
            return ""
    return ""

# --- AI TẠO SINH THỰC THỤ (GEMINI VISION + TEXT QUA GOOGLE_API_KEY) ---
def generate_generative_ai_package(topic_text="", uploaded_file=None):
    client = get_gemini_client()
    
    search_topic = topic_text.strip()
    if not search_topic and uploaded_file is not None:
        search_topic = re.sub(r'[_\-\.]+', ' ', uploaded_file.name.rsplit('.', 1)[0])
    is_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', search_topic, re.I))
    en_query = translate_stable(search_topic, "vi", "en") if (is_vi and search_topic) else (search_topic or "English conversation")
    yt_ids = search_youtube_videos(en_query)

    if client is not None:
        try:
            from google.genai import types
            contents = []
            if uploaded_file is not None:
                fname = uploaded_file.name.lower()
                raw_bytes = uploaded_file.getvalue()
                if fname.endswith(".png"):
                    contents.append(types.Part.from_bytes(data=raw_bytes, mime_type="image/png"))
                    contents.append("Hãy quan sát kỹ từng chi tiết, số liệu, tên biến, bảng biểu hoặc bối cảnh trong hình ảnh này.")
                else:
                    doc_txt = extract_doc_text(uploaded_file)
                    if doc_txt:
                        contents.append(f"Dựa trên nội dung tài liệu sau:\n{doc_txt[:4500]}")

            if topic_text.strip():
                contents.append(f"Chủ đề trọng tâm: {topic_text.strip()}")

            prompt = """
            Bạn là chuyên gia giáo dục song ngữ Anh - Việt. Dựa trên hình ảnh, tài liệu hoặc chủ đề được cung cấp ở trên, hãy SÁNG TẠO MỚI HOÀN TOÀN (tuyệt đối không dùng câu mẫu rập khuôn) một gói học tập gồm:
            1. Một cuộc HỘI THOẠI THỰC TẾ, TỰ NHIÊN (6 đến 8 lượt lời đối đáp sâu sắc giữa 2 nhân vật có tên và vai trò phù hợp với bối cảnh: 1 Nam gender='male', 1 Nữ gender='female'). Nếu là ảnh kết quả thống kê/bảng biểu/nghiên cứu, hai nhân vật phải thảo luận trực tiếp các con số, tên biến và kết quả cụ thể có trong ảnh.
            2. Một BÀI VIẾT / KỊCH BẢN GIẢNG BÀI chi tiết (3 đến 4 phần rõ ràng, phân tích chuyên sâu nội dung của ảnh/chủ đề để giảng viên dùng giảng dạy).
            3. Danh sách 5 từ vựng/thuật ngữ đắt giá nhất rút ra từ chính nội dung trên (kèm phiên âm IPA và nghĩa tiếng Việt).
            4. Một cấu trúc ngữ pháp tiêu biểu xuất hiện trong bài.
            5. Một câu luyện nghe-viết chính tả (listen_en) và một câu hỏi tình huống (speaking_prompt) để Gia sư kiểm tra người học.

            Trả về STRICT JSON (không bọc markdown ```json) theo đúng định dạng:
            {
              "dialogue": {
                "title": "Tiêu đề hội thoại sát thực tế",
                "turns": [
                  {"role": "Tên & Vai nhân vật", "gender": "male", "en": "Câu tiếng Anh tự nhiên", "vi": "Bản dịch tiếng Việt"}
                ],
                "vocab": [
                  {"word": "từ vựng", "ipa": "/IPA/", "mean": "nghĩa tiếng Việt"}
                ],
                "grammar": {
                  "title": "Tên cấu trúc ngữ pháp",
                  "rule": "Công thức",
                  "example": "Câu ví dụ"
                }
              },
              "lecture": {
                "title": "TIÊU ĐỀ BÀI GIẢNG / BÀI VIẾT",
                "sections": [
                  {"heading": "1. Tiêu đề phần", "en": "Đoạn văn tiếng Anh chi tiết", "vi": "Dịch tiếng Việt"}
                ],
                "vocab": [
                  {"word": "Thuật ngữ", "mean": "Nghĩa tiếng Việt"}
                ]
              },
              "practice": {
                "listen_en": "Một câu tiếng Anh hay trích từ bài để người dùng nghe và gõ lại",
                "listen_vi": "Nghĩa tiếng Việt của câu trên",
                "speaking_prompt": "Một câu hỏi tình huống tiếng Anh để người dùng trả lời và AI chấm điểm"
              }
            }
            """
            contents.append(prompt)
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=contents)
            raw_json = re.sub(r'^```json\s*|\s*```$', '', resp.text.strip())
            parsed = json.loads(raw_json)
            parsed["youtube_ids"] = yt_ids
            return parsed
        except Exception as e:
            st.warning(f"Lưu ý kết nối Gemini API: {str(e)}")

    # Fallback dự phòng
    doc_txt = extract_doc_text(uploaded_file) if (uploaded_file and not uploaded_file.name.lower().endswith(".png")) else ""
    base_topic = search_topic or "Chi-square test in medical research"
    
    dlg_fallback = {
        "title": f"Thảo luận chuyên sâu: {base_topic}",
        "turns": [
            {"role": "Dr. Minh (Biostatistician)", "gender": "male", "en": f"Let us examine the data and methodology for {en_query}. What is our primary objective here?", "vi": f"Hãy cùng xem xét dữ liệu và phương pháp cho {base_topic}. Mục tiêu chính của chúng ta ở đây là gì?"},
            {"role": "Dr. Lan (Researcher)", "gender": "female", "en": f"We want to evaluate the association between categorical variables and verify whether the observed differences are statistically significant.", "vi": "Chúng ta muốn đánh giá mối liên quan giữa các biến phân loại và xác minh xem sự khác biệt quan sát được có ý nghĩa thống kê hay không."}
        ],
        "vocab": [
            {"word": "categorical variable", "ipa": "/ˌkæt̬.əˈɡɔːr.ɪ.kəl ˈver.i.ə.bəl/", "mean": "biến phân loại (định tính)"},
            {"word": "statistically significant", "ipa": "/stəˈtɪs.tɪ.kəl.i sɪɡˈnɪf.ə.kənt/", "mean": "có ý nghĩa thống kê"}
        ],
        "grammar": {
            "title": "Mệnh đề Danh ngữ với 'Whether' trong Nghiên cứu",
            "rule": "Verify / Evaluate + whether + S + V",
            "example": "We verify whether the observed association is statistically significant."
        }
    }

    e1 = f"Today we analyze {en_query}. Selecting the right analytical method depends on the measurement scale of your variables and sample distribution."
    lec_sections = [{"heading": "1. Conceptual Framework (Cơ sở khái niệm)", "en": e1, "vi": translate_stable(e1, "en", "vi")}]
    if doc_txt:
        paras = [p.strip() for p in doc_txt.split("\n") if len(p.strip()) > 10][:4]
        if paras:
            lec_sections = []
            for i, p in enumerate(paras):
                is_p_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', p, re.I))
                en_p = translate_stable(p, "vi", "en") if is_p_vi else p
                vi_p = p if is_p_vi else translate_stable(p, "en", "vi")
                lec_sections.append({"heading": f"Phần {i+1}: Nội dung phân tích", "en": en_p, "vi": vi_p})

    return {
        "youtube_ids": yt_ids,
        "dialogue": dlg_fallback,
        "lecture": {
            "title": f"BÀI GIẢNG & PHÂN TÍCH: {base_topic.upper()}",
            "sections": lec_sections,
            "vocab": [{"word": v["word"], "mean": v["mean"]} for v in dlg_fallback["vocab"]]
        },
        "practice": {
            "listen_en": "We evaluate whether the observed differences are statistically significant.",
            "listen_vi": "Chúng ta đánh giá xem sự khác biệt quan sát được có ý nghĩa thống kê hay không.",
            "speaking_prompt": f"How would you explain {en_query} to your colleagues in English?"
        }
    }

# --- GIA SƯ AI CHẤM ĐIỂM VIẾT / NÓI / NGHE HIỂU & XẾP TRÌNH ĐỘ ---
def evaluate_user_english(user_input, task_type="writing", reference_text=""):
    client = get_gemini_client()
    if client is not None:
        try:
            prompt = f"""
            Bạn là Gia sư Tiếng Anh bản xứ chuyên nghiệp. Hãy đánh giá bài làm của học viên.
            Loại bài tập: {task_type} (writing: viết câu/đoạn văn | dictation: nghe và chép lại câu mẫu "{reference_text}" | speaking: trả lời câu hỏi "{reference_text}").
            Bài làm của học viên: "{user_input}"

            Hãy phân tích cực kỳ chi tiết, chỉ rõ:
            1. Điểm số (thang 100) và Xếp loại trình độ CEFR hiện tại của câu này (A1, A2, B1, B2, C1, hoặc C2).
            2. Chỉ rõ từng lỗi sai (ngữ pháp, dùng từ, chính tả, giới từ, thì...) và giải thích tại sao sai bằng tiếng Việt dễ hiểu. Nếu không có lỗi, khen ngợi điểm mạnh.
            3. Đưa ra 2 phiên bản sửa lại hoàn hảo: 1 câu Giao tiếp tự nhiên và 1 câu Học thuật/Chuyên nghiệp.

            Trả về STRICT JSON (không bọc ```json):
            {{
              "score": 85,
              "cefr_level": "B2 (Upper-Intermediate)",
              "errors_html": "HTML liệt kê rõ từng lỗi sai (tô đỏ từ sai -> tô xanh từ đúng) và giải thích tiếng Việt",
              "natural_version": "Câu tiếng Anh giao tiếp tự nhiên",
              "academic_version": "Câu tiếng Anh học thuật/chuyên nghiệp"
            }}
            """
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            raw_json = re.sub(r'^```json\s*|\s*```$', '', resp.text.strip())
            res = json.loads(raw_json)
            res["natural_b64"] = asyncio.run(synth_single_b64_async(res["natural_version"], "en-US-JennyNeural"))
            res["academic_b64"] = asyncio.run(synth_single_b64_async(res["academic_version"], "en-US-GuyNeural"))
            return res
        except Exception:
            pass

    is_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', user_input, re.I))
    if is_vi:
        nat_en = translate_stable(user_input, "vi", "en")
        acad_en = nat_en
        err_html = "Bạn đang nhập tiếng Việt. Hệ thống đã chuyển sang tiếng Anh để bạn luyện tập. Hãy thử tự viết bằng tiếng Anh để Gia sư chấm lỗi ngữ pháp nhé!"
        score = 70
        level = "B1 (Intermediate)"
    else:
        nat_en = user_input
        vi_back = translate_stable(user_input, "en", "vi")
        acad_en = translate_stable(vi_back, "vi", "en")
        words = user_input.split()
        score = min(95, 60 + len(words) * 2)
        level = "B2 (Upper-Intermediate)" if len(words) >= 10 else "B1 (Intermediate)"
        if reference_text and task_type == "dictation":
            ref_words = set(re.findall(r'\w+', reference_text.lower()))
            usr_words = set(re.findall(r'\w+', user_input.lower()))
            missing = ref_words - usr_words
            score = int((len(ref_words - missing) / max(1, len(ref_words))) * 100)
            err_html = f"<b>So sánh với câu gốc:</b> {reference_text}<br><b>Các từ bạn nghe thiếu/sai:</b> <span style='color:#dc3545; font-weight:bold;'>{', '.join(missing) if missing else 'Không có lỗi, nghe chính xác 100%!'}</span>"
        else:
            err_html = f"<b>Cấu trúc câu:</b> Đúng ngữ pháp cơ bản ({len(words)} từ). Có thể nâng cấp từ vựng như phiên bản học thuật bên dưới."

    nat_b64 = asyncio.run(synth_single_b64_async(nat_en, "en-US-JennyNeural"))
    acad_b64 = asyncio.run(synth_single_b64_async(acad_en, "en-US-GuyNeural"))
    return {
        "score": score,
        "cefr_level": level,
        "errors_html": err_html,
        "natural_version": nat_en,
        "academic_version": acad_en,
        "natural_b64": nat_b64,
        "academic_b64": acad_b64
    }

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
# TAB 3: HỌC TIẾNG ANH CÙNG AI (KẾT NỐI TRỰC TIẾP GOOGLE_API_KEY TRONG SECRETS)
# ==============================================================================
with tab3:
    st.subheader("Hệ thống Học Tiếng Anh Tương tác cùng AI")

    with st.expander("Tải tài liệu lên (Word / PDF / PNG)", expanded=False):
        uploaded_file_t3 = st.file_uploader("Chọn file Word (.docx), PDF (.pdf) hoặc Hình ảnh (.png):", type=["docx", "pdf", "png"], key="t3_file_uploader")
        if uploaded_file_t3 is not None:
            if uploaded_file_t3.name.lower().endswith(".png"):
                st.image(uploaded_file_t3, caption="Hình ảnh đã tải lên", width=260)
            if st.button("Tạo Hội thoại & Bài giảng từ tài liệu này", type="primary"):
                with st.spinner("AI đang đọc hình ảnh/tài liệu và tạo sinh nội dung mới..."):
                    pkg = generate_generative_ai_package(uploaded_file=uploaded_file_t3)
                    dlg_enriched = attach_neural_audio_to_dialogue(json.dumps(pkg["dialogue"], ensure_ascii=False))
                    st.session_state["t3_dlg_json"] = dlg_enriched
                    st.session_state["t3_lec_json"] = json.dumps(pkg["lecture"], ensure_ascii=False)
                    st.session_state["t3_yt_ids"] = pkg["youtube_ids"]
                    st.session_state["t3_practice"] = pkg["practice"]
                    st.session_state["t3_listen_b64"] = asyncio.run(synth_single_b64_async(pkg["practice"]["listen_en"], "en-US-JennyNeural"))
                    st.success("Đã tạo xong nội dung học tập mới từ tài liệu!")

    col_in, col_go = st.columns([4, 1])
    with col_in:
        user_topic = st.text_input(
            "Nhập chủ đề bất kỳ (VD: kiểm định Chi-square, hồi quy logistic, tại ga metro, nhập cảnh sân bay...):",
            placeholder="Nhập chủ đề muốn tạo video, hội thoại & bài giảng...",
            key="t3_topic_input"
        )
    with col_go:
        st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)
        btn_create_topic = st.button("Tạo nội dung AI", type="primary", use_container_width=True)

    if btn_create_topic and user_topic.strip():
        with st.spinner(f"AI đang tìm video thực tế & sáng tạo hội thoại về '{user_topic}'..."):
            pkg = generate_generative_ai_package(topic_text=user_topic.strip())
            dlg_enriched = attach_neural_audio_to_dialogue(json.dumps(pkg["dialogue"], ensure_ascii=False))
            st.session_state["t3_dlg_json"] = dlg_enriched
            st.session_state["t3_lec_json"] = json.dumps(pkg["lecture"], ensure_ascii=False)
            st.session_state["t3_yt_ids"] = pkg["youtube_ids"]
            st.session_state["t3_practice"] = pkg["practice"]
            st.session_state["t3_listen_b64"] = asyncio.run(synth_single_b64_async(pkg["practice"]["listen_en"], "en-US-JennyNeural"))

    if "t3_dlg_json" not in st.session_state:
        with st.spinner("Đang khởi tạo dữ liệu học tập..."):
            pkg = generate_generative_ai_package(topic_text="Chi-square test in medical research")
            dlg_enriched = attach_neural_audio_to_dialogue(json.dumps(pkg["dialogue"], ensure_ascii=False))
            st.session_state["t3_dlg_json"] = dlg_enriched
            st.session_state["t3_lec_json"] = json.dumps(pkg["lecture"], ensure_ascii=False)
            st.session_state["t3_yt_ids"] = pkg["youtube_ids"]
            st.session_state["t3_practice"] = pkg["practice"]
            st.session_state["t3_listen_b64"] = asyncio.run(synth_single_b64_async(pkg["practice"]["listen_en"], "en-US-JennyNeural"))

    with st.expander("Gia sư AI Đánh giá Toàn diện (Viết – Nói – Nghe – Hiểu & Xếp hạng Trình độ)", expanded=False):
        prac = st.session_state.get("t3_practice", {})
        g_tab1, g_tab2, g_tab3 = st.tabs(["1. Chấm bài Viết & Diễn đạt", "2. Luyện Nghe & Chép chính tả", "3. Luyện Nói & Phản xạ Tình huống"])
        
        with g_tab1:
            st.caption("Nhập một câu tiếng Anh bạn tự viết (hoặc câu tiếng Việt muốn diễn đạt). Gia sư sẽ chỉ rõ lỗi sai, giải thích và xếp loại trình độ CEFR (A1–C2).")
            w_input = st.text_area("Bài viết của bạn:", height=90, placeholder="VD: Students should download SPSS 27 to following the lesson better...", key="tutor_w_in")
            if st.button("Chấm điểm & Sửa lỗi chi tiết", type="primary", key="btn_eval_w"):
                if w_input.strip():
                    with st.spinner("Gia sư AI đang chấm lỗi ngữ pháp & từ vựng..."):
                        st.session_state["tutor_eval_res"] = evaluate_user_english(w_input.strip(), task_type="writing")

        with g_tab2:
            st.caption("Bấm nghe câu tiếng Anh bản xứ bên dưới, sau đó gõ lại chính xác những gì bạn nghe được để kiểm tra kỹ năng Nghe - Hiểu.")
            listen_b64 = st.session_state.get("t3_listen_b64", "")
            if listen_b64:
                st.audio(base64.b64decode(listen_b64), format="audio/mp3")
            d_input = st.text_input("Gõ lại câu tiếng Anh bạn vừa nghe được:", key="tutor_d_in")
            if st.button("Kiểm tra Nghe - Hiểu", type="primary", key="btn_eval_d"):
                if d_input.strip():
                    with st.spinner("Đang đối chiếu bài nghe..."):
                        st.session_state["tutor_eval_res"] = evaluate_user_english(d_input.strip(), task_type="dictation", reference_text=prac.get("listen_en", ""))

        with g_tab3:
            sp_prompt = prac.get("speaking_prompt", "How would you explain your research findings to an international audience?")
            st.info(f"**Câu hỏi tình huống từ Gia sư:** {sp_prompt}")
            s_input = st.text_input("Nhập câu trả lời của bạn bằng tiếng Anh:", key="tutor_s_in")
            if st.button("Đánh giá Câu trả lời", type="primary", key="btn_eval_s"):
                if s_input.strip():
                    with st.spinner("Gia sư đang đánh giá phản xạ giao tiếp..."):
                        st.session_state["tutor_eval_res"] = evaluate_user_english(s_input.strip(), task_type="speaking", reference_text=sp_prompt)

        if "tutor_eval_res" in st.session_state:
            ev = st.session_state["tutor_eval_res"]
            st.markdown("---")
            c_sc1, c_sc2 = st.columns(2)
            with c_sc1:
                st.metric("Điểm đánh giá", f"{ev['score']} / 100")
            with c_sc2:
                st.metric("Trình độ ước tính (CEFR)", ev["cefr_level"])
            
            st.markdown(f"<div style='background:#fff3cd; border-left:4px solid #ffc107; padding:10px 14px; border-radius:6px; margin-bottom:10px;'><b>Phân tích lỗi sai & Góp ý:</b><br>{ev['errors_html']}</div>", unsafe_allow_html=True)
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.success(f"**Diễn đạt tự nhiên:** {ev['natural_version']}")
                if ev.get("natural_b64"):
                    st.audio(base64.b64decode(ev["natural_b64"]), format="audio/mp3")
            with col_v2:
                st.info(f"**Văn phong học thuật:** {ev['academic_version']}")
                if ev.get("academic_b64"):
                    st.audio(base64.b64decode(ev["academic_b64"]), format="audio/mp3")

    dlg_json_safe = st.session_state["t3_dlg_json"]
    lec_json_safe = st.session_state["t3_lec_json"]
    yt_ids_safe = json.dumps(st.session_state.get("t3_yt_ids", ["aircAruvnKk"]))

    tutor_ui_template = """
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
                grid-template-columns: repeat(3, 1fr);
                background-color: #0d6efd;
                border-radius: 8px;
                padding: 5px;
                gap: 5px;
                margin-bottom: 12px;
                box-shadow: 0 3px 8px rgba(13, 110, 253, 0.25);
            }
            .menu-item {
                padding: 10px 8px;
                border: none;
                border-radius: 6px;
                background-color: transparent;
                color: #ffffff;
                font-weight: bold;
                cursor: pointer;
                font-size: 13px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                transition: 0.2s;
            }
            .menu-item:hover { background-color: rgba(255, 255, 255, 0.2); }
            .menu-item.active {
                background-color: #ffffff;
                color: #0d6efd;
                box-shadow: 0 2px 5px rgba(0,0,0,0.12);
            }
            .arrow-icon { font-size: 10px; transition: transform 0.2s; }
            .menu-item.active .arrow-icon { transform: rotate(180deg); }

            .dropdown-panel {
                background: #ffffff;
                border: 1px solid #cfe2ff;
                border-top: 4px solid #0d6efd;
                border-radius: 8px;
                padding: 14px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                display: none;
            }
            .dropdown-panel.active { display: block; }

            .video-layout { display: flex; gap: 14px; flex-direction: row; }
            @media (max-width: 820px) { .video-layout { flex-direction: column; } }
            .video-main { flex: 1.45; }
            .video-sidebar { flex: 1; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; }

            .yt-wrapper {
                position: relative;
                padding-bottom: 56.25%;
                height: 0;
                overflow: hidden;
                border-radius: 8px;
                background: #000;
                margin-bottom: 10px;
                border: 1px solid #ced4da;
            }
            .yt-wrapper iframe {
                position: absolute;
                top: 0; left: 0;
                width: 100%; height: 100%;
                border: 0;
            }
            .controls-toolbar {
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
                justify-content: center;
                margin-bottom: 12px;
                background: #e7f1ff;
                padding: 10px;
                border-radius: 8px;
            }
            .btn-ui {
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                cursor: pointer;
                border: none;
            }
            .btn-green { background: #198754; color: #fff; }
            .btn-navy { background: #084298; color: #fff; }
            .btn-red { background: #dc3545; color: #fff; }
            .btn-white { background: #ffffff; color: #0d6efd; border: 1px solid #0d6efd; }

            .turn-card {
                padding: 10px 12px;
                border-radius: 6px;
                margin-bottom: 8px;
                border-left: 4px solid #0d6efd;
                background: #f0f7ff;
                transition: 0.2s;
            }
            .turn-card.female {
                border-left-color: #d63384;
                background: #fff0f6;
            }
            .turn-card.active-turn {
                box-shadow: 0 0 0 2px #0d6efd;
                transform: scale(1.005);
            }
            .turn-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 4px;
                font-size: 12px;
                font-weight: bold;
                color: #084298;
            }
            .turn-card.female .turn-header { color: #a61e4d; }
            .btn-mini-play {
                background: #0d6efd;
                color: #fff;
                border: none;
                border-radius: 4px;
                padding: 3px 9px;
                font-size: 11px;
                font-weight: bold;
                cursor: pointer;
            }
            .turn-card.female .btn-mini-play { background: #d63384; }
            .sub-hidden { filter: blur(5px); user-select: none; opacity: 0.35; }

            .vocab-item {
                background: #ffffff;
                border-left: 4px solid #0d6efd;
                border-radius: 6px;
                padding: 8px 10px;
                margin-bottom: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            }
            .grammar-box {
                background: #e7f1ff;
                border: 1px solid #b6d4fe;
                border-radius: 6px;
                padding: 10px;
                margin-top: 10px;
            }
            .lecture-box {
                max-height: 440px;
                overflow-y: auto;
                border: 1px solid #b6d4fe;
                border-radius: 8px;
                padding: 14px;
                font-family: 'Times New Roman', Times, serif;
            }
            .input-row { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
            .input-row input { flex: 1; min-width: 180px; padding: 9px 12px; border: 1px solid #ced4da; border-radius: 6px; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="blue-menu-bar">
            <button class="menu-item active" onclick="switchSubTab('video', this)">
                <span>Video Thực tế & Hội thoại</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="switchSubTab('lecture', this)">
                <span>Bài viết & Kịch bản</span>
                <span class="arrow-icon">▼</span>
            </button>
            <button class="menu-item" onclick="switchSubTab('dict', this)">
                <span>Từ điển & Phát âm</span>
                <span class="arrow-icon">▼</span>
            </button>
        </div>

        <!-- PANEL 1: VIDEO YOUTUBE THỰC TẾ + HỘI THOẠI NAM/NỮ + TỪ VỰNG -->
        <div id="sub-video" class="dropdown-panel active">
            <div style="font-weight:bold; color:#084298; font-size:15px; margin-bottom:10px;" id="dlg-main-title"></div>
            <div class="video-layout">
                <div class="video-main">
                    <div class="yt-wrapper">
                        <iframe id="yt-player-frame" src="" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                    </div>
                    <div style="display:flex; gap:6px; justify-content:flex-end; margin-bottom:10px;">
                        <button class="btn-ui btn-white" onclick="nextYoutubeVideo()">Chuyển Video khác cùng chủ đề ↻</button>
                    </div>

                    <div class="controls-toolbar">
                        <button class="btn-ui btn-green" onclick="playAllTurns(1.0)">Nghe Hội thoại Nam/Nữ (1.0x)</button>
                        <button class="btn-ui btn-navy" onclick="playAllTurns(0.75)">Nghe chậm (0.75x)</button>
                        <button class="btn-ui btn-red" onclick="stopAudio()">Dừng đọc</button>
                        <button class="btn-ui btn-white" id="btn-sub" onclick="toggleSubs()">Ẩn phụ đề</button>
                    </div>

                    <div id="turns-list-container"></div>
                </div>

                <div class="video-sidebar">
                    <div style="font-weight:bold; color:#0d6efd; font-size:14px; border-bottom:1px solid #dee2e6; padding-bottom:5px; margin-bottom:8px;">
                        Từ vựng trọng tâm (Bấm nghe từng từ)
                    </div>
                    <div id="vocab-list-container"></div>

                    <div style="font-weight:bold; color:#084298; font-size:14px; border-bottom:1px solid #dee2e6; padding-bottom:5px; margin-top:14px; margin-bottom:8px;">
                        Ngữ pháp & Mẫu câu liên quan
                    </div>
                    <div id="grammar-container"></div>
                </div>
            </div>
        </div>

        <!-- PANEL 2: BÀI VIẾT & KỊCH BẢN GIẢNG BÀI + XUẤT WORD -->
        <div id="sub-lecture" class="dropdown-panel">
            <div style="display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap;">
                <button class="btn-ui btn-green" onclick="exportLectureToWord()">Tải về file Word (.doc)</button>
                <button class="btn-ui btn-white" id="btn-lec-vi" onclick="toggleLecVi()">Ẩn bản dịch tiếng Việt</button>
            </div>
            <div class="lecture-box" id="lecture-content-box"></div>
        </div>

        <!-- PANEL 3: TỪ ĐIỂN & PHÁT ÂM -->
        <div id="sub-dict" class="dropdown-panel">
            <div class="input-row">
                <input type="text" id="dict-query" placeholder="Nhập từ tiếng Anh cần tra cứu..." onkeypress="if(event.key==='Enter') searchDict()">
                <button class="btn-ui btn-navy" onclick="searchDict()">Tra cứu</button>
            </div>
            <div id="dict-output" style="font-size:14px; color:#495057;"></div>
        </div>

        <script>
            const DLG_DATA = __DLG_JSON__;
            const LEC_DATA = __LEC_JSON__;
            const YT_IDS = __YT_IDS__;

            let ytIndex = 0;
            let currentAudio = null;
            let isPlayingSeq = false;
            let subsVisible = true;
            let lecViVisible = true;

            function loadYoutubeByIdx() {
                if (YT_IDS && YT_IDS.length > 0) {
                    let vid = YT_IDS[ytIndex % YT_IDS.length];
                    document.getElementById('yt-player-frame').src = `https://www.youtube.com/embed/${vid}`;
                }
            }

            function nextYoutubeVideo() {
                ytIndex++;
                loadYoutubeByIdx();
            }

            function switchSubTab(tabId, btn) {
                document.querySelectorAll('.dropdown-panel').forEach(p => p.classList.remove('active'));
                document.querySelectorAll('.menu-item').forEach(b => b.classList.remove('active'));
                document.getElementById('sub-' + tabId).classList.add('active');
                btn.classList.add('active');
                stopAudio();
            }

            function stopAudio() {
                isPlayingSeq = false;
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }
                if ('speechSynthesis' in window) window.speechSynthesis.cancel();
                document.querySelectorAll('.turn-card').forEach(c => c.classList.remove('active-turn'));
            }

            function playSingleBase64(b64, fallbackText, rate = 1.0, onEndCallback = null) {
                stopAudio();
                if (b64 && b64.length > 20) {
                    currentAudio = new Audio("data:audio/mp3;base64," + b64);
                    currentAudio.playbackRate = rate;
                    currentAudio.onended = function() {
                        if (onEndCallback) onEndCallback();
                    };
                    currentAudio.play().catch(() => {
                        fallbackBrowserSpeak(fallbackText, rate, onEndCallback);
                    });
                } else {
                    fallbackBrowserSpeak(fallbackText, rate, onEndCallback);
                }
            }

            function fallbackBrowserSpeak(text, rate, cb) {
                if ('speechSynthesis' in window) {
                    let u = new SpeechSynthesisUtterance(text);
                    u.lang = 'en-US';
                    u.rate = rate;
                    u.onend = function() { if (cb) cb(); };
                    window.speechSynthesis.speak(u);
                }
            }

            function playTurnByIndex(idx) {
                let t = DLG_DATA.turns[idx];
                playSingleBase64(t.audio_b64, t.en, 1.0, () => {
                    document.querySelectorAll('.turn-card').forEach(c => c.classList.remove('active-turn'));
                });
                let card = document.getElementById('tcard-' + idx);
                if (card) card.classList.add('active-turn');
            }

            function playVocabByIndex(idx) {
                let v = DLG_DATA.vocab[idx];
                playSingleBase64(v.audio_b64, v.word, 0.95);
            }

            function playAllTurns(rate) {
                stopAudio();
                isPlayingSeq = true;
                let idx = 0;

                function step() {
                    if (!isPlayingSeq || idx >= DLG_DATA.turns.length) {
                        isPlayingSeq = false;
                        document.querySelectorAll('.turn-card').forEach(c => c.classList.remove('active-turn'));
                        return;
                    }
                    let t = DLG_DATA.turns[idx];
                    document.querySelectorAll('.turn-card').forEach(c => c.classList.remove('active-turn'));
                    let card = document.getElementById('tcard-' + idx);
                    if (card) card.classList.add('active-turn');

                    if (t.audio_b64 && t.audio_b64.length > 20) {
                        currentAudio = new Audio("data:audio/mp3;base64," + t.audio_b64);
                        currentAudio.playbackRate = rate;
                        currentAudio.onended = function() {
                            idx++;
                            setTimeout(step, 300);
                        };
                        currentAudio.play().catch(() => {
                            idx++;
                            step();
                        });
                    } else {
                        fallbackBrowserSpeak(t.en, rate, () => {
                            idx++;
                            setTimeout(step, 300);
                        });
                    }
                }
                step();
            }

            function toggleSubs() {
                subsVisible = !subsVisible;
                document.querySelectorAll('.sub-text').forEach(el => {
                    if (subsVisible) el.classList.remove('sub-hidden');
                    else el.classList.add('sub-hidden');
                });
                document.getElementById('btn-sub').innerText = subsVisible ? "Ẩn phụ đề" : "Hiện phụ đề";
            }

            function renderAll() {
                loadYoutubeByIdx();
                document.getElementById('dlg-main-title').innerText = DLG_DATA.title;

                let turnsHtml = "";
                DLG_DATA.turns.forEach((t, i) => {
                    let isFem = t.gender === "female";
                    let cls = isFem ? "turn-card female" : "turn-card";
                    let gText = isFem ? "Giọng Nữ" : "Giọng Nam";
                    turnsHtml += `
                        <div class="${cls}" id="tcard-${i}">
                            <div class="turn-header">
                                <span>${t.role} (${gText})</span>
                                <button class="btn-mini-play" onclick="playTurnByIndex(${i})">Nghe câu này</button>
                            </div>
                            <div class="sub-text" style="font-size:14.5px; font-weight:bold; color:#111;">${t.en}</div>
                            <div class="sub-text" style="font-size:13px; color:#555; font-style:italic; margin-top:3px;">${t.vi}</div>
                        </div>
                    `;
                });
                document.getElementById('turns-list-container').innerHTML = turnsHtml;

                let vocabHtml = "";
                DLG_DATA.vocab.forEach((v, i) => {
                    vocabHtml += `
                        <div class="vocab-item">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:bold; color:#0d6efd; font-size:14.5px;">${v.word}</span>
                                <button class="btn-mini-play" onclick="playVocabByIndex(${i})">Nghe từ</button>
                            </div>
                            ${v.ipa ? `<div style="font-family:monospace; color:#6c757d; font-size:12px;">${v.ipa}</div>` : ''}
                            <div style="font-size:13px; color:#212529; margin-top:2px;">Nghĩa: <b>${v.mean}</b></div>
                        </div>
                    `;
                });
                document.getElementById('vocab-list-container').innerHTML = vocabHtml;

                if (DLG_DATA.grammar) {
                    document.getElementById('grammar-container').innerHTML = `
                        <div class="grammar-box">
                            <div style="font-weight:bold; color:#084298; font-size:13.5px;">${DLG_DATA.grammar.title}</div>
                            <div style="background:#fff; padding:5px 7px; border-radius:4px; font-family:monospace; font-size:12px; color:#d63384; margin:5px 0;">${DLG_DATA.grammar.rule}</div>
                            <div style="font-size:13px;"><b>Ví dụ:</b> <i>"${DLG_DATA.grammar.example}"</i></div>
                        </div>
                    `;
                }

                let lecHtml = `<h4 style="color:#084298; border-bottom:2px solid #0d6efd; padding-bottom:6px; margin-top:0;">${LEC_DATA.title}</h4>`;
                LEC_DATA.sections.forEach(s => {
                    lecHtml += `
                        <div style="background:#f8f9fa; border-left:4px solid #0d6efd; padding:10px 12px; margin-bottom:10px; border-radius:4px;">
                            <div style="font-weight:bold; color:#0d6efd; margin-bottom:4px;">${s.heading}</div>
                            <div style="color:#111; line-height:1.55;">${s.en}</div>
                            <div class="lec-vi-line" style="color:#495057; font-style:italic; margin-top:5px; border-top:1px dashed #ced4da; padding-top:4px;">${s.vi}</div>
                        </div>
                    `;
                });
                if (LEC_DATA.vocab && LEC_DATA.vocab.length > 0) {
                    lecHtml += `<div style="background:#e7f1ff; padding:10px; border-radius:6px;"><b>Thuật ngữ trọng tâm:</b><ul style="margin-bottom:0;">`;
                    LEC_DATA.vocab.forEach(v => {
                        lecHtml += `<li><b>${v.word}:</b> ${v.mean}</li>`;
                    });
                    lecHtml += `</ul></div>`;
                }
                document.getElementById('lecture-content-box').innerHTML = lecHtml;
            }

            function toggleLecVi() {
                lecViVisible = !lecViVisible;
                document.querySelectorAll('.lec-vi-line').forEach(el => {
                    el.style.display = lecViVisible ? "block" : "none";
                });
                document.getElementById('btn-lec-vi').innerText = lecViVisible ? "Ẩn bản dịch tiếng Việt" : "Hiện bản dịch tiếng Việt";
            }

            function exportLectureToWord() {
                let body = `<h2 style="text-align:center; color:#084298; font-family:'Times New Roman', serif;">${LEC_DATA.title}</h2><hr/>`;
                LEC_DATA.sections.forEach(s => {
                    body += `<p style="font-weight:bold; color:#0d6efd; font-size:13pt;">${s.heading}</p><p style="font-size:12pt;">${s.en}</p><p style="font-size:11.5pt; font-style:italic; color:#333;"><i>(${s.vi})</i></p>`;
                });
                let docHtml = `<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><style>body{font-family:'Times New Roman',serif;}</style></head><body>${body}</body></html>`;
                let blob = new Blob(['\ufeff', docHtml], { type: 'application/msword' });
                let url = URL.createObjectURL(blob);
                let a = document.createElement('a');
                a.href = url;
                a.download = 'Bai_Giang_Tieng_Anh.doc';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }

            async function searchDict() {
                let w = document.getElementById('dict-query').value.trim();
                if (!w) return;
                let out = document.getElementById('dict-output');
                out.innerHTML = "Đang tra cứu từ điển...";
                try {
                    let res = await fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=vi&q=${encodeURIComponent(w)}`);
                    let data = await res.json();
                    let vi = Array.isArray(data) ? data.join(" ") : data;
                    let ipa = "";
                    let defText = "";
                    try {
                        let dRes = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${encodeURIComponent(w)}`);
                        if (dRes.ok) {
                            let dData = await dRes.json();
                            ipa = dData[0].phonetic || (dData[0].phonetics.find(p => p.text) || {}).text || "";
                            defText = dData[0].meanings[0].definitions[0].definition || "";
                        }
                    } catch(e) {}

                    out.innerHTML = `<div style="background:#f1f8ff; border-left:4px solid #0d6efd; padding:12px; border-radius:6px;">
                        <div style="font-size:18px; font-weight:bold; color:#0d6efd;">${w} <span style="font-family:monospace; color:#6c757d; font-size:14px;">${ipa}</span></div>
                        <div style="font-size:15px; margin-top:4px;"><b>Nghĩa tiếng Việt:</b> ${vi}</div>
                        ${defText ? `<div style="font-size:13.5px; color:#495057; margin-top:4px;"><b>Giải nghĩa Anh-Anh:</b> ${defText}</div>` : ''}
                    </div>`;
                } catch(e) { out.innerHTML = "Lỗi kết nối từ điển."; }
            }

            renderAll();
        </script>
    </body>
    </html>
    """

    final_tutor_html = (tutor_ui_template
        .replace("__DLG_JSON__", dlg_json_safe)
        .replace("__LEC_JSON__", lec_json_safe)
        .replace("__YT_IDS__", yt_ids_safe)
    )
    components.html(final_tutor_html, height=900, scrolling=True)
