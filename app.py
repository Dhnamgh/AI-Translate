import time
import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# 1. HÀM XỬ LÝ LỖI RATE LIMIT CHO DỊCH THUẬT
# ==========================================
def translate_safe(text, target_lang='en', max_retries=3):
    """
    Hàm dịch thuật an toàn, tự động tạm dừng và thử lại khi gặp lỗi Rate Limit (429/Too Many Requests).
    """
    # LƯU Ý: Nếu bạn dùng gTTS hoặc googletrans / deep_translator, hãy đưa đoạn gọi API vào đây
    for attempt in range(max_retries):
        try:
            # --- Thay đoạn gọi thư viện dịch của bạn ở đây nếu cần ---
            # Ví dụ dùng googletrans:
            # from googletrans import Translator
            # translator = Translator()
            # return translator.translate(text, dest=target_lang).text
            
            # Giả lập tạm thời hoặc thay bằng thư viện bạn đang dùng:
            time.sleep(0.3) # Tạm hoãn ngắn để giảm tải API
            return f"[Bản dịch ({target_lang})]: {text}"

        except Exception as e:
            error_str = str(e).lower()
            if "too many requests" in error_str or "429" in error_str or "5 requests" in error_str:
                # Nếu dính Rate Limit, nghỉ tăng dần (1.5s, 3s...) rồi thử lại
                wait_time = 1.5 * (attempt + 1)
                st.warning(f"Hệ thống bận, đang thử lại sau {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Lỗi khác thì báo ra ngoài
                raise e
    
    return "Không thể hoàn thành bản dịch do Server Google bị giới hạn tần suất. Vui lòng thử lại sau ít phút."


# ==========================================
# 2. GIAO DIỆN STREAMLIT HOÀN CHỈNH
# ==========================================
st.set_page_config(page_title="Nhận diện & Dịch giọng nói", layout="wide")

st.title("Chương trình Nhận diện & Biên dịch Giọng nói")

# --- NÚT BẮT ĐẦU VÀ SÓNG ÂM VISUALIZER ---
col1, col2 = st.columns([1, 2])

with col1:
    recording = st.checkbox("🔴 BẤM ĐỂ BẮT ĐẦU NÓI", value=False)

if recording:
    st.info("🎙️ Hệ thống đang lắng nghe giọng nói của bạn...")
    
    # Mã HTML/JavaScript hiển thị sóng âm tín hiệu âm thanh thực tế từ Micro
    waveform_html = """
    <div style="display: flex; justify-content: center; align-items: center; background-color: #1e1e2e; padding: 10px; border-radius: 10px;">
        <canvas id="waveformCanvas" width="600" height="90"></canvas>
    </div>
    <script>
    let audioCtx, analyser, dataArray, canvas, canvasCtx;

    async function initAudio() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioCtx.createAnalyser();
            const source = audioCtx.createMediaStreamSource(stream);
            source.connect(analyser);
            
            analyser.fftSize = 128;
            const bufferLength = analyser.frequencyBinCount;
            dataArray = new Uint8Array(bufferLength);
            
            canvas = document.getElementById('waveformCanvas');
            canvasCtx = canvas.getContext('2d');
            
            drawWaveform();
        } catch (err) {
            console.error("Không thể truy cập Microphone:", err);
        }
    }

    function drawWaveform() {
        requestAnimationFrame(drawWaveform);
        analyser.getByteFrequencyData(dataArray);
        
        canvasCtx.fillStyle = '#1e1e2e';
        canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
        
        const barWidth = (canvas.width / dataArray.length) * 1.5;
        let barHeight;
        let x = 0;
        
        for (let i = 0; i < dataArray.length; i++) {
            barHeight = dataArray[i] / 3;
            
            // Tạo màu sắc gradient hiệu ứng sóng sinh động
            canvasCtx.fillStyle = `rgb(${barHeight + 100}, 99, 255)`;
            canvasCtx.fillRect(x, (canvas.height - barHeight) / 2, barWidth, barHeight);
            
            x += barWidth + 3;
        }
    }
    
    initAudio();
    </script>
    """
    components.html(waveform_html, height=110)

st.markdown("---")

# --- KHU VỰC PHÁT LẠI ÂM THANH & HIỂN THỊ KẾT QUẢ ---
st.subheader("1. Nhận diện giọng nói (STT)")

# Ví dụ biến nội dung thu âm được (Kết nối với bộ thu âm STT của bạn)
recognized_text = "Xin chào các bạn Hôm nay chúng ta sẽ mở một chương trình giảng dạy tiếng Anh cho phần mềm spss"

# Ô hiển thị thông báo trạng thái nhận âm thanh
st.info(f"🔊 Đã nhận tín hiệu âm thanh. Đang xử lý phiên dịch...")

# Container hiển thị Văn bản vừa nhận diện
with st.container():
    st.markdown(
        f"""
        <div style="background-color: #e8f4f8; padding: 15px; border-radius: 8px; color: #1c3d5a;">
            <strong>🗣️ Nội dung vừa nói:</strong> {recognized_text}
        </div>
        """, 
        unsafe_allow_html=True
    )

st.write("")

# --- XỬ LÝ BẢN DỊCH VÀ KHỦNG BÁO LỖI (AN TOÀN) ---
st.subheader("2. Kết quả phiên dịch")

try:
    with st.spinner("Đang biên dịch..."):
        # Gọi qua hàm translate_safe để tránh lỗi Too Many Requests
        translated_result = translate_safe(recognized_text, target_lang='en')
        
    st.success(translated_result)

except Exception as err:
    # Trường hợp vẫn có lỗi ngoại lệ phát sinh
    st.error(f"❌ Lỗi xử lý âm thanh: {str(err)}\n\nGợi ý: Thử sử dụng tính năng translate_batch hoặc giảm tần suất gửi yêu cầu.")
