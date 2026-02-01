import streamlit as st
from openai import OpenAI
import base64
import fitz  # PyMuPDF
from PIL import Image
import io

# הגדרות עיצוב לממשק
st.set_page_config(page_title="ממיר כתב יד מקצועי", layout="wide")
st.title("📄 OCR מקצועי: מכתב יד לטקסט מוקלד")
st.markdown("---")

# הזנת מפתח API
api_key = st.sidebar.text_input("הכנס מפתח OpenAI API:", type="password")
if not api_key:
    st.info("נא להזין מפתח API בתפריט הצד כדי להתחיל.")
    st.stop()

client = OpenAI(api_key=api_key)

# העלאת קבצים
uploaded_file = st.file_uploader("בחר קובץ תמונה או PDF (תומך במספר דפים)", type=["jpg", "jpeg", "png", "pdf"])

if uploaded_file:
    all_text = ""
    
    if st.button("התחל פענוח (OCR)"):
        with st.spinner('מעבד דפים... נא להמתין'):
            try:
                images_to_process = []
                
                # אם זה PDF - הופך את כל הדפים לתמונות
                if uploaded_file.type == "application/pdf":
                    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                    for i in range(len(doc)):
                        page = doc.load_page(i)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # איכות גבוהה יותר
                        images_to_process.append(pix.tobytes("jpg"))
                else:
                    # אם זה תמונה רגילה
                    images_to_process.append(uploaded_file.read())

                # לופ על כל הדפים שנמצאו
                progress_bar = st.progress(0)
                for index, img_data in enumerate(images_to_process):
                    base64_image = base64.b64encode(img_data).decode('utf-8')
                    
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Please transcribe the handwritten text in this image. Keep the format natural. If it is in Hebrew, transcribe it accurately."},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ],
                            }
                        ],
                    )
                    
                    page_content = response.choices[0].message.content
                    all_text += f"--- דף {index + 1} ---\n{page_content}\n\n"
                    progress_bar.progress((index + 1) / len(images_to_process))

                st.success("הפענוח הסתיים בהצלחה!")

            except Exception as e:
                st.error(f"שגיאה בתהליך: {e}")

    # תצוגת תוצאות וכלים
    if all_text:
        st.subheader("הטקסט שחולץ:")
        st.text_area("תוצאה:", value=all_text, height=400, id="main_text")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # כפתור העתקה (זמין בגרסאות חדשות של Streamlit)
            if hasattr(st, "copy_to_clipboard"):
                st.copy_to_clipboard(all_text)
                st.info("הטקסט הועתק ללוח!")
            else:
                st.write("ניתן לסמן את הטקסט למעלה ולהעתיק (Ctrl+C)")

        with col2:
            # כפתור הורדה כקובץ TXT
            st.download_button(
                label="📥 הורד כקובץ TXT",
                data=all_text,
                file_name="transcription.txt",
                mime="text/plain"
            )
