import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io

# הגדרת הדף
st.set_page_config(page_title="פענוח כתב יד - Gemini", layout="centered")

# עיצוב דף נקי
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .paper-sheet {
        background-color: white;
        padding: 40px;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        direction: rtl;
        text-align: right;
        font-family: 'David', 'Frank Ruhl Libre', serif;
        font-size: 20px;
        line-height: 1.8;
        white-space: pre-wrap;
        color: #1a1a1a;
        border: 1px solid #ddd;
    }
    .stButton>button {
        width: 100%;
        background-color: #4285F4;
        color: white;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔎 פענוח כתב יד (חינם - Gemini)")

# הזנת מפתח
api_key = st.sidebar.text_input("Google API Key:", type="password", help="AIza...")

if not api_key:
    st.warning("👈 נא להזין מפתח Google API בתפריט הצד")
    st.stop()

# הגדרת המודל - גרסה מעודכנת
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
except Exception as e:
    st.error(f"שגיאה בהגדרת המודל: {e}")

uploaded_file = st.file_uploader("בחר קובץ (PDF או תמונה)", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    with st.status("מעבד את המסמך...", expanded=True) as status:
        try:
            full_text = ""
            images = []
            
            # שלב 1: המרה לתמונות
            status.write("📄 מפרק את הקובץ לדפים...")
            if uploaded_file.type == "application/pdf":
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                for i in range(len(doc)):
                    page = doc.load_page(i)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
                    img_data = pix.tobytes("png")
                    images.append(Image.open(io.BytesIO(img_data)))
            else:
                images.append(Image.open(uploaded_file))

            # שלב 2: שליחה לגוגל
            status.write("🧠 Gemini מנתח את הכתב...")
            progress_bar = st.progress(0)
            
            for idx, img in enumerate(images):
                # בקשה ספציפית לדיוק בעברית
                response = model.generate_content([
                    "Please transcribe this handwritten text into digital text. The text is in Hebrew. Be as accurate as possible and maintain the original line breaks. Return ONLY the transcribed text.",
                    img
                ])
                
                full_text += response.text + "\n\n"
                progress_bar.progress((idx + 1) / len(images))

            status.update(label="הפענוח הושלם!", state="complete", expanded=False)

            # הצגת התוצאה
            st.subheader("הטקסט שפוענח:")
            st.markdown(f'<div class="paper-sheet">{full_text}</div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # הורדה
            st.download_button(
                label="📥 הורד קובץ TXT",
                data=full_text,
                file_name="gemini_result.txt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"שגיאה בתהליך: {str(e)}")
