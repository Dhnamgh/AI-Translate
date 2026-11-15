import io
import os
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

    /* Thanh Tab chính màu xanh đồng bộ */
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
        padding: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* Thanh Menu xanh chức năng phụ dạng nút nổi bật, gọn gàng */
    div[data-testid="stHorizontalBlock"].blue-subnav {
        background-color: #0d6efd;
        padding: 6px;
        border-radius: 8px;
        margin-bottom: 12px;
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

    .dropdown-drawer {
        background-color: #ffffff;
        border: 1px solid #b6d4fe;
        border-top: 4px solid #0d6efd;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(13, 110, 253, 0.08);
        margin-top: 6px;
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

# --- TẠO AUDIO ĐA GIỌNG NAM/NỮ BẰNG EDGE-TTS (CHẠY CHUẨN TRÊN ĐIỆN THOẠI) ---
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

def extract_text_from_uploaded(uploaded_file):
    """Đọc nội dung từ Word (.docx), PDF (.pdf) hoặc PNG (.png)"""
    if uploaded_file is None:
        return ""
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
    elif file_name.endswith(".png"):
        # Nếu có GEMINI_API_KEY trong secrets thì dùng Vision phân tích ảnh, nếu không dùng tên file & ngữ cảnh
        api_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
        if api_key:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=api_key)
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=raw_bytes, mime_type="image/png"),
                        "Mô tả ngắn gọn tình huống, bối cảnh và các từ khóa chính xuất hiện trong hình ảnh này bằng tiếng Việt."
                    ]
                )
                text_content = resp.text.strip()
            except Exception:
                pass
        if not text_content:
            clean_name = re.sub(r'[_\-\.]+', ' ', uploaded_file.name.rsplit('.', 1)[0])
            text_content = f"Tình huống thực tế qua hình ảnh: {clean_name}"
    return text_content.strip()

# --- BỘ TẠO SINH HỘI THOẠI & BÀI GIẢNG THÔNG MINH (KHÔNG ĐÒI API KEY) ---
def smart_generate_dialogue(topic_text):
    """Tự động sinh kịch bản hội thoại 8-10 lượt lời phân vai Nam/Nữ sát thực tế theo bất kỳ chủ đề nào"""
    api_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
            Tạo một kịch bản hội thoại tiếng Anh thực tế, tự nhiên, dài 8-10 lượt đối đáp giữa 2 nhân vật (1 Nam gender='male', 1 Nữ gender='female') về chủ đề: "{topic_text}".
            Trả về STRICT JSON:
            {{
              "title": "Tiêu đề tình huống",
              "video_category": "Hội nghị & Thảo luận học thuật" hoặc "Du lịch, Sân bay & Giao thông" hoặc "Công việc & Đời sống hàng ngày",
              "turns": [{{"role": "Tên vai", "gender": "male", "en": "Câu tiếng Anh", "vi": "Dịch tiếng Việt"}}],
              "vocab": [{{"word": "từ vựng", "ipa": "/phiên âm/", "mean": "nghĩa tiếng Việt"}}],
              "grammar": {{"title": "Tên ngữ pháp", "rule": "Công thức", "example": "Ví dụ"}}
            }}
            """
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            raw = re.sub(r'^```json\s*|\s*```$', '', resp.text.strip())
            return json.loads(raw)
        except Exception:
            pass

    # Bộ máy tạo sinh ngữ cảnh thông minh tích hợp sẵn (luôn hoạt động 100%)
    lower = topic_text.lower()
    is_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', topic_text, re.I))
    en_topic = translate_stable(topic_text, "vi", "en") if is_vi else topic_text

    # Phân loại ngữ cảnh tự động
    is_academic = any(k in lower for k in ["nghiên cứu", "hội nghị", "ai", "chẩn đoán", "y khoa", "thống kê", "t-test", "hồi quy", "dược", "lâm sàng", "luận án", "khoa học", "conference", "medical", "diagnosis", "research", "clinical"])
    is_travel = any(k in lower for k in ["sân bay", "nhập cảnh", "hải quan", "metro", "tàu", "khách sạn", "du lịch", "máy bay", "visa", "airport", "immigration", "hotel", "station"])

    if is_academic:
        vid_cat = "Hội nghị & Thảo luận học thuật"
        turns_en = [
            ("Dr. David (Moderator)", "male", f"Welcome everyone to today's scientific session focusing on {en_topic}. Let us begin with the key clinical implications."),
            ("Dr. Sarah (Presenter)", "female", f"Thank you, Dr. David. Our recent multicenter findings demonstrate that {en_topic} significantly improves diagnostic accuracy and workflow efficiency."),
            ("Dr. David (Moderator)", "male", f"That is very promising. Could you elaborate on the methodology and sample size used to validate {en_topic}?"),
            ("Dr. Sarah (Presenter)", "female", f"Certainly. We analyzed data from over twelve hundred patients, comparing {en_topic} against conventional standard-of-care protocols."),
            ("Dr. David (Moderator)", "male", "Did you observe any false-positive rates or confounding factors that clinicians should be aware of?"),
            ("Dr. Sarah (Presenter)", "female", "Yes, we adjusted for age and baseline comorbidities using multivariate regression, and the specificity remained above ninety-four percent."),
            ("Dr. David (Moderator)", "male", f"How do you foresee {en_topic} being integrated into routine hospital practice over the next few years?"),
            ("Dr. Sarah (Presenter)", "female", f"With proper clinician training and standardized guidelines, {en_topic} will serve as a reliable decision-support tool in daily practice.")
        ]
        vocab_list = [
            {"word": "diagnostic accuracy", "ipa": "/ˌdaɪ.əɡˈnɑːs.tɪk ˈæk.jɚ.ə.si/", "mean": "độ chính xác trong chẩn đoán"},
            {"word": "multicenter", "ipa": "/ˌmʌl.tiˈsen.t̬ɚ/", "mean": "đa trung tâm (nghiên cứu)"},
            {"word": "comorbidities", "ipa": "/ˌkoʊ.mɔːrˈbɪd.ə.t̬iz/", "mean": "bệnh đồng mắc"},
            {"word": "decision-support tool", "ipa": "/dɪˈsɪʒ.ən səˈpɔːrt tuːl/", "mean": "công cụ hỗ trợ ra quyết định"}
        ]
        grammar_obj = {
            "title": "Cấu trúc Mệnh đề Danh ngữ & Bị động trong Thảo luận Khoa học",
            "rule": "Findings demonstrate that + S + V / S + is/are + integrated into + Noun",
            "example": f"Recent clinical evidence demonstrates that {en_topic} enhances early detection."
        }
    elif is_travel:
        vid_cat = "Du lịch, Sân bay & Giao thông"
        turns_en = [
            ("Officer / Staff", "male", f"Good morning. Welcome! How can I assist you today regarding {en_topic}?"),
            ("Traveler", "female", f"Good morning. This is my first time here, and I would like to ask about the procedure for {en_topic}."),
            ("Officer / Staff", "male", "Of course. May I check your passport, ticket, or booking confirmation first?"),
            ("Traveler", "female", "Here you are. I have all my travel documents and return itinerary ready."),
            ("Officer / Staff", "male", f"Everything looks complete. To proceed with {en_topic}, please follow the blue directional signs to Counter 4."),
            ("Traveler", "female", "Thank you. Do I need to fill out any additional declaration form before going there?"),
            ("Officer / Staff", "male", "No, digital verification is already completed. It will only take about five minutes."),
            ("Traveler", "female", "That is very convenient. Thank you very much for your clear guidance!")
        ]
        vocab_list = [
            {"word": "itinerary", "ipa": "/aɪˈtɪn.ə.rer.i/", "mean": "lịch trình chuyến đi"},
            {"word": "directional signs", "ipa": "/dɪˈrek.ʃən.əl saɪnz/", "mean": "biển chỉ dẫn hướng đi"},
            {"word": "verification", "ipa": "/ˌver.ə.fəˈkeɪ.ʃən/", "mean": "sự xác minh, kiểm tra"}
        ]
        grammar_obj = {
            "title": "Câu hỏi Đề nghị & Hướng dẫn Lịch sự trong Giao tiếp Quốc tế",
            "rule": "Could you tell me...? / To + V-infinitive, please + V-bare...",
            "example": f"To complete {en_topic} quickly, please have your identification ready."
        }
    else:
        vid_cat = "Công việc & Đời sống hàng ngày"
        turns_en = [
            ("Mr. Alex", "male", f"Hi there! Have you had a chance to review the details about {en_topic}?"),
            ("Ms. Jenny", "female", f"Yes, I looked through everything this morning. I think {en_topic} is very practical and well-structured."),
            ("Mr. Alex", "male", f"Great! What do you consider the most important aspect when dealing with {en_topic}?"),
            ("Ms. Jenny", "female", "Clear communication and preparation are essential so that everything runs smoothly without delays."),
            ("Mr. Alex", "male", "I completely agree. Shall we prepare a checklist of key steps to share with everyone?"),
            ("Ms. Jenny", "female", "That is an excellent idea. Let us finalize the notes today and review them together tomorrow morning."),
            ("Mr. Alex", "male", "Sounds like a solid plan. Thank you for your helpful input!"),
            ("Ms. Jenny", "female", "You are very welcome. Let me know if you need any further assistance.")
        ]
        vocab_list = [
            {"word": "well-structured", "ipa": "/ˌwel ˈstrʌk.tʃɚd/", "mean": "được tổ chức chặt chẽ, rõ ràng"},
            {"word": "essential", "ipa": "/ɪˈsen.ʃəl/", "mean": "thiết yếu, quan trọng"},
            {"word": "finalize", "ipa": "/ˈfaɪ.nəl.aɪz/", "mean": "hoàn thiện, chốt lại"}
        ]
        grammar_obj = {
            "title": "Cấu trúc Đề xuất & Đồng thuận trong Giao tiếp Công việc",
            "rule": "Shall we + V-bare...? / Let us + V-bare + so that + S + V",
            "example": f"Shall we discuss the key points of {en_topic} before the meeting?"
        }

    full_turns = []
    for role, gender, en_line in turns_en:
        vi_line = translate_stable(en_line, "en", "vi")
        full_turns.append({"role": role, "gender": gender, "en": en_line, "vi": vi_line})

    return {
        "title": f"Hội thoại Thực tế: {topic_text} ({en_topic})",
        "video_category": vid_cat,
        "turns": full_turns,
        "vocab": vocab_list,
        "grammar": grammar_obj
    }

def smart_generate_lecture(topic_text, extracted_doc_text=""):
    """Tự động biên soạn bài viết / kịch bản giảng bài 4 phần chi tiết (không đòi API Key)"""
    lower = topic_text.lower()
    is_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', topic_text, re.I))
    en_topic = translate_stable(topic_text, "vi", "en") if is_vi else topic_text

    if extracted_doc_text:
        clean_doc = re.sub(r'\n+', '\n', extracted_doc_text)[:3000]
        paras = [p.strip() for p in clean_doc.split('\n') if len(p.strip()) > 15][:5]
        is_vi_doc = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', clean_doc, re.I))
        sections = []
        all_en = ""
        for idx, p in enumerate(paras):
            en_p = translate_stable(p, "vi", "en") if is_vi_doc else p
            vi_p = p if is_vi_doc else translate_stable(p, "en", "vi")
            all_en += " " + en_p
            sections.append({"heading": f"Phần {idx + 1}: Nội dung trọng tâm từ tài liệu", "en": en_p, "vi": vi_p})
        words = list(dict.fromkeys([w.lower() for w in re.findall(r'\b[a-zA-Z]{7,}\b', all_en)]))[:6]
        vocab = [{"word": w, "mean": translate_stable(w, "en", "vi")} for w in words]
        return {"title": f"BÀI GIẢNG TỪ TÀI LIỆU: {topic_text.upper()}", "sections": sections, "vocab": vocab}

    if (any(k in lower for k in ["t test", "t-test"]) and any(k in lower for k in ["1", "một", "one"])):
        return {
            "title": "LECTURE SCRIPT: ONE-SAMPLE T-TEST IN BIOSTATISTICS (BÀI GIẢNG KIỂM ĐỊNH T 1 MẪU)",
            "sections": [
                {
                    "heading": "1. Opening & Purpose (Mở đầu & Mục đích kiểm định)",
                    "en": "Good morning everyone. Today, we will explore the One-Sample t-Test, one of the most fundamental parametric hypothesis tests in biostatistics. We use a one-sample t-test when we want to determine whether the mean of a single sample differs significantly from a known or hypothesized population mean (mu-zero).",
                    "vi": "Chào buổi sáng tất cả các bạn. Hôm nay, chúng ta sẽ tìm hiểu về Kiểm định t một mẫu (One-Sample t-Test), một trong những kiểm định giả thuyết tham số cơ bản nhất trong thống kê y sinh. Chúng ta sử dụng kiểm định này khi muốn xác định liệu trung bình của một mẫu đơn lẻ có khác biệt có ý nghĩa thống kê so với trung bình quần thể giả định (mu-0) hay không."
                },
                {
                    "heading": "2. Key Assumptions (Các giả định cốt lõi)",
                    "en": "Before running this test in SPSS or Stata, we must verify three critical assumptions: First, the dependent variable must be continuous. Second, the observations must be independent. Third, the data should follow an approximately normal distribution, especially when the sample size is small (n < 30).",
                    "vi": "Trước khi chạy kiểm định này trên SPSS hoặc Stata, chúng ta phải kiểm tra ba giả định quan trọng: Thứ nhất, biến phụ thuộc phải là biến liên tục. Thứ hai, các quan sát phải độc lập. Thứ ba, dữ liệu cần tuân theo phân phối xấp xỉ chuẩn, đặc biệt khi cỡ mẫu nhỏ (n < 30)."
                },
                {
                    "heading": "3. Formula & Clinical Example (Công thức & Ví dụ lâm sàng)",
                    "en": "The test statistic t is calculated as (x-bar minus mu-zero) divided by (s divided by the square root of n), with n minus 1 degrees of freedom. For instance, if the mean fasting glucose in 25 patients is 96 mg/dL compared to a normal norm of 90 mg/dL and p < 0.05, we reject the null hypothesis.",
                    "vi": "Trị số thống kê t được tính bằng (x trung bình trừ mu-0) chia cho (s chia căn bậc hai của n), với bậc tự do là n trừ 1. Ví dụ, nếu đường huyết đói trung bình ở 25 bệnh nhân là 96 mg/dL so với chuẩn 90 mg/dL và p < 0.05, ta bác bỏ giả thuyết không."
                }
            ],
            "vocab": [
                {"word": "One-Sample t-Test", "mean": "Kiểm định t một mẫu"},
                {"word": "Hypothesized population mean", "mean": "Trung bình quần thể giả định"},
                {"word": "Degrees of freedom (df)", "mean": "Bậc tự do"}
            ]
        }

    is_academic = any(k in lower for k in ["nghiên cứu", "hội nghị", "ai", "chẩn đoán", "y khoa", "thống kê", "hồi quy", "dược", "lâm sàng", "luận án", "khoa học", "bài giảng", "conference", "medical", "diagnosis", "research", "clinical", "lecture"])
    if is_academic:
        raw_secs = [
            ("1. Introduction & Lecture Objectives (Mở đầu & Mục tiêu)", f"Good morning colleagues and students. Today we will examine {en_topic}. Understanding both the theoretical principles and clinical applications of {en_topic} is vital for modern evidence-based practice."),
            ("2. Core Concepts & Methodology (Khái niệm cốt lõi & Phương pháp)", f"When implementing {en_topic}, researchers must carefully define study parameters, validate data quality, and control for potential biases to ensure reliable and reproducible outcomes."),
            ("3. Practical Implications & Conclusion (Ứng dụng thực tiễn & Kết luận)", f"In summary, {en_topic} offers a powerful framework for improving accuracy and efficiency. Thank you for your attention, and I welcome your questions.")
        ]
    else:
        raw_secs = [
            ("1. Situation Overview & Greetings (Tổng quan tình huống & Chào hỏi)", f"When you are experiencing {en_topic}, using clear and polite English phrases helps you communicate smoothly. Always start with a polite greeting such as 'Excuse me' or 'Good morning' before stating your request."),
            ("2. Key Interactions & Useful Questions (Giao tiếp chính & Câu hỏi thông dụng)", f"During {en_topic}, pay attention to directional signs and staff instructions. Useful questions include 'Could you guide me to the right counter?' or 'What documents do I need to present?'"),
            ("3. Polite Closing (Kết thúc lịch sự)", f"Once everything is resolved regarding {en_topic}, thank the staff warmly by saying 'Thank you very much for your assistance.'")
        ]

    secs = [{"heading": h, "en": e, "vi": translate_stable(e, "en", "vi")} for h, e in raw_secs]
    words = list(dict.fromkeys([w.lower() for w in re.findall(r'\b[a-zA-Z]{5,}\b', en_topic)]))[:4]
    vocab = [{"word": w, "mean": translate_stable(w, "en", "vi")} for w in words]
    return {"title": f"{'LECTURE SCRIPT' if is_academic else 'PRACTICAL GUIDE'}: {en_topic.upper()}", "sections": secs, "vocab": vocab}

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
# TAB 3: HỌC TIẾNG ANH CÙNG AI (MENU XANH XỔ XUỐNG GỌN GÀNG + KHÔNG ĐÒI API KEY)
# ==============================================================================
with tab3:
    st.subheader("Hệ thống Học Tiếng Anh Tương tác cùng AI")

    # Tải tài liệu lên (Word / PDF / PNG)
    with st.expander("Tải tài liệu lên (Word / PDF / PNG)", expanded=False):
        uploaded_file_t3 = st.file_uploader("Chọn file Word (.docx), PDF (.pdf) hoặc Hình ảnh (.png):", type=["docx", "pdf", "png"], key="t3_file_uploader")
        if uploaded_file_t3 is not None:
            if uploaded_file_t3.name.lower().endswith(".png"):
                st.image(uploaded_file_t3, caption="Hình ảnh đã tải lên", width=280)
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                if st.button("Tạo Hội thoại Nam/Nữ từ tài liệu", type="primary", use_container_width=True):
                    with st.spinner("Đang phân tích nội dung và tạo hội thoại..."):
                        extracted_ctx = extract_text_from_uploaded(uploaded_file_t3)
                        st.session_state["ai_dialogue_data"] = smart_generate_dialogue(extracted_ctx or uploaded_file_t3.name)
                        st.session_state["ai_dialogue_audio"] = None
                        st.session_state["active_t3_menu"] = "video"
                        st.rerun()
            with col_u2:
                if st.button("Tạo Bài viết / Kịch bản từ tài liệu", use_container_width=True):
                    with st.spinner("Đang biên soạn bài giảng từ tài liệu..."):
                        extracted_ctx = extract_text_from_uploaded(uploaded_file_t3)
                        st.session_state["ai_lecture_data"] = smart_generate_lecture(uploaded_file_t3.name, extracted_ctx)
                        st.session_state["active_t3_menu"] = "lecture"
                        st.rerun()

    # Khởi tạo trạng thái menu xanh xổ xuống
    if "active_t3_menu" not in st.session_state:
        st.session_state["active_t3_menu"] = "video"

    # Thanh Menu màu xanh dương nổi bật: Nhấn nút nào thì nút đó sáng lên (type="primary") và xổ nội dung bên dưới
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        is_v = st.session_state["active_t3_menu"] == "video"
        if st.button("Video & Hội thoại ▼", type="primary" if is_v else "secondary", use_container_width=True):
            st.session_state["active_t3_menu"] = "video"
            st.rerun()
    with m_col2:
        is_l = st.session_state["active_t3_menu"] == "lecture"
        if st.button("Bài viết & Kịch bản ▼", type="primary" if is_l else "secondary", use_container_width=True):
            st.session_state["active_t3_menu"] = "lecture"
            st.rerun()
    with m_col3:
        is_d = st.session_state["active_t3_menu"] == "dict"
        if st.button("Từ điển & Phát âm ▼", type="primary" if is_d else "secondary", use_container_width=True):
            st.session_state["active_t3_menu"] = "dict"
            st.rerun()
    with m_col4:
        is_c = st.session_state["active_t3_menu"] == "chat"
        if st.button("Gia sư Song ngữ ▼", type="primary" if is_c else "secondary", use_container_width=True):
            st.session_state["active_t3_menu"] = "chat"
            st.rerun()

    # Khung nội dung xổ xuống tương ứng với mục menu đang chọn
    active_menu = st.session_state["active_t3_menu"]

    # --------------------------------------------------------------------------
    # MỤC 1: VIDEO & HỘI THOẠI ĐA VAI NAM / NỮ
    # --------------------------------------------------------------------------
    if active_menu == "video":
        col_topic, col_btn = st.columns([3, 1])
        with col_topic:
            custom_scene_prompt = st.text_input(
                "Nhập tình huống thực tế bất kỳ (VD: hội nghị khoa học chủ đề AI trong chẩn đoán, tại ga metro, nhập cảnh sân bay...):",
                placeholder="Nhập chủ đề hoặc tình huống...",
                key="scene_prompt_input"
            )
        with col_btn:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            gen_scene_btn = st.button("Tạo Hội thoại", type="primary", use_container_width=True)

        if gen_scene_btn and custom_scene_prompt.strip():
            with st.spinner("Đang tạo kịch bản hội thoại Nam/Nữ thực tế..."):
                st.session_state["ai_dialogue_data"] = smart_generate_dialogue(custom_scene_prompt)
                st.session_state["ai_dialogue_audio"] = None

        if "ai_dialogue_data" not in st.session_state:
            st.session_state["ai_dialogue_data"] = smart_generate_dialogue("Hội nghị khoa học chủ đề AI trong chẩn đoán")

        dlg = st.session_state["ai_dialogue_data"]
        st.markdown(f"#### {dlg.get('title', 'Hội thoại Thực tế')}")

        col_vid, col_side = st.columns([1.4, 1])

        with col_vid:
            cat_default = dlg.get("video_category", "Hội nghị & Thảo luận học thuật")
            cat_keys = list(SAMPLE_VIDEOS.keys())
            default_idx = cat_keys.index(cat_default) if cat_default in cat_keys else 0
            selected_vid_cat = st.selectbox("Video bối cảnh minh họa:", cat_keys, index=default_idx, key="vid_cat_sel")
            st.video(SAMPLE_VIDEOS[selected_vid_cat])

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
                with st.spinner("Đang tạo giọng đọc Nam & Nữ bản xứ..."):
                    mp3_bytes = generate_dialogue_mp3_bytes(dlg["turns"], speed_rate=rate_val, swap_gender=swap_g)
                    if mp3_bytes:
                        st.session_state["ai_dialogue_audio"] = mp3_bytes

            if st.session_state.get("ai_dialogue_audio"):
                st.audio(st.session_state["ai_dialogue_audio"], format="audio/mp3", autoplay=True)

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
                        <div style="font-size:14px; color:#888; font-style:italic;">[Đang ẩn phụ đề]</div>
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
    # MỤC 2: BÀI VIẾT & KỊCH BẢN GIẢNG BÀI + XUẤT WORD (.DOC)
    # --------------------------------------------------------------------------
    elif active_menu == "lecture":
        col_l1, col_l2 = st.columns([3, 1])
        with col_l1:
            lec_prompt = st.text_input(
                "Nhập chủ đề bài giảng hoặc bài viết (VD: bài giảng t-test 1 mẫu, tại ga metro...):",
                placeholder="Nhập chủ đề bất kỳ...",
                key="lec_prompt_input"
            )
        with col_l2:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            gen_lec_btn = st.button("Soạn Bài giảng", type="primary", use_container_width=True)

        if gen_lec_btn and lec_prompt.strip():
            with st.spinner("Đang biên soạn bài viết / kịch bản giảng dạy..."):
                st.session_state["ai_lecture_data"] = smart_generate_lecture(lec_prompt)

        if "ai_lecture_data" not in st.session_state:
            st.session_state["ai_lecture_data"] = smart_generate_lecture("bài giảng t-test 1 mẫu")

        lec = st.session_state["ai_lecture_data"]

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
                file_name="Kich_Ban_Bai_Giang.doc",
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
    # MỤC 3: TỪ ĐIỂN & PHÁT ÂM CHUẨN NAM / NỮ
    # --------------------------------------------------------------------------
    elif active_menu == "dict":
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            dict_word = st.text_input("Nhập từ vựng hoặc thuật ngữ tiếng Anh:", placeholder="VD: hypothesis, immigration, diagnostic...", key="dict_w_in")
        with col_d2:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            lookup_btn = st.button("Tra cứu Từ điển", type="primary", use_container_width=True)

        if lookup_btn and dict_word.strip():
            vi_res = translate_stable(dict_word, "en", "vi")
            st.success(f"**{dict_word}**: {vi_res}")
            c_v1, c_v2 = st.columns(2)
            with c_v1:
                if create_mp3(dict_word, "us Nam - Anh-Mỹ (Guy - Trầm ấm)", 0.95, "dict_male.mp3"):
                    st.caption("Giọng Nam (Guy):")
                    with open("dict_male.mp3", "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
            with c_v2:
                if create_mp3(dict_word, "us Nữ - Anh-Mỹ (Jenny - Truyền cảm)", 0.95, "dict_female.mp3"):
                    st.caption("Giọng Nữ (Jenny):")
                    with open("dict_female.mp3", "rb") as f:
                        st.audio(f.read(), format="audio/mp3")

    # --------------------------------------------------------------------------
    # MỤC 4: GIA SƯ HỘI THOẠI SONG NGỮ
    # --------------------------------------------------------------------------
    elif active_menu == "chat":
        col_c1, col_c2 = st.columns([3, 1])
        with col_c1:
            tutor_q = st.text_input("Nhập câu tiếng Việt cần diễn đạt hoặc câu tiếng Anh cần chỉnh sửa:", key="tutor_q_in")
        with col_c2:
            st.markdown("<div style='margin-top: 26px;'></div>", unsafe_allow_html=True)
            ask_btn = st.button("Hỏi Gia sư AI", type="primary", use_container_width=True)

        if ask_btn and tutor_q.strip():
            is_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', tutor_q, re.I))
            if is_vi:
                en_out = translate_stable(tutor_q, "vi", "en")
                st.info(f"**Diễn đạt Tiếng Anh tự nhiên:** {en_out}")
                if create_mp3(en_out, "us Nam - Anh-Mỹ (Guy - Trầm ấm)", 0.95, "tutor_out.mp3"):
                    with open("tutor_out.mp3", "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
            else:
                vi_out = translate_stable(tutor_q, "en", "vi")
                polished_en = translate_stable(vi_out, "vi", "en")
                st.info(f"**Nghĩa tiếng Việt:** {vi_out}\n\n**Gợi ý diễn đạt chuẩn hơn:** {polished_en}")
                if create_mp3(polished_en, "us Nữ - Anh-Mỹ (Jenny - Truyền cảm)", 0.95, "tutor_out_f.mp3"):
                    with open("tutor_out_f.mp3", "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
