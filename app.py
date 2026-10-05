import time
import json
import asyncio
import urllib.parse
import urllib.request
import textwrap
import streamlit as st
import streamlit.components.v1 as components
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
</style>
""", unsafe_allow_html=True)

# Đã bỏ các icon emoji để đồng bộ chuẩn xác với hình ảnh giao diện của anh
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

@st.cache_data(show_spinner=False, ttl=3600)
def translate_stable(text, src_code, tgt_code):
    if not text.strip():
        return ""
    
    src = "zh-CN" if src_code.lower() == "zh-cn" else src_code
    tgt = "zh-CN" if tgt_code.lower() == "zh-cn" else tgt_code

    def call_google_gtx(t):
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": src, "tl": tgt, "dt": "t", "q": t}
        query_string = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{url}?{query_string}", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return "".join([item[0] for item in data[0] if item[0]])

    paragraphs = text.split('\n')
    final_translated = []
    
    for p in paragraphs:
        if not p.strip():
            final_translated.append("")
            continue
            
        chunks = textwrap.wrap(p, width=1500, replace_whitespace=False)
        p_trans = ""
        for chunk in chunks:
            try:
                p_trans += call_google_gtx(chunk) + " "
            except Exception as e:
                p_trans += f"[Lỗi: Không thể kết nối máy chủ Google - {str(e)}] "
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

tab1, tab2 = st.tabs([
    "💬 Dịch văn bản & Hội thoại", 
    "🎙 Cabin Phiên dịch Trực tiếp"
])

with tab1:
    st.subheader("Dịch văn bản & Hội thoại chuyên sâu")
    
    col_t1_src, col_t1_tgt = st.columns(2)
    with col_t1_src:
        src_lang_name_t1 = st.selectbox("Ngôn ngữ nguồn:", list(LANG_OPTIONS.keys()), index=0, key="t1_src")
    with col_t1_tgt:
        tgt_lang_name_t1 = st.selectbox("Ngôn ngữ đích:", list(LANG_OPTIONS.keys()), index=1, key="t1_tgt")

    input_text = st.text_area("Nhập văn bản cần dịch:", height=150, placeholder="Dán văn bản cần dịch vào đây (Hỗ trợ văn bản siêu dài)...", key="t1_input_text")
    
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
        st.markdown("### Cài đặt Âm thanh & Tải về:")
        
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

with tab2:
    st.subheader("Phiên dịch Hội nghị Trực tiếp (Cabin Song Song)")

    col_t2_src, col_t2_tgt, _ = st.columns([2, 2, 1])
    with col_t2_src:
        src_lang_name_t2 = st.selectbox("Ngôn ngữ nói (Mic):", list(LANG_OPTIONS.keys()), index=0, key="t2_src")
    with col_t2_tgt:
        tgt_lang_name_t2 = st.selectbox("Ngôn ngữ dịch out:", list(LANG_OPTIONS.keys()), index=1, key="t2_tgt")

    lang_code_js = "vi-VN" if LANG_OPTIONS[src_lang_name_t2] == "vi" else "en-US"
    src_code_val = LANG_OPTIONS[src_lang_name_t2]
    tgt_code_val = LANG_OPTIONS[tgt_lang_name_t2]

    st.write("---")

    cabin_html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            .cabin-box {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 15px;
                text-align: center;
            }}
            .btn-control {{
                font-family: 'Times New Roman', Times, serif !important;
                padding: 12px 24px;
                font-size: 14px !important;
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
                font-family: 'Times New Roman', Times, serif !important;
                margin-top: 10px;
                font-weight: bold;
                font-size: 13px !important;
                color: #28a745;
            }}
            .cabin-grid {{
                display: flex;
                flex-direction: row;
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
                height: 500px; 
                overflow-y: auto; 
                box-shadow: inset 0 0 5px rgba(0,0,0,0.05);
            }}
            .panel-title {{
                font-family: 'Times New Roman', Times, serif !important;
                font-weight: bold;
                font-size: 14px !important;
                margin-bottom: 10px;
                border-bottom: 1px solid #e9ecef;
                padding-bottom: 5px;
            }}
            .panel-content {{
                font-size: 16px;
                line-height: 1.6;
                word-wrap: break-word;
            }}
            
            @media (max-width: 768px) {{
                .cabin-grid {{
                    flex-direction: column;
                }}
                .cabin-panel {{
                    height: 350px; 
                }}
            }}
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
                <div class="panel-title">Bản dịch Cabin ({tgt_lang_name_t2})</div>
                <div id="live-translated-text" class="panel-content"></div>
            </div>
            <div class="cabin-panel" id="scroll-orig">
                <div class="panel-title">Phát biểu Gốc ({src_lang_name_t2})</div>
                <div id="live-original-text" class="panel-content"></div>
            </div>
        </div>
    </div>

    <script>
        var recognition;
        var isRunning = false;
        
        // Quản lý riêng rẽ phiên lịch sử và phiên nháp để tránh lặp từ trên điện thoại
        var sessionOrigHistory = "";
        var sessionTransHistory = "";
        var origSegments = [];
        var transSegments = [];
        var finalProcessed = [];
        
        var transQueue = [];
        var isTranslatingFinal = false;
        var translationTimer;

        function scrollToBottom() {{
            let pTrans = document.getElementById('scroll-trans');
            let pOrig = document.getElementById('scroll-orig');
            if(pTrans) pTrans.scrollTop = pTrans.scrollHeight;
            if(pOrig) pOrig.scrollTop = pOrig.scrollHeight;
        }}

        async function fetchTranslation(text) {{
            if (!text || text.trim() === "") return "";
            let chunk = text.length > 800 ? text.substring(text.length - 800) : text;
            let q = encodeURIComponent(chunk);
            let src = '{src_code_val}';
            let tgt = '{tgt_code_val}';

            try {{
                let res1 = await fetch(`https://translate.googleapis.com/translate_a/single?client=gtx&sl=${{src}}&tl=${{tgt}}&dt=t&q=${{q}}`);
                if (res1.ok) {{
                    let data1 = await res1.json();
                    return data1[0].map(item => item[0]).join("");
                }}
            }} catch(e) {{}}

            try {{
                let res2 = await fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=${{src}}&tl=${{tgt}}&q=${{q}}`);
                if (res2.ok) {{
                    let data2 = await res2.json();
                    if (Array.isArray(data2)) return data2.join(" ");
                    if (typeof data2 === 'string') return data2;
                }}
            }} catch(e) {{}}

            return "[Lỗi mạng - Thử lại sau...]";
        }}

        async function processQueue() {{
            if (isTranslatingFinal || transQueue.length === 0) return;
            isTranslatingFinal = true;
            
            let item = transQueue.shift();
            let translated = await fetchTranslation(item.text);
            
            if (translated && !translated.includes("[Lỗi")) {{
                transSegments[item.index] = translated.trim();
                renderUI();
            }} else {{
                transSegments[item.index] = "[Lỗi mạng]";
                renderUI();
            }}
            
            isTranslatingFinal = false;
            processQueue();
        }}

        function renderUI(interimText = "") {{
            let origHTML = sessionOrigHistory;
            let transHTML = sessionTransHistory;

            // Render lại chính xác từng đoạn, xuống dòng rành mạch bằng <br><br>
            for (let i = 0; i < origSegments.length; i++) {{
                if (origSegments[i]) {{
                    origHTML += "<span style='color: #0056b3; font-weight: 500; display: block; margin-bottom: 12px;'>" + origSegments[i] + "</span>";
                }}
                if (transSegments[i]) {{
                    let color = transSegments[i].includes("[⚡") ? "#888888" : "#28a745";
                    let weight = transSegments[i].includes("[⚡") ? "normal" : "bold";
                    transHTML += "<span style='color: " + color + "; font-weight: " + weight + "; display: block; margin-bottom: 12px;'>" + transSegments[i] + "</span>";
                }}
            }}

            let origBox = document.getElementById('live-original-text');
            let transBox = document.getElementById('live-translated-text');

            if (interimText.trim() !== "") {{
                origBox.innerHTML = origHTML + "<span style='color: #888888; font-style: italic;'>" + interimText + "</span>";
                
                // Gọi API dịch cho text nháp (debounced)
                clearTimeout(translationTimer);
                translationTimer = setTimeout(async () => {{
                    let t_interim = await fetchTranslation(interimText);
                    if (t_interim && !t_interim.includes("[Lỗi")) {{
                        transBox.innerHTML = transHTML + "<span style='color: #888888; font-style: italic;'>" + t_interim + "</span>";
                        scrollToBottom();
                    }}
                }}, 600);
            }} else {{
                origBox.innerHTML = origHTML;
                transBox.innerHTML = transHTML;
            }}
            
            scrollToBottom();
        }}

        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
            document.getElementById('status-badge').innerText = 'Trình duyệt không hỗ trợ Web Speech API. Hãy dùng Google Chrome hoặc Safari!';
        }} else {{
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = '{lang_code_js}';

            recognition.onstart = function() {{
                isRunning = true;
                document.getElementById('status-badge').innerText = 'Trạng thái: Cabin đang mở mic liên tục...';
                document.getElementById('start-btn').disabled = true;
                document.getElementById('stop-btn').disabled = false;
            }};

            recognition.onresult = function(event) {{
                let interimText = "";

                // Cách này khóa chặt hoàn toàn lỗi lặp câu trên điện thoại Android/Chrome
                for (let i = 0; i < event.results.length; ++i) {{
                    let text = event.results[i][0].transcript.trim();
                    
                    if (event.results[i].isFinal) {{
                        if (!finalProcessed[i]) {{
                            finalProcessed[i] = true; // Khóa mốc này vĩnh viễn
                            
                            if (text !== "") {{
                                text = text.charAt(0).toUpperCase() + text.slice(1);
                                if (!text.match(/[.!?]$/)) text += ".";
                                
                                origSegments[i] = text;
                                transSegments[i] = "[⚡...]";
                                
                                transQueue.push({{index: i, text: text}});
                                processQueue();
                            }} else {{
                                origSegments[i] = "";
                                transSegments[i] = "";
                            }}
                        }}
                    }} else {{
                        interimText += text + " ";
                    }}
                }}

                renderUI(interimText.trim());
            }};

            recognition.onend = function() {{
                // Khi micro nghỉ, lưu tạm các câu đã chốt vào lịch sử và reset mảng để làm trống bộ nhớ
                let origHTML = "";
                let transHTML = "";
                for (let i = 0; i < origSegments.length; i++) {{
                    if (origSegments[i]) origHTML += "<span style='color: #0056b3; font-weight: 500; display: block; margin-bottom: 12px;'>" + origSegments[i] + "</span>";
                    if (transSegments[i]) {{
                        let color = transSegments[i].includes("[⚡") ? "#888888" : "#28a745";
                        let weight = transSegments[i].includes("[⚡") ? "normal" : "bold";
                        transHTML += "<span style='color: " + color + "; font-weight: " + weight + "; display: block; margin-bottom: 12px;'>" + transSegments[i] + "</span>";
                    }}
                }}
                
                sessionOrigHistory += origHTML;
                sessionTransHistory += transHTML;
                
                origSegments = [];
                transSegments = [];
                finalProcessed = [];

                if (isRunning) {{
                    try {{ recognition.start(); }} catch (e) {{}}
                }} else {{
                    document.getElementById('status-badge').innerText = 'Trạng thái: Đã dừng hệ thống cabin.';
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('stop-btn').disabled = true;
                }}
            }};
        }}

        function startCabin() {{
            if (recognition) {{
                isRunning = true;
                sessionOrigHistory = "";
                sessionTransHistory = "";
                origSegments = [];
                transSegments = [];
                finalProcessed = [];
                transQueue = [];
                isTranslatingFinal = false;
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

    components.html(cabin_html_code, height=750)
