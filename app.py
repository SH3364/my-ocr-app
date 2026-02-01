import streamlit as st
from openai import OpenAI
import base64
import fitz  # PyMuPDF
from PIL import Image
import io

# הגדרות עיצוב RTL ועברית
st.set_page_config(page_title="ממיר כתב יד", layout="centered")
st.markdown("""
    <style>
    .main { direction: rtl; text-align: right; }
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stTextArea textarea { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

st.title("📝 המרת כתב יד לטקסט")
st.write("העלה קובץ וההמרה תתחיל באופן אוטומטי")

# מפתח API - הגדר בתפריט הצד
api_key = st.sidebar.text_input("מפתח OpenAI API:", type="password")

if not api_key:
    st.warning("👈 נא להזין מפתח API בתפריט הצד")
    st.stop()

client = OpenAI(api_key=api_key)

# העלאת קובץ
uploaded_file = st.file_uploader("בחר תמונה או PDF", type=["jpg", "jpeg", "png", "pdf"])

# המרה אוטומטית ברגע שיש קובץ
if uploaded_file:
    all_text = ""
    with st.spinner('מפענח את הכתב... נא להמתין'):
        try:
            images_to_process = []
            if uploaded_file.type == "application/pdf":
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                for i in range(len(doc)):
                    page = doc.load_page(i)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    images_to_process.append(pix.tobytes("jpg"))
            else:
                images_to_process.append(uploaded_file.read())

            for index, img_data in enumerate(images_to_process):
                base64_image = base64.b64encode(img_data).decode('utf-8')
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "transcribe the handwritten text in this image. if it is in Hebrew, write it in Hebrew accurately. return ONLY the text."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ],
                        }
                    ],
                )
                all_text += response.choices[0].message.content + "\n\n"

            st.success("הפענוח הסתיים!")
            
            # הצגת הטקסט (ללא ה-id שגרם לשגיאה)
            st.text_area("הטקסט שחולץ:", value=all_text, height=300)
            
            # כפתורי פעולה
            col1, col2 = st.columns(2)
            with col1:
                st.download_button("📥 הורד קובץ TXT", all_text, file_name="output.txt")
            with col2:
                st.info("לחיצה ימנית על הטקסט לבחירה והעתקה")

        except Exception as e:
            st.error(f"שגיאה: {str(e)}")
