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

# --- TẠO AUDIO BASE64 EDGE-TTS CHO TỪNG CÂU & TỪ VỰNG ---
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

def analyze_uploaded_file(uploaded_file):
    """Phân tích file Word, PDF hoặc Hình ảnh PNG trả về (ngữ cảnh, là_ảnh_hay_không)"""
    if uploaded_file is None:
        return "", False
    file_name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()

    if file_name.endswith(".docx"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(raw_bytes))
            txt = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return txt.strip(), False
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
                return "\n".join(paragraphs).strip(), False
    elif file_name.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages).strip(), False
        except Exception:
            return "", False
    elif file_name.endswith(".png"):
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
                        "Đọc toàn bộ chữ, bảng biểu hoặc mô tả chính xác bối cảnh chuyên môn/đời sống trong hình ảnh này bằng tiếng Việt."
                    ]
                )
                if resp.text and resp.text.strip():
                    return resp.text.strip(), True
            except Exception:
                pass
        # Phân tích thông minh từ tên file ảnh nếu chưa có Vision key
        base_name = uploaded_file.name.rsplit('.', 1)[0]
        clean_name = re.sub(r'[_\-\.]+', ' ', base_name)
        return f"Phân tích dữ liệu và tình huống thực tế từ hình ảnh {clean_name}", True
    return "", False

def build_dialogue_payload(topic_text):
    lower = topic_text.lower()
    is_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', topic_text, re.I))
    en_topic = translate_stable(topic_text, "vi", "en") if is_vi else topic_text

    # 1. Kiểm định phân phối chuẩn (Normality Test / SPSS Histogram)
    if any(k in lower for k in ["normality", "shapiro", "kolmogorov", "phân phối chuẩn", "lệch phải", "skewness", "bpv"]):
        scene_type = "academic"
        turns_raw = [
            ("Dr. Nam (Biostatistician)", "male", "Looking at the SPSS output and histogram, how do we evaluate whether this continuous variable follows a normal distribution?", "Nhìn vào bảng kết quả SPSS và biểu đồ histogram, làm thế nào để chúng ta đánh giá xem biến liên tục này có tuân theo phân phối chuẩn hay không?"),
            ("Dr. Linh (Researcher)", "female", "We examine both the statistical tests of normality—Kolmogorov-Smirnov and Shapiro-Wilk—along with the visual shape of the histogram and skewness value.", "Chúng ta kiểm tra cả hai kiểm định phân phối chuẩn—Kolmogorov-Smirnov và Shapiro-Wilk—cùng với hình dạng trực quan của biểu đồ histogram và hệ số bất đối xứng skewness."),
            ("Dr. Nam (Biostatistician)", "male", "Here, both Kolmogorov-Smirnov and Shapiro-Wilk show p-values less than 0.001, and the histogram displays a clear right-skewed tail.", "Ở đây, cả hai kiểm định Kolmogorov-Smirnov và Shapiro-Wilk đều có trị số p nhỏ hơn 0.001, và biểu đồ histogram cho thấy đuôi lệch phải rất rõ."),
            ("Dr. Linh (Researcher)", "female", "Exactly. Since p is less than 0.05, we reject the assumption of normality. Therefore, we should report the median and interquartile range instead of the mean and standard deviation.", "Chính xác. Vì p nhỏ hơn 0.05, chúng ta bác bỏ giả định phân phối chuẩn. Do đó, chúng ta nên báo cáo trung vị và khoảng tứ phân vị thay vì trung bình và độ lệch chuẩn."),
            ("Dr. Nam (Biostatistician)", "male", "And which hypothesis test should we use when comparing this skewed variable between two independent groups?", "Và chúng ta nên sử dụng kiểm định giả thuyết nào khi so sánh biến lệch chuẩn này giữa hai nhóm độc lập?"),
            ("Dr. Linh (Researcher)", "female", "We should apply the non-parametric Mann-Whitney U test rather than the independent-samples t-test.", "Chúng ta nên áp dụng kiểm định phi tham số Mann-Whitney U thay vì kiểm định t hai mẫu độc lập.")
        ]
        vocab_list = [
            {"word": "normal distribution", "ipa": "/ˈnɔːr.məl ˌdɪs.trɪˈbjuː.ʃən/", "mean": "phân phối chuẩn"},
            {"word": "right-skewed", "ipa": "/raɪt skjuːd/", "mean": "lệch phải (phân phối)"},
            {"word": "interquartile range", "ipa": "/ˌɪn.t̬ɚˈkwɔːr.taɪl reɪndʒ/", "mean": "khoảng tứ phân vị (IQR)"},
            {"word": "non-parametric test", "ipa": "/ˌnɑːn.per.əˈmet.rɪk test/", "mean": "kiểm định phi tham số"}
        ]
        grammar_obj = {
            "title": "Mệnh đề Chỉ Nguyên nhân & Hệ quả trong Diễn giải Thống kê",
            "rule": "Since + S + V (p < 0.05), we reject... Therefore, we should + V-bare...",
            "example": "Since the data are right-skewed, we should report the median and interquartile range."
        }
    # 2. Hồi quy Logistic
    elif "logistic" in lower or "hồi quy" in lower:
        scene_type = "academic"
        turns_raw = [
            ("Dr. Nam (Biostatistician)", "male", "For your clinical study on treatment outcomes, why did you choose multivariate logistic regression instead of linear regression?", "Đối với nghiên cứu lâm sàng về kết cục điều trị của bạn, tại sao bạn chọn hồi quy logistic đa biến thay vì hồi quy tuyến tính?"),
            ("Dr. Linh (Clinical Researcher)", "female", "Because our primary dependent variable is dichotomous: complete remission versus persistent symptoms. Linear regression is only appropriate for continuous outcomes.", "Bởi vì biến phụ thuộc chính của chúng tôi là biến nhị giá: lui bệnh hoàn toàn so với còn triệu chứng. Hồi quy tuyến tính chỉ phù hợp cho biến kết cục liên tục."),
            ("Dr. Nam (Biostatistician)", "male", "How did you select the independent variables to include in the multivariate model?", "Bạn đã lựa chọn các biến độc lập để đưa vào mô hình đa biến như thế nào?"),
            ("Dr. Linh (Clinical Researcher)", "female", "We first performed univariate screening, and variables with p below 0.20 along with clinical confounders like age were entered into the model.", "Trước tiên chúng tôi sàng lọc đơn biến, và các biến có p dưới 0.20 cùng các yếu tố gây nhiễu lâm sàng như tuổi được đưa vào mô hình."),
            ("Dr. Nam (Biostatistician)", "male", "How do you interpret the Adjusted Odds Ratio for your primary predictor in the final output?", "Bạn diễn giải Tỷ số chênh hiệu chỉnh (aOR) cho yếu tố tiên lượng chính như thế nào?"),
            ("Dr. Linh (Clinical Researcher)", "female", "The adjusted odds ratio is 2.45 with a 95% confidence interval from 1.32 to 4.54, meaning patients with this factor had 2.45 times higher odds of remission.", "Tỷ số chênh hiệu chỉnh là 2.45 với khoảng tin cậy 95% từ 1.32 đến 4.54, nghĩa là bệnh nhân có yếu tố này có chênh đạt lui bệnh cao gấp 2.45 lần.")
        ]
        vocab_list = [
            {"word": "logistic regression", "ipa": "/ləˈdʒɪs.tɪk rɪˈɡreʃ.ən/", "mean": "hồi quy logistic"},
            {"word": "dichotomous", "ipa": "/daɪˈkɑː.t̬ə.məs/", "mean": "nhị giá (2 giá trị)"},
            {"word": "adjusted odds ratio", "ipa": "/əˈdʒʌs.tɪd ɑːdz ˈreɪ.ʃoʊ/", "mean": "tỷ số chênh hiệu chỉnh (aOR)"},
            {"word": "confounding variable", "ipa": "/kənˈfaʊn.dɪŋ ˈver.i.ə.bəl/", "mean": "biến gây nhiễu"}
        ]
        grammar_obj = {
            "title": "Mệnh đề Phân từ Hiện tại (V-ing) diễn giải kết quả thống kê",
            "rule": "The aOR is [Value], meaning + S + V (had X times higher odds of + V-ing)",
            "example": "The adjusted odds ratio is 2.45, meaning treated patients had higher odds of recovery."
        }
    # 3. Kiểm định t-test 1 mẫu
    elif (any(k in lower for k in ["t test", "t-test"]) and any(k in lower for k in ["1", "một", "one"])):
        scene_type = "academic"
        turns_raw = [
            ("Professor", "male", "Today let us review when to apply a One-Sample t-Test in clinical research.", "Hôm nay chúng ta hãy ôn lại khi nào áp dụng Kiểm định t một mẫu trong nghiên cứu lâm sàng."),
            ("Student", "female", "We use it to compare the mean of a single sample against a known or hypothesized population mean.", "Chúng ta dùng kiểm định này để so sánh trung bình của một mẫu đơn lẻ với trung bình quần thể giả định ạ."),
            ("Professor", "male", "Correct. What assumptions must be satisfied before running the one-sample t-test?", "Chính xác. Những giả định nào cần được thỏa mãn trước khi chạy kiểm định t một mẫu?"),
            ("Student", "female", "The dependent variable must be continuous, observations independent, and data approximately normally distributed.", "Biến phụ thuộc phải là biến liên tục, các quan sát độc lập, và dữ liệu phân phối xấp xỉ chuẩn."),
            ("Professor", "male", "And how do we decide whether to reject the null hypothesis?", "Và làm thế nào để chúng ta quyết định có bác bỏ giả thuyết không hay không?"),
            ("Student", "female", "If the two-tailed p-value is less than 0.05, we reject H0 and conclude a statistically significant difference.", "Nếu trị số p hai phía nhỏ hơn 0.05, chúng ta bác bỏ H0 và kết luận có sự khác biệt có ý nghĩa thống kê.")
        ]
        vocab_list = [
            {"word": "one-sample t-test", "ipa": "/wʌn ˈsæm.pəl tiː test/", "mean": "kiểm định t một mẫu"},
            {"word": "null hypothesis", "ipa": "/nʌl haɪˈpɑː.θə.sɪs/", "mean": "giả thuyết không (H0)"},
            {"word": "normal distribution", "ipa": "/ˈnɔːr.məl ˌdɪs.trɪˈbjuː.ʃən/", "mean": "phân phối chuẩn"}
        ]
        grammar_obj = {
            "title": "Câu điều kiện loại 0/1 trong Quy tắc Thống kê",
            "rule": "If + S + V (Present Simple), S + V (Present Simple / Will)",
            "example": "If the p-value is less than 0.05, we reject the null hypothesis."
        }
    # 4. Quán Cà phê / Starbucks
    elif any(k in lower for k in ["starbucks", "coffee", "cà phê", "quán", "đồ uống", "cafe"]):
        scene_type = "cafe"
        turns_raw = [
            ("Barista", "male", "Good morning! Welcome to Starbucks. What can I get started for you today?", "Chào buổi sáng! Chào mừng đến Starbucks. Hôm nay bạn muốn gọi đồ uống gì ạ?"),
            ("Customer", "female", "Hi! Could I get a Grande Iced Caramel Macchiato with oat milk, please?", "Chào bạn! Cho mình một ly Caramel Macchiato đá cỡ vừa pha với sữa yến mạch nhé?"),
            ("Barista", "male", "Sure thing. Would you like any whipped cream or extra espresso shot on that?", "Chắc chắn rồi. Bạn có muốn thêm kem tươi hay thêm một shot cà phê espresso không?"),
            ("Customer", "female", "No whipped cream, please. Also, do you have any holiday pastries today?", "Không kem tươi nhé. Ngoài ra hôm nay quán có bánh ngọt theo mùa lễ hội không?"),
            ("Barista", "male", "Yes, we have freshly baked cinnamon rolls and cranberry bliss bars right here.", "Có ạ, chúng tôi có bánh cuộn quế mới nướng và bánh nam việt quất ngay tại quầy này."),
            ("Customer", "female", "I will take one cinnamon roll warmed up, please. Can I pay by card?", "Cho mình lấy một bánh cuộn quế hâm nóng nhé. Mình thanh toán bằng thẻ được không?")
        ]
        vocab_list = [
            {"word": "oat milk", "ipa": "/oʊt mɪlk/", "mean": "sữa yến mạch"},
            {"word": "cinnamon roll", "ipa": "/ˈsɪn.ə.mən roʊl/", "mean": "bánh cuộn quế"},
            {"word": "pickup counter", "ipa": "/ˈpɪk.ʌp ˈkaʊn.t̬ɚ/", "mean": "quầy nhận đồ"}
        ]
        grammar_obj = {
            "title": "Câu gọi món lịch sự với 'Could I get...' & 'I will take...'",
            "rule": "Could I get + [Size] + [Drink] + with + [Option], please?",
            "example": "Could I get a medium iced latte with less ice, please?"
        }
    # 5. Ga Metro / Sân bay
    elif any(k in lower for k in ["metro", "tàu", "nhà ga", "sân bay", "nhập cảnh", "hải quan", "immigration", "airport", "station"]):
        scene_type = "transit"
        turns_raw = [
            ("Officer / Staff", "male", f"Good morning. How can I assist you today regarding {en_topic}?", f"Chào buổi sáng. Tôi có thể hỗ trợ gì cho bạn hôm nay về {topic_text}?"),
            ("Passenger", "female", "Good morning. Could you tell me which platform or counter I should go to, and what documents are required?", "Chào buổi sáng. Bạn có thể cho tôi biết tôi nên đến sân ga hoặc quầy nào, và cần những giấy tờ gì không?"),
            ("Officer / Staff", "male", "Please have your passport, ticket, or smart card ready. Follow the blue directional signs straight ahead to Gate 2.", "Vui lòng chuẩn bị sẵn hộ chiếu, vé hoặc thẻ thông minh. Hãy đi theo biển chỉ dẫn màu xanh thẳng phía trước đến Cổng số 2."),
            ("Passenger", "female", "Thank you. How long does the procedure take, and where is the transfer desk?", "Cảm ơn bạn. Thủ tục mất khoảng bao lâu, và quầy chuyển tiếp nằm ở đâu ạ?"),
            ("Officer / Staff", "male", "It takes only five minutes. The transfer desk is right next to the main escalator on your left.", "Chỉ mất 5 phút thôi. Quầy chuyển tiếp nằm ngay cạnh thang cuốn chính bên tay trái của bạn."),
            ("Passenger", "female", "That is very clear. Thank you very much for your help!", "Rất rõ ràng rồi ạ. Cảm ơn sự giúp đỡ của bạn rất nhiều!")
        ]
        vocab_list = [
            {"word": "directional sign", "ipa": "/dɪˈrek.ʃən.əl saɪn/", "mean": "biển chỉ dẫn hướng đi"},
            {"word": "escalator", "ipa": "/ˈes.kə.leɪ.t̬ɚ/", "mean": "thang cuốn"},
            {"word": "transfer desk", "ipa": "/ˈtræns.fɝː desk/", "mean": "quầy chuyển tiếp / nối chuyến"}
        ]
        grammar_obj = {
            "title": "Câu hỏi Gián tiếp Lịch sự (Embedded Questions)",
            "rule": "Could you tell me + Wh-word + S + V?",
            "example": "Could you tell me where the ticket vending machine is?"
        }
    else:
        is_acad = any(k in lower for k in ["nghiên cứu", "hội nghị", "ai", "chẩn đoán", "y khoa", "dược", "lâm sàng", "luận án", "khoa học", "conference", "medical", "diagnosis", "research"])
        scene_type = "academic" if is_acad else "general"
        turns_raw = [
            ("Mr. David", "male", f"Good morning. Let us discuss the key aspects of {en_topic} in detail today.", f"Chào buổi sáng. Hôm nay chúng ta hãy cùng thảo luận chi tiết về các khía cạnh chính của {topic_text}."),
            ("Ms. Jenny", "female", f"I would be glad to. Recently, {en_topic} has attracted significant attention due to its practical impact.", f"Tôi rất sẵn lòng. Gần đây, {topic_text} đã thu hút nhiều sự chú ý nhờ tác động thực tiễn của nó."),
            ("Mr. David", "male", f"What do you consider the most critical factor when implementing {en_topic}?", f"Theo bạn, yếu tố nào là quan trọng nhất khi triển khai {topic_text}?"),
            ("Ms. Jenny", "female", "Careful planning, standardized procedures, and clear communication are essential for achieving optimal outcomes.", "Lập kế hoạch cẩn thận, quy trình chuẩn hóa và giao tiếp rõ ràng là những yếu tố thiết yếu để đạt kết quả tối ưu."),
            ("Mr. David", "male", "Are there any common challenges or pitfalls we should anticipate in advance?", "Có thách thức hay trở ngại phổ biến nào mà chúng ta nên lường trước không?"),
            ("Ms. Jenny", "female", "Yes, initial resource allocation and training require attention, but systematic monitoring resolves most issues early.", "Có, việc phân bổ nguồn lực và đào tạo ban đầu cần được chú trọng, nhưng giám sát có hệ thống sẽ giải quyết sớm hầu hết vấn đề."),
            ("Mr. David", "male", f"Thank you for those insights. Let us summarize our action plan for {en_topic}.", f"Cảm ơn những chia sẻ sâu sắc đó. Hãy cùng tổng kết kế hoạch hành động cho {topic_text}."),
            ("Ms. Jenny", "female", "Agreed. I will circulate the summary notes to everyone right after our session.", "Đồng ý. Tôi sẽ gửi bản ghi chú tổng kết cho mọi người ngay sau buổi thảo luận này.")
        ]
        words = list(dict.fromkeys([w.lower() for w in re.findall(r'\b[a-zA-Z]{5,}\b', en_topic)]))[:3]
        vocab_list = [{"word": w, "ipa": "", "mean": translate_stable(w, "en", "vi")} for w in words]
        vocab_list.append({"word": "systematic monitoring", "ipa": "/ˌsɪs.təˈmæt.ɪk ˈmɑː.nə.t̬ɚ.ɪŋ/", "mean": "giám sát có hệ thống"})
        vocab_list.append({"word": "optimal outcomes", "ipa": "/ˈɑːp.tə.məl ˈaʊt.kʌmz/", "mean": "kết quả tối ưu"})
        grammar_obj = {
            "title": "Cấu trúc Nhấn mạnh Vai trò & Điều kiện Thiết yếu",
            "rule": "Noun Phrase + are essential for + V-ing / Noun",
            "example": f"Standardized protocols are essential for ensuring the quality of {en_topic}."
        }

    turns_list = [{"role": r, "gender": g, "en": e, "vi": v} for r, g, e, v in turns_raw]
    return {
        "title": f"Hội thoại Thực tế: {topic_text}",
        "scene_type": scene_type,
        "turns": turns_list,
        "vocab": vocab_list,
        "grammar": grammar_obj
    }

def build_lecture_payload(topic_text, extracted_doc_text="", is_image_source=False):
    """Tạo kịch bản bài giảng chi tiết 3-4 phần (Đảm bảo KHÔNG BAO GIỜ RỖNG kể cả khi tải ảnh PNG lên)"""
    combined_context = f"{topic_text} {extracted_doc_text}".lower()
    is_vi = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', topic_text, re.I))
    en_topic = translate_stable(topic_text, "vi", "en") if is_vi else topic_text

    # Nếu là tài liệu văn bản dài (Word / PDF) có nhiều đoạn rõ ràng
    if extracted_doc_text and not is_image_source:
        clean_doc = re.sub(r'\n+', '\n', extracted_doc_text)[:3000]
        paras = [p.strip() for p in clean_doc.split('\n') if len(p.strip()) > 10][:5]
        if len(paras) >= 2:
            is_vi_doc = bool(re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', clean_doc, re.I))
            sections = []
            all_en = ""
            for idx, p in enumerate(paras):
                en_p = translate_stable(p, "vi", "en") if is_vi_doc else p
                vi_p = p if is_vi_doc else translate_stable(p, "en", "vi")
                all_en += " " + en_p
                sections.append({"heading": f"Phần {idx + 1}: Nội dung trọng tâm từ tài liệu", "en": en_p, "vi": vi_p})
            words = list(dict.fromkeys([w.lower() for w in re.findall(r'\b[a-zA-Z]{6,}\b', all_en)]))[:6]
            vocab = [{"word": w, "mean": translate_stable(w, "en", "vi")} for w in words]
            return {"title": f"BÀI GIẢNG TỪ TÀI LIỆU: {topic_text.upper()}", "sections": sections, "vocab": vocab}

    # Nhận diện chuyên đề từ ảnh PNG hoặc từ khóa nhập vào
    if any(k in combined_context for k in ["normality", "shapiro", "kolmogorov", "phân phối chuẩn", "lệch phải", "skewness", "bpv"]):
        return {
            "title": "LECTURE SCRIPT: TESTS OF NORMALITY & SKEWED DATA IN SPSS (KIỂM ĐỊNH PHÂN PHỐI CHUẨN)",
            "sections": [
                {
                    "heading": "1. Visual Inspection: Histogram & Skewness (Đánh giá trực quan qua Biểu đồ & Độ lệch)",
                    "en": "When examining continuous variables in biostatistics, we first inspect the histogram and descriptive statistics. As seen in the output, a long tail extending to the right indicates a positively skewed (right-skewed) distribution rather than a symmetric bell-shaped normal curve.",
                    "vi": "Khi kiểm tra các biến liên tục trong thống kê y sinh, trước tiên chúng ta quan sát biểu đồ histogram và các chỉ số mô tả. Như thấy trong kết quả, phần đuôi kéo dài về bên phải cho thấy phân phối lệch dương (lệch phải) thay vì đường cong hình chuông đối xứng chuẩn."
                },
                {
                    "heading": "2. Formal Statistical Tests: Kolmogorov-Smirnov & Shapiro-Wilk (Kiểm định thống kê)",
                    "en": "Next, we examine the Tests of Normality table. Both the Kolmogorov-Smirnov test and the Shapiro-Wilk test yield a significance level (Sig. or p-value) of less than 0.001. Because p < 0.05, we reject the null hypothesis of normality and conclude that the data are not normally distributed.",
                    "vi": "Tiếp theo, chúng ta xem xét bảng Kiểm định phân phối chuẩn (Tests of Normality). Cả kiểm định Kolmogorov-Smirnov và Shapiro-Wilk đều cho mức ý nghĩa (Sig. hoặc trị số p) nhỏ hơn 0.001. Vì p < 0.05, chúng ta bác bỏ giả thuyết không về tính chuẩn và kết luận dữ liệu không tuân theo phân phối chuẩn."
                },
                {
                    "heading": "3. Practical Recommendation for Reporting & Testing (Khuyến nghị trình bày & chọn kiểm định)",
                    "en": "Because the distribution is non-normal, researchers must summarize the variable using the median and interquartile range (25th and 75th percentiles) instead of the mean and standard deviation, and use non-parametric tests such as the Mann-Whitney U test.",
                    "vi": "Do phân phối không chuẩn, nhà nghiên cứu phải tóm tắt biến bằng trung vị và khoảng tứ phân vị (bách phân vị thứ 25 và 75) thay vì trung bình và độ lệch chuẩn, đồng thời sử dụng các kiểm định phi tham số như kiểm định Mann-Whitney U."
                }
            ],
            "vocab": [
                {"word": "Tests of Normality", "mean": "Kiểm định phân phối chuẩn"},
                {"word": "Right-skewed distribution", "mean": "Phân phối lệch phải"},
                {"word": "Percentiles (25th, 75th)", "mean": "Các điểm bách phân vị (tứ phân vị)"},
                {"word": "Non-parametric test", "mean": "Kiểm định phi tham số"}
            ]
        }

    if "logistic" in combined_context or "hồi quy" in combined_context:
        return {
            "title": "LECTURE SCRIPT: MULTIVARIATE LOGISTIC REGRESSION (BÀI GIẢNG HỒI QUY LOGISTIC ĐA BIẾN)",
            "sections": [
                {
                    "heading": "1. Opening & Purpose (Mở đầu & Mục đích mô hình)",
                    "en": "Good morning everyone. Today we will examine Multivariate Logistic Regression, one of the most widely used statistical methods in clinical research. Binary logistic regression is applied when the dependent variable is dichotomous—having only two categories such as cured versus not cured.",
                    "vi": "Chào buổi sáng tất cả các bạn. Hôm nay chúng ta sẽ tìm hiểu về Hồi quy Logistic Đa biến, một trong những phương pháp thống kê được sử dụng rộng rãi nhất trong nghiên cứu lâm sàng. Hồi quy logistic nhị phân được áp dụng khi biến phụ thuộc là biến nhị giá—chỉ có hai phân loại như khỏi bệnh so với không khỏi bệnh."
                },
                {
                    "heading": "2. Controlling Confounders & Adjusted Odds Ratio (Hiệu chỉnh nhiễu & Tỷ số chênh aOR)",
                    "en": "The major strength of multivariate logistic regression is its ability to adjust for multiple confounding variables simultaneously. We report the Adjusted Odds Ratio (aOR) with its 95% confidence interval. An aOR > 1 indicates a risk factor, whereas an aOR < 1 indicates a protective factor.",
                    "vi": "Điểm mạnh cốt lõi của hồi quy logistic đa biến là khả năng hiệu chỉnh đồng thời cho nhiều biến gây nhiễu. Chúng ta báo cáo Tỷ số chênh hiệu chỉnh (aOR) kèm khoảng tin cậy 95%. Giá trị aOR > 1 cho thấy yếu tố nguy cơ, trong khi aOR < 1 cho thấy yếu tố bảo vệ."
                },
                {
                    "heading": "3. Model Diagnostics (Đánh giá độ phù hợp mô hình)",
                    "en": "Finally, we evaluate model calibration using the Hosmer-Lemeshow goodness-of-fit test (where p > 0.05 indicates good fit) and assess discrimination using the Area Under the ROC Curve (AUC).",
                    "vi": "Cuối cùng, chúng ta đánh giá độ định chuẩn của mô hình bằng kiểm định độ phù hợp Hosmer-Lemeshow (trong đó p > 0.05 cho thấy mô hình phù hợp tốt) và đánh giá khả năng phân biệt bằng Diện tích dưới đường cong ROC (AUC)."
                }
            ],
            "vocab": [
                {"word": "Multivariate logistic regression", "mean": "Hồi quy logistic đa biến"},
                {"word": "Dichotomous variable", "mean": "Biến nhị giá"},
                {"word": "Adjusted Odds Ratio (aOR)", "mean": "Tỷ số chênh hiệu chỉnh"},
                {"word": "Goodness-of-fit", "mean": "Độ phù hợp của mô hình"}
            ]
        }

    if (any(k in combined_context for k in ["t test", "t-test"]) and any(k in combined_context for k in ["1", "một", "one"])):
        return {
            "title": "LECTURE SCRIPT: ONE-SAMPLE T-TEST IN BIOSTATISTICS (BÀI GIẢNG KIỂM ĐỊNH T 1 MẪU)",
            "sections": [
                {
                    "heading": "1. Opening & Purpose (Mở đầu & Mục đích kiểm định)",
                    "en": "Good morning everyone. Today, we will explore the One-Sample t-Test, used to determine whether the mean of a single sample differs significantly from a known or hypothesized population mean (mu-zero).",
                    "vi": "Chào buổi sáng tất cả các bạn. Hôm nay, chúng ta sẽ tìm hiểu về Kiểm định t một mẫu, dùng để xác định liệu trung bình của một mẫu đơn lẻ có khác biệt có ý nghĩa thống kê so với trung bình quần thể giả định (mu-0) hay không."
                },
                {
                    "heading": "2. Key Assumptions & Formula (Giả định cốt lõi & Công thức)",
                    "en": "Before running this test, verify that the dependent variable is continuous, observations are independent, and data follow an approximately normal distribution. If p < 0.05, we reject the null hypothesis H0.",
                    "vi": "Trước khi chạy kiểm định, hãy kiểm tra biến phụ thuộc là biến liên tục, các quan sát độc lập và dữ liệu phân phối xấp xỉ chuẩn. Nếu p < 0.05, ta bác bỏ giả thuyết không H0."
                }
            ],
            "vocab": [
                {"word": "One-Sample t-Test", "mean": "Kiểm định t một mẫu"},
                {"word": "Null hypothesis (H0)", "mean": "Giả thuyết không"}
            ]
        }

    # Nếu là ảnh chụp bối cảnh bất kỳ hoặc chủ đề tự do
    context_desc_en = translate_stable(extracted_doc_text, "vi", "en") if extracted_doc_text else en_topic
    is_academic = any(k in combined_context for k in ["nghiên cứu", "hội nghị", "ai", "chẩn đoán", "y khoa", "thống kê", "dược", "lâm sàng", "luận án", "khoa học", "bài giảng", "spss", "stata", "biểu đồ"])
    if is_academic:
        raw_secs = [
            ("1. Introduction & Context Analysis (Mở đầu & Phân tích bối cảnh)", f"Good morning colleagues and students. Today we will examine {context_desc_en}. Understanding both the theoretical principles and practical interpretation of these findings is essential for evidence-based research."),
            ("2. Core Methodology & Interpretation (Phương pháp cốt lõi & Diễn giải)", f"When evaluating {context_desc_en}, researchers must carefully verify statistical assumptions, examine key parameters, and avoid misinterpreting p-values or sample distributions."),
            ("3. Practical Implications & Conclusion (Ứng dụng thực tiễn & Kết luận)", f"In summary, systematic analysis of {context_desc_en} ensures accurate and reproducible scientific conclusions. Thank you for your attention.")
        ]
    else:
        raw_secs = [
            ("1. Situation Overview & Greetings (Tổng quan tình huống & Chào hỏi)", f"In real-life situations involving {context_desc_en}, using clear and polite English expressions makes communication smooth and natural. Always start with a friendly greeting such as 'Excuse me' or 'Good morning'."),
            ("2. Key Interactions & Useful Questions (Giao tiếp chính & Câu hỏi thông dụng)", f"When dealing with {context_desc_en}, listen carefully to instructions and use polite requests such as 'Could you please help me with...' or 'Could you explain the steps?'"),
            ("3. Polite Closing (Kết thúc lịch sự)", f"Once everything is completed regarding {context_desc_en}, express your appreciation warmly by saying 'Thank you very much for your assistance.'")
        ]

    secs = [{"heading": h, "en": e, "vi": translate_stable(e, "en", "vi")} for h, e in raw_secs]
    words = list(dict.fromkeys([w.lower() for w in re.findall(r'\b[a-zA-Z]{5,}\b', context_desc_en)]))[:4]
    vocab = [{"word": w, "mean": translate_stable(w, "en", "vi")} for w in words]
    return {"title": f"{'LECTURE SCRIPT' if is_academic else 'PRACTICAL GUIDE'}: {topic_text.upper()}", "sections": secs, "vocab": vocab}

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
# TAB 3: HỌC TIẾNG ANH CÙNG AI (HOÀN THIỆN TOÀN BỘ LỖI TẢI ẢNH, VIDEO & GIA SƯ)
# ==============================================================================
with tab3:
    st.subheader("Hệ thống Học Tiếng Anh Tương tác cùng AI")

    with st.expander("Tải tài liệu lên (Word / PDF / PNG)", expanded=False):
        uploaded_file_t3 = st.file_uploader("Chọn file Word (.docx), PDF (.pdf) hoặc Hình ảnh (.png):", type=["docx", "pdf", "png"], key="t3_file_uploader")
        if uploaded_file_t3 is not None:
            if uploaded_file_t3.name.lower().endswith(".png"):
                st.image(uploaded_file_t3, caption="Hình ảnh đã tải lên", width=260)
            if st.button("Tạo Hội thoại & Bài giảng từ tài liệu này", type="primary"):
                with st.spinner("Đang phân tích nội dung & tổng hợp giọng đọc Nam/Nữ..."):
                    extracted_ctx, is_img = analyze_uploaded_file(uploaded_file_t3)
                    # Tạo cả Hội thoại và Bài giảng đầy đủ từ nội dung ảnh/tài liệu
                    raw_dlg = build_dialogue_payload(extracted_ctx or uploaded_file_t3.name)
                    st.session_state["t3_dlg_json"] = attach_neural_audio_to_dialogue(json.dumps(raw_dlg, ensure_ascii=False))
                    
                    raw_lec = build_lecture_payload(uploaded_file_t3.name, extracted_ctx, is_image_source=is_img)
                    st.session_state["t3_lec_json"] = json.dumps(raw_lec, ensure_ascii=False)
                    st.success("Đã tạo xong Hội thoại & Bài giảng chi tiết từ tài liệu/hình ảnh!")

    col_in, col_go = st.columns([4, 1])
    with col_in:
        user_topic = st.text_input(
            "Nhập chủ đề bất kỳ (VD: kiểm định phân phối chuẩn, hồi quy logistic, tại ga metro, nhập cảnh sân bay...):",
            placeholder="Nhập chủ đề muốn tạo hội thoại & bài giảng...",
            key="t3_topic_input"
        )
    with col_go:
        st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)
        btn_create_topic = st.button("Tạo nội dung AI", type="primary", use_container_width=True)

    if btn_create_topic and user_topic.strip():
        with st.spinner(f"Đang biên soạn hội thoại Nam/Nữ & bài giảng về '{user_topic}'..."):
            raw_dlg = build_dialogue_payload(user_topic.strip())
            st.session_state["t3_dlg_json"] = attach_neural_audio_to_dialogue(json.dumps(raw_dlg, ensure_ascii=False))
            raw_lec = build_lecture_payload(user_topic.strip())
            st.session_state["t3_lec_json"] = json.dumps(raw_lec, ensure_ascii=False)

    if "t3_dlg_json" not in st.session_state:
        with st.spinner("Đang khởi tạo dữ liệu học tập..."):
            init_dlg = build_dialogue_payload("Kiểm định phân phối chuẩn trong SPSS")
            st.session_state["t3_dlg_json"] = attach_neural_audio_to_dialogue(json.dumps(init_dlg, ensure_ascii=False))
            init_lec = build_lecture_payload("Kiểm định phân phối chuẩn trong SPSS")
            st.session_state["t3_lec_json"] = json.dumps(init_lec, ensure_ascii=False)

    dlg_json_safe = st.session_state["t3_dlg_json"]
    lec_json_safe = st.session_state["t3_lec_json"]

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
                grid-template-columns: repeat(4, 1fr);
                background-color: #0d6efd;
                border-radius: 8px;
                padding: 5px;
                gap: 5px;
                margin-bottom: 12px;
                box-shadow: 0 3px 8px rgba(13, 110, 253, 0.25);
            }
            @media (max-width: 768px) {
                .blue-menu-bar { grid-template-columns: repeat(2, 1fr); }
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

            .canvas-stage {
                background: linear-gradient(135deg, #071936 0%, #0d6efd 100%);
                border-radius: 10px;
                padding: 12px;
                color: white;
                margin-bottom: 12px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.15);
            }
            canvas#sceneCanvas {
                width: 100%;
                height: 210px;
                background: #0a2540;
                border-radius: 8px;
                display: block;
                border: 1px solid rgba(255,255,255,0.2);
            }
            .stage-caption {
                background: rgba(0, 0, 0, 0.6);
                border-radius: 6px;
                padding: 10px;
                margin-top: 8px;
                text-align: center;
                min-height: 64px;
            }
            .controls-toolbar {
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
                justify-content: center;
                margin-top: 10px;
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
            .tutor-card {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                margin-top: 8px;
            }
        </style>
    </head>
    <body>
        <div class="blue-menu-bar">
            <button class="menu-item active" onclick="switchSubTab('video', this)">
                <span>Video & Hội thoại</span>
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
            <button class="menu-item" onclick="switchSubTab('chat', this)">
                <span>Gia sư Song ngữ</span>
                <span class="arrow-icon">▼</span>
            </button>
        </div>

        <!-- PANEL 1: VIDEO HOẠT HỌA + HỘI THOẠI NAM/NỮ + TỪ VỰNG -->
        <div id="sub-video" class="dropdown-panel active">
            <div style="font-weight:bold; color:#084298; font-size:15px; margin-bottom:10px;" id="dlg-main-title"></div>
            <div class="video-layout">
                <div class="video-main">
                    <div class="canvas-stage">
                        <canvas id="sceneCanvas" width="640" height="210"></canvas>
                        <div class="stage-caption">
                            <div style="font-size:14px; font-weight:bold; color:#fff;" id="stage-en">Bấm "Phát Video & Hội thoại" để xem hoạt họa & nghe đối đáp Nam - Nữ</div>
                            <div style="font-size:12.5px; color:#9ec5fe; font-style:italic; margin-top:4px;" id="stage-vi"></div>
                        </div>
                        <div class="controls-toolbar">
                            <button class="btn-ui btn-green" onclick="playAllTurns(1.0)">Phát Video & Hội thoại (1.0x)</button>
                            <button class="btn-ui btn-navy" onclick="playAllTurns(0.75)">Nghe chậm (0.75x)</button>
                            <button class="btn-ui btn-red" onclick="stopAudio()">Dừng</button>
                            <button class="btn-ui btn-white" id="btn-sub" onclick="toggleSubs()">Ẩn phụ đề</button>
                        </div>
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
                <input type="text" id="dict-query" placeholder="Nhập từ tiếng Anh (VD: normality, skewness, logistic)..." onkeypress="if(event.key==='Enter') searchDict()">
                <button class="btn-ui btn-navy" onclick="searchDict()">Tra cứu & Nghe</button>
            </div>
            <div id="dict-output" style="font-size:14px; color:#495057;"></div>
        </div>

        <!-- PANEL 4: GIA SƯ SONG NGỮ NÂNG CAO -->
        <div id="sub-chat" class="dropdown-panel">
            <div class="input-row">
                <input type="text" id="tutor-query" placeholder="Nhập câu tiếng Việt muốn diễn đạt chuẩn bản xứ hoặc câu tiếng Anh cần chỉnh sửa..." onkeypress="if(event.key==='Enter') askTutor()">
                <button class="btn-ui btn-navy" onclick="askTutor()">Phân tích & Gợi ý</button>
            </div>
            <div id="tutor-output" style="font-size:14px;"></div>
        </div>

        <script>
            const DLG_DATA = __DLG_JSON__;
            const LEC_DATA = __LEC_JSON__;

            let currentAudio = null;
            let isPlayingSeq = false;
            let subsVisible = true;
            let lecViVisible = true;
            let activeSpeakerGender = null;
            let wavePhase = 0;

            function switchSubTab(tabId, btn) {
                document.querySelectorAll('.dropdown-panel').forEach(p => p.classList.remove('active'));
                document.querySelectorAll('.menu-item').forEach(b => b.classList.remove('active'));
                document.getElementById('sub-' + tabId).classList.add('active');
                btn.classList.add('active');
                stopAudio();
            }

            // =====================================================================
            // VẼ VIDEO HOẠT HỌA ĐA LỚP SINH ĐỘNG TRÊN CANVAS
            // =====================================================================
            function drawSceneFrame() {
                const canvas = document.getElementById('sceneCanvas');
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                const w = canvas.width;
                const h = canvas.height;

                ctx.clearRect(0, 0, w, h);

                // Nền gradient phòng hội thảo / sân bay / quán cà phê
                let grad = ctx.createLinearGradient(0, 0, w, h);
                grad.addColorStop(0, "#06142e");
                grad.addColorStop(1, "#1d4ed8");
                ctx.fillStyle = grad;
                ctx.fillRect(0, 0, w, h);

                // Bảng trình chiếu / Màn hình bối cảnh ở giữa phía sau
                ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
                ctx.strokeStyle = "rgba(147, 197, 253, 0.4)";
                ctx.lineWidth = 1.5;
                ctx.fillRect(195, 20, 250, 115);
                ctx.strokeRect(195, 20, 250, 115);

                // Vẽ biểu đồ / họa tiết minh họa động trên màn hình giữa
                if (DLG_DATA.scene_type === "academic") {
                    ctx.fillStyle = "#93c5fd";
                    ctx.font = "bold 11px sans-serif";
                    ctx.fillText("BIOSTATISTICS & CLINICAL DATA", 215, 38);
                    // Vẽ các cột biểu đồ chuyển động nhẹ
                    for (let b = 0; b < 7; b++) {
                        let bh = 25 + Math.abs(Math.sin(b * 0.8 + wavePhase * 0.04)) * 45;
                        ctx.fillStyle = b === 1 ? "#38bdf8" : "rgba(147, 197, 253, 0.5)";
                        ctx.fillRect(220 + b * 28, 122 - bh, 18, bh);
                    }
                } else {
                    ctx.fillStyle = "#fde047";
                    ctx.font = "bold 11px sans-serif";
                    ctx.fillText("LIVE COMMUNICATION SCENE", 230, 38);
                }

                // Sóng âm thanh ở khu vực giữa
                for (let i = 0; i < 16; i++) {
                    let barH = activeSpeakerGender ? (10 + Math.abs(Math.sin(wavePhase * 0.25 + i * 0.55)) * 34) : 5;
                    ctx.fillStyle = activeSpeakerGender === 'male' ? "#38bdf8" : (activeSpeakerGender === 'female' ? "#f472b6" : "rgba(255,255,255,0.25)");
                    ctx.fillRect(216 + i * 13, 165 - barH / 2, 7, barH);
                }

                // Nhân vật Nam (bên trái)
                let malePulse = (activeSpeakerGender === 'male') ? Math.sin(wavePhase * 0.3) * 6 : 0;
                ctx.beginPath();
                ctx.arc(110, 105, 38 + Math.abs(malePulse), 0, Math.PI * 2);
                ctx.fillStyle = (activeSpeakerGender === 'male') ? "rgba(56, 189, 248, 0.35)" : "rgba(255,255,255,0.07)";
                ctx.fill();

                ctx.beginPath();
                ctx.arc(110, 92, 20, 0, Math.PI * 2);
                ctx.fillStyle = "#38bdf8";
                ctx.fill();
                // Miệng cử động khi nhân vật Nam đang nói
                if (activeSpeakerGender === 'male') {
                    ctx.fillStyle = "#06142e";
                    ctx.beginPath();
                    ctx.ellipse(110, 99, 6, 2 + Math.abs(Math.sin(wavePhase * 0.4)) * 4, 0, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.fillStyle = "#0284c7";
                ctx.fillRect(85, 116, 50, 36);
                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 12px sans-serif";
                ctx.textAlign = "center";
                ctx.fillText("Giọng Nam", 110, 172);

                // Nhân vật Nữ (bên phải)
                let femalePulse = (activeSpeakerGender === 'female') ? Math.sin(wavePhase * 0.3) * 6 : 0;
                ctx.beginPath();
                ctx.arc(530, 105, 38 + Math.abs(femalePulse), 0, Math.PI * 2);
                ctx.fillStyle = (activeSpeakerGender === 'female') ? "rgba(244, 114, 182, 0.35)" : "rgba(255,255,255,0.07)";
                ctx.fill();

                ctx.beginPath();
                ctx.arc(530, 92, 20, 0, Math.PI * 2);
                ctx.fillStyle = "#f472b6";
                ctx.fill();
                // Miệng cử động khi nhân vật Nữ đang nói
                if (activeSpeakerGender === 'female') {
                    ctx.fillStyle = "#06142e";
                    ctx.beginPath();
                    ctx.ellipse(530, 99, 6, 2 + Math.abs(Math.sin(wavePhase * 0.4)) * 4, 0, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.fillStyle = "#db2777";
                ctx.fillRect(505, 116, 50, 36);
                ctx.fillStyle = "#ffffff";
                ctx.fillText("Giọng Nữ", 530, 172);
                ctx.textAlign = "left";

                wavePhase++;
                requestAnimationFrame(drawSceneFrame);
            }
            drawSceneFrame();

            // =====================================================================
            // PHÁT ÂM THANH EDGE-TTS TỪNG CÂU & TỪ VỰNG
            // =====================================================================
            function stopAudio() {
                isPlayingSeq = false;
                activeSpeakerGender = null;
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
                        activeSpeakerGender = null;
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
                    u.onend = function() {
                        activeSpeakerGender = null;
                        if (cb) cb();
                    };
                    window.speechSynthesis.speak(u);
                }
            }

            function playTurnByIndex(idx) {
                let t = DLG_DATA.turns[idx];
                activeSpeakerGender = t.gender;
                document.getElementById('stage-en').innerText = subsVisible ? `${t.role}: "${t.en}"` : "[Đang ẩn phụ đề]";
                document.getElementById('stage-vi').innerText = subsVisible ? t.vi : "";
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
                        activeSpeakerGender = null;
                        document.querySelectorAll('.turn-card').forEach(c => c.classList.remove('active-turn'));
                        return;
                    }
                    let t = DLG_DATA.turns[idx];
                    activeSpeakerGender = t.gender;
                    document.querySelectorAll('.turn-card').forEach(c => c.classList.remove('active-turn'));
                    let card = document.getElementById('tcard-' + idx);
                    if (card) card.classList.add('active-turn');

                    document.getElementById('stage-en').innerText = subsVisible ? `${t.role}: "${t.en}"` : "[Đang ẩn phụ đề]";
                    document.getElementById('stage-vi').innerText = subsVisible ? t.vi : "";

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
                out.innerHTML = "Đang tra cứu từ điển quốc tế...";
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

            // GIA SƯ SONG NGỮ NÂNG CAO: PHÂN TÍCH 2 PHONG CÁCH (TỰ NHIÊN & HỌC THUẬT) + GIẢI THÍCH CẤU TRÚC
            async function askTutor() {
                let q = document.getElementById('tutor-query').value.trim();
                if (!q) return;
                let out = document.getElementById('tutor-output');
                out.innerHTML = "Gia sư AI đang phân tích ngữ cảnh và gợi ý cách diễn đạt chuẩn...";
                let isVi = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i.test(q);
                
                try {
                    if (isVi) {
                        let res = await fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=vi&tl=en&q=${encodeURIComponent(q)}`);
                        let data = await res.json();
                        let baseEn = Array.isArray(data) ? data.join(" ") : data;

                        // Nâng cấp văn phong học thuật / giảng dạy
                        let academicEn = baseEn
                            .replace(/^You should /i, "Students are strongly advised to ")
                            .replace(/onto your computer/i, "on your personal computer")
                            .replace(/to follow the lesson better/i, "to facilitate seamless hands-on practice during the lecture")
                            .replace(/working on the computer with your instructor/i, "following the instructor's live demonstration");

                        if (academicEn === baseEn) {
                            academicEn = "To ensure optimal engagement, " + baseEn.charAt(0).toLowerCase() + baseEn.slice(1);
                        }

                        out.innerHTML = `
                            <div class="tutor-card">
                                <div style="margin-bottom:8px;">
                                    <span style="background:#cfe2ff; color:#084298; padding:2px 8px; border-radius:4px; font-size:11.5px; font-weight:bold;">1. DIỄN ĐẠT GIAO TIẾP TỰ NHIÊN</span>
                                    <div style="font-size:15px; font-weight:bold; color:#0d6efd; margin-top:4px;">"${baseEn}"</div>
                                </div>
                                <div style="border-top:1px dashed #ced4da; padding-top:8px; margin-bottom:8px;">
                                    <span style="background:#d1e7dd; color:#0f5132; padding:2px 8px; border-radius:4px; font-size:11.5px; font-weight:bold;">2. VĂN PHONG HỌC THUẬT / GIẢNG ĐƯỜNG</span>
                                    <div style="font-size:15px; font-weight:bold; color:#198754; margin-top:4px;">"${academicEn}"</div>
                                </div>
                                <div style="background:#fff3cd; padding:8px 10px; border-radius:6px; font-size:13px; color:#664d03;">
                                    <b>Ghi chú từ Gia sư:</b> Khi hướng dẫn sinh viên trên lớp, dùng cụm <i>"hands-on practice"</i> (thực hành trực tiếp) và <i>"live demonstration"</i> (thao tác mẫu trực tiếp) sẽ tự nhiên và chuẩn học thuật hơn dịch từng từ.
                                </div>
                            </div>
                        `;
                    } else {
                        let res = await fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=vi&q=${encodeURIComponent(q)}`);
                        let data = await res.json();
                        let viMeaning = Array.isArray(data) ? data.join(" ") : data;

                        let resBack = await fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=vi&tl=en&q=${encodeURIComponent(viMeaning)}`);
                        let dataBack = await resBack.json();
                        let polished = Array.isArray(dataBack) ? dataBack.join(" ") : dataBack;

                        out.innerHTML = `
                            <div class="tutor-card">
                                <div style="margin-bottom:6px;"><b>Nghĩa tiếng Việt chuẩn xác:</b> ${viMeaning}</div>
                                <div style="margin-bottom:6px;"><b>Gợi ý câu tự nhiên hơn:</b> <span style="color:#0d6efd; font-weight:bold;">"${polished}"</span></div>
                            </div>
                        `;
                    }
                } catch(e) { out.innerHTML = "Lỗi kết nối Gia sư AI."; }
            }

            renderAll();
        </script>
    </body>
    </html>
    """

    final_tutor_html = (tutor_ui_template
        .replace("__DLG_JSON__", dlg_json_safe)
        .replace("__LEC_JSON__", lec_json_safe)
    )
    components.html(final_tutor_html, height=880, scrolling=True)
