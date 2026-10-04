import random
import streamlit as st
import asyncio
import edge_tts
from deep_translator import GoogleTranslator
from google import genai
from google.genai import types

# 1. Cấu hình trang
st.set_page_config(
    page_title="AI Translate",
    page_icon="🌐",
    layout="wide"
)

# 2. XÁC THỰC MẬT KHẨU TỪ SECRETS
def check_password():
    """Kiểm tra mật khẩu truy cập ứng dụng"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.subheader("🔒 Yêu cầu Mật khẩu Truy cập")
        user_input = st.text_input("Nhập mật khẩu để tiếp tục:", type="password")
        
        if st.button("Đăng nhập", type="primary"):
            # Lấy mật khẩu từ Secrets, mặc định là 123456 nếu chưa cấu hình
            correct_password = st.secrets.get("APP_PASSWORD", "123456")
            if user_input == correct_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Mật khẩu không đúng. Vui lòng thử lại!")
        return False
    return True

if not check_password():
    st.stop()

# 3. LẤY DANH SÁCH API KEYS TỪ SECRETS
# Hỗ trợ nhận 1 string duy nhất hoặc 1 danh sách nhiều API Keys để xoay vòng
raw_keys = st.secrets.get("GOOGLE_API_KEYS", st.secrets.get("GOOGLE_API_KEY", []))
if isinstance(raw_keys, str):
    API_KEYS = [raw_keys]
else:
    API_KEYS = list(raw_keys)

# Danh sách giọng đọc mẫu của Google AI Studio
GOOGLE_VOICES = {
    "Nam - Trầm ấm, Trang trọng (Fenrir)": "Fenrir",
    "Nam - Truyền cảm (Puck)": "Puck",
    "Nam - Điềm tĩnh, Báo cáo (Charon)": "Charon",
    "Nữ - Nhẹ nhàng, Rõ chữ (Kore)": "Kore",
    "Nữ - Truyền cảm, Thuyết trình (Aoede)": "Aoede"
}

# 4. HÀM GỌI GEMINI TTS CÓ TỰ ĐỘNG XOAY VÒNG KEY (KEY ROTATION)
def generate_google_tts(text, voice_name, style_prompt):
    if not API_KEYS:
        raise Exception("Chưa cấu hình GOOGLE_API_KEYS trong Streamlit Secrets!")
    
    # Xáo trộn danh sách Key để phân bổ đều lưu lượng
    shuffled_keys = API_KEYS.copy()
    random.shuffle(shuffled_keys)
    
    last_error = None
    for api_key in shuffled_keys:
        try:
            client = genai.Client(api_key=api_key)
            full_prompt = f"{style_prompt}\n\nVăn bản cần đọc:\n{text}"
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="audio/mp3",
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
            
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return part.inline_data.data
        except Exception as e:
            last_error = e
            continue  # Nếu Key hiện tại bị lỗi hạn mức (Quota), tự động nhảy sang Key tiếp theo
            
    raise Exception(f"Tất cả API Keys dự phòng đều bị hết hạn mức hoặc lỗi: {last_error}")

# --- GIAO DIỆN ỨNG DỤNG ---
st.title("AI Translate")

tab1, tab2 = st.tabs(["📝 Chuyển Văn bản thành Giọng đọc (TTS)", "🌐 Dịch Hội nghị Trực tiếp"])

# ==============================================================================
# TAB 1: TEXT TO SPEECH
# ==============================================================================
with tab1:
    st.subheader("Text to speech")
    
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        selected_voice_label = st.selectbox(
            "1. Chọn giọng đọc Google:",
            list(GOOGLE_VOICES.keys()),
            index=0
        )
        voice_code = GOOGLE_VOICES[selected_voice_label]
        
        style_instruction = st.selectbox(
            "2. Yêu cầu phong cách & giọng vùng miền (Prompt):",
            [
                "Hãy đọc bằng giọng Nam miền Bắc, phong cách báo cáo khoa học, phát âm rõ ràng, tốc độ vừa phải, trang trọng.",
                "Hãy đọc bằng giọng Nữ miền Bắc, phong cách thuyết trình hội thảo, truyền cảm.",
                "Hãy đọc bằng giọng Nam miền Nam, tự nhiên, điềm tĩnh.",
                "Hãy đọc bằng giọng Nữ miền Nam, nhẹ nhàng, rõ chữ."
            ]
        )

        text_input = st.text_area(
            "3. Nhập nội dung văn bản / bài báo cáo:",
            height=200,
            placeholder="Nhập văn bản cần chuyển thành giọng đọc..."
        )
        
        btn_generate = st.button("▶ Đọc & Tạo file MP3", type="primary", use_container_width=True)

    with col_right:
        st.markdown("### Kết quả âm thanh")
        if btn_generate:
            if not text_input.strip():
                st.warning("⚠️ Vui lòng nhập nội dung văn bản!")
            else:
                with st.spinner("⏳ Đang tạo âm thanh từ Google AI Studio..."):
                    try:
                        audio_data = generate_google_tts(text_input, voice_code, style_instruction)
                        st.success("✅ Tạo âm thanh thành công!")
                        
                        st.audio(audio_data, format="audio/mp3")
                        
                        st.download_button(
                            label="📥 Tải file MP3 về máy",
                            data=audio_data,
                            file_name="bao_cao_ai_translate.mp3",
                            mime="audio/mp3",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"❌ Có lỗi xảy ra: {e}")

# ==============================================================================
# TAB 2: DỊCH HỘI NGHỊ TRỰC TIẾP
# ==============================================================================
with tab2:
    st.subheader("Phiên dịch Hội nghị Trực tiếp")
    
    col_lang1, col_lang2 = st.columns(2)
    with col_lang1:
        src_lang = st.selectbox("Ngôn ngữ gốc:", ["Tiếng Việt", "Tiếng Anh"], index=0)
    with col_lang2:
        tgt_lang = st.selectbox("Ngôn ngữ đích:", ["Tiếng Anh", "Tiếng Việt"], index=0)
        
    speech_text = st.text_area("Nội dung phát biểu:", height=120, placeholder="Nhập văn bản cần dịch...")
    btn_translate = st.button("🔄 Dịch ngay", type="primary", use_container_width=True)
    
    if btn_translate and speech_text.strip():
        with st.spinner("⏳ Đang xử lý dịch thuật..."):
            lang_map = {"Tiếng Việt": "vi", "Tiếng Anh": "en"}
            translated_text = GoogleTranslator(
                source=lang_map[src_lang], 
                target=lang_map[tgt_lang]
            ).translate(speech_text)
            
            st.markdown(f"**Bản dịch ({tgt_lang}):**")
            st.success(translated_text)
