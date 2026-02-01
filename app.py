import streamlit as st
from openai import OpenAI
import base64
import fitz  # PyMuPDF
import io

# הגדרת הדף
st.set_page_config(page_title="ממיר כתב יד", layout="centered")

# עיצוב מיוחד למסמך - נראה כמו דף נייר
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .paper-sheet {
        background-color: white;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 18px;
        line-height: 1.6;
        white-space: pre-wrap; /* שומר על ירידות שורה */
        color: #000000;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📄 המרת כתב יד לטקסט")
st.markdown("---")

# תפריט צד למפתח
api_key = st.sidebar.text_input("מפתח OpenAI API:", type="password")
if not api_key:
    st.warning("נא להזין מפתח API בתפריט הצד")
    st.stop()

client = OpenAI(api_key=api_key)

uploaded_file = st.file_uploader("בחר קובץ (PDF או תמונה)", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    # הצגת הודעת טעינה יפה
    with st.status("מעבד את הקובץ...", expanded=True) as status:
        try:
            full_text = ""
            images = []
            
            # שלב 1: המרת הקובץ לתמונות
            status.write("🔍 סורק את הדפים...")
            if uploaded_file.type == "application/pdf":
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                for i in range(len(doc)):
                    page = doc.load_page(i)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    images.append(pix.tobytes("jpg"))
            else:
                images.append(uploaded_file.read())

            # שלב 2: שליחה ל-AI
            status.write("🤖 מפענח כתב יד...")
            progress_bar = st.progress(0)
            
            for idx, img_data in enumerate(images):
                base64_img = base64.b64encode(img_data).decode('utf-8')
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Transcribe the handwritten text exactly as it appears. Keep line breaks. Return ONLY the text."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                            ]
                        }
                    ]
                )
                full_text += response.choices[0].message.content + "\n\n"
                progress_bar.progress((idx + 1) / len(images))

            status.update(label="הפענוח הושלם!", state="complete", expanded=False)

            # הצגת התוצאה כ"דף נייר"
            st.subheader("תוצאה:")
            st.markdown(f'<div class="paper-sheet">{full_text}</div>', unsafe_allow_html=True)
            
            st.write("") # רווח
            
            # כפתור הורדה
            st.download_button(
                label="📥 הורד את הטקסט למחשב",
                data=full_text,
                file_name="result.txt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"התרחשה שגיאה: {e}")
