import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io

# הגדרות דף
st.set_page_config(page_title="פענוח כתב יד", layout="centered")

st.markdown("""
<style>
    .paper-sheet {
        background-color: white; padding: 35px; border-radius: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); direction: rtl; text-align: right;
        font-family: 'David', sans-serif; font-size: 20px; line-height: 1.6;
        white-space: pre-wrap; color: #1a1a1a; border: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔎 פענוח כתב יד מקצועי")

api_key = st.sidebar.text_input("Google API Key:", type="password")

if not api_key:
    st.warning("👈 הכנס מפתח API בתפריט הצד כדי להתחיל")
    st.stop()

# פונקציה להפעלת המודל בצורה בטוחה
def process_with_gemini(image_list, key):
    genai.configure(api_key=key)
    # שימוש בגרסה היציבה ביותר בלבד
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    combined_results = ""
    for img in image_list:
        response = model.generate_content([
            "Read this handwritten text in Hebrew and transcribe it accurately. Return only the text.",
            img
        ])
        combined_results += response.text + "\n\n"
    return combined_results

uploaded_file = st.file_uploader("העלה צילום כתב יד או PDF", type=["jpg", "png", "jpeg", "pdf"])

if uploaded_file:
    with st.status("מנתח את המסמך...", expanded=True) as status:
        try:
            images = []
            if uploaded_file.type == "application/pdf":
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
            else:
                images.append(Image.open(uploaded_file))

            # הפעלה
            result_text = process_with_gemini(images, api_key)
            
            status.update(label="הפענוח הסתיים!", state="complete", expanded=False)
            st.markdown(f'<div class="paper-sheet">{result_text}</div>', unsafe_allow_html=True)
            st.download_button("📥 הורד טקסט", result_text, file_name="output.txt")

        except Exception as e:
            # כאן הקוד ינסה להסביר מה הבעיה אם היא תקרה שוב
            if "404" in str(e):
                st.error("שגיאת חיבור (404): נסה לרענן את האפליקציה דרך Manage App -> Reboot")
            else:
                st.error(f"התגלתה שגיאה: {str(e)}")
