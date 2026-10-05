import time
import json
import asyncio
import urllib.parse
import urllib.request
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
</style>
""", unsafe_allow_html=True)

LANG_OPTIONS = {
    "🇻🇳 Tiếng Việt": "vi",
    "🇺🇸 Tiếng Anh (Mỹ)": "en",
    "🇬🇧 Tiếng Anh (Anh)": "en",
    "🇨🇳 Tiếng Trung (Phổ thông)": "zh-CN",
    "🇯🇵 Tiếng Nhật": "ja",
    "🇰🇷 Tiếng Hàn": "ko",
    "🇫🇷 Tiếng Pháp": "fr",
    "🇩🇪 Tiếng Đức": "de",
    "🇪🇸 Tiếng Tây Ban Nha": "es",
    "🇮🇹 Tiếng Ý": "it",
    "🇷🇺 Tiếng Nga": "ru",
    "🇹🇭 Tiếng Thái": "th"
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
    
    src = src_code.lower()
    tgt = tgt_code.lower()
    if src == "zh-cn": src = "zh-CN"
    if tgt == "zh-cn": tgt = "zh-CN"

    try:
        translator = GoogleTranslator(source=src, target=tgt)
        max_len = 4000 
        if len(text) <= max_len:
            return translator.translate(text)
        else:
            paragraphs = text.split('\n')
            result = ""
            for p in paragraphs:
                if p.strip():
                    if len(p) > max_len:
                        chunks = [p[i:i+max_len] for i in range(0, len(p), max_len)]
                        for chunk in chunks:
                            result += translator.translate(chunk) + " "
                        result += "\n"
                    else:
                        result += translator.translate(p) + "\n"
                else:
                    result += "\n"
            return result.strip()
    except Exception as e:
        return f"Không thể kết nối dịch thuật: {str(e)}"

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
    st.markdown("Hệ thống tự động nhận diện điểm dừng, ngắt đoạn nhạy hơn khi người nói ngừng 1 giây.")

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
        <style>
            .cabin-box {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
            }}
            .btn-control {{
                font-family: 'Times New Roman', Times, serif !important;
                padding: 12px 28px;
                font-size: 13px !important;
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
                margin-top: 15px;
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
                padding: 20px;
                text-align: left;
                height: 480px; 
                overflow-y: auto; 
            }}
            .panel-title {{
                font-family: 'Times New Roman', Times, serif !important;
                font-weight: bold;
                font-size: 13px !important;
                margin-bottom: 12px;
                border-bottom: 1px solid #e9ecef;
                padding-bottom: 8px;
            }}
            .panel-content {{
                font-size: 17px;
                line-height: 1.6;
                word-wrap: break-word;
                white-space: pre-wrap; 
            }}
            #live-translated-text {{ color: #28a745; font-weight: bold; }}
            #live-original-text {{ color: #0056b3; font-style: italic; }}
            
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
        var historyOriginal = "";
        var historyTranslated = "";
        var translationTimer;
        var pauseTimer; 

        function scrollToBottom() {{
            let pTrans = document.getElementById('scroll-trans');
            let pOrig = document.getElementById('scroll-orig');
            if(pTrans) pTrans.scrollTop = pTrans.scrollHeight;
            if(pOrig) pOrig.scrollTop = pOrig.scrollHeight;
        }}

        async function fetchTranslation(text) {{
            if (!text || text.trim() === "") return "";
            let chunk = text.length > 500 ? text.substring(text.length - 500) : text;
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

            try {{
                let gtxUrl = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${{src}}&tl=${{tgt}}&dt=t&q=${{q}}`;
                let res3 = await fetch(`https://api.allorigins.win/get?url=${{encodeURIComponent(gtxUrl)}}`);
                if (res3.ok) {{
                    let data3 = await res3.json();
                    let actualData = JSON.parse(data3.contents);
                    return actualData[0].map(item => item[0]).join("");
                }}
            }} catch(e) {{}}

            return "[Hệ thống nghẽn...]";
        }}

        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {{
            document.getElementById('status-badge').innerText = 'Trình duyệt không hỗ trợ Web Speech API. Hãy dùng Google Chrome hoặc Microsoft Edge!';
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
                clearTimeout(pauseTimer);

                let interim = '';
                let finalStr = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {{
                    if (event.results[i].isFinal) {{
                        let text = event.results[i][0].transcript.trim();
                        text = text.charAt(0).toUpperCase() + text.slice(1);
                        if (!text.match(/[.!?]$/)) text += ".";
                        finalStr += text + " ";
                    }} else {{
                        interim += event.results[i][0].transcript;
                    }}
                }}

                let origBox = document.getElementById('live-original-text');
                let transBox = document.getElementById('live-translated-text');

                origBox.innerText = historyOriginal + finalStr + interim;
                scrollToBottom(); 

                if (finalStr.trim() !== "") {{
                    clearTimeout(translationTimer);
                    
                    let cleanFinal = finalStr.trim();
                    historyOriginal += cleanFinal + "\\n\\n";
                    origBox.innerText = historyOriginal;
                    scrollToBottom();

                    fetchTranslation(cleanFinal).then(translated => {{
                        if (translated && !translated.includes("[Hệ thống")) {{
                            let cleanTrans = translated.trim();
                            cleanTrans = cleanTrans.charAt(0).toUpperCase() + cleanTrans.slice(1);
                            if (!cleanTrans.match(/[.!?]$/)) cleanTrans += ".";
                            
                            historyTranslated += cleanTrans + "\\n\\n";
                        }}
                        transBox.innerText = historyTranslated;
                        scrollToBottom();
                    }});
                }} 
                
                if (interim.trim() !== "") {{
                    clearTimeout(translationTimer);
                    translationTimer = setTimeout(() => {{
                        fetchTranslation(interim).then(translatedInterim => {{
                            if (translatedInterim && !translatedInterim.includes("[Hệ thống")) {{
                                transBox.innerText = historyTranslated + translatedInterim;
                                scrollToBottom();
                            }}
                        }});
                    }}, 400); 
                }}

                pauseTimer = setTimeout(() => {{
                    let hasNewlineAdded = false;

                    if (historyOriginal.trim() !== "" && !historyOriginal.endsWith("\\n\\n")) {{
                        historyOriginal = historyOriginal.trimEnd() + "\\n\\n";
                        document.getElementById('live-original-text').innerText = historyOriginal;
                        hasNewlineAdded = true;
                    }}

                    if (historyTranslated.trim() !== "" && !historyTranslated.endsWith("\\n\\n")) {{
                        historyTranslated = historyTranslated.trimEnd() + "\\n\\n";
                        document.getElementById('live-translated-text').innerText = historyTranslated;
                        hasNewlineAdded = true;
                    }}

                    if (hasNewlineAdded) {{
                        scrollToBottom();
                    }}
                }}, 1000); 
            }};

            recognition.onend = function() {{
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
                historyOriginal = "";
                historyTranslated = "";
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

    components.html(cabin_html_code, height=850)
