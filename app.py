import streamlit as st
import requests
import base64
import fitz  # PyMuPDF
from PIL import Image
import io

# הגדרות דף
st.set_page_config(page_title="פענוח כתב יד", layout="centered")

st.markdown("""
<style>
    .paper-sheet {
        background-color: white; padding: 35px; border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); direction: rtl; text-align: right;
        font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 20px; line-height: 1.8;
        white-space: pre-wrap; color: #1a1a1a; border: 1px solid #ddd;
    }
    .stButton>button { width: 100%; background-color: #1a73e8; color: white; border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("📝 מפענח כתב יד מקצועי")
st.write("העלה קובץ וההמרה תתחיל מיד")

api_key = st.sidebar.text_input("מפתח Google API:", type="password")

if not api_key:
    st.info("👈 אנא הכנס את המפתח שלך בתפריט הצד")
    st.stop()

def get_text_from_gemini(base64_image, key):
    # חיבור ישיר לשרת של גוגל - עוקף את כל שגיאות ה-404
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [
                {"text": "Transcribe the handwritten text in this image accurately. If it is in Hebrew, write in Hebrew. Return ONLY the text with original line breaks."},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}
            ]
        }]
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        return f"שגיאה בשרת: {response.text}"

uploaded_file = st.file_uploader("בחר קובץ (PDF/JPG/PNG)", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    with st.status("מעבד את המסמך...", expanded=True) as status:
        try:
            full_text = ""
            images_data = []
            
            # המרת הקובץ לתמונות
            if uploaded_file.type == "application/pdf":
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    images_data.append(base64.b64encode(pix.tobytes("jpg")).decode('utf-8'))
            else:
                img_bytes = uploaded_file.read()
                images_data.append(base64.b64encode(img_bytes).decode('utf-8'))

            # פענוח
            status.write("🧠 מנתח את הכתב...")
            for img_b64 in images_data:
                full_text += get_text_from_gemini(img_b64, api_key) + "\n\n"

            status.update(label="הפענוח הושלם!", state="complete", expanded=False)
            
            st.subheader("התוצאה:")
            st.markdown(f'<div class="paper-sheet">{full_text}</div>', unsafe_allow_html=True)
            st.download_button("📥 הורד קובץ טקסט", full_text, file_name="decoded_text.txt")

        except Exception as e:
            st.error(f"שגיאה: {str(e)}")
