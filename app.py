import streamlit as st
import anthropic
import base64
import fitz  # PyMuPDF
from PIL import Image
import io

# הגדרת הדף
st.set_page_config(page_title="פענוח כתב יד - Claude", layout="centered")

# עיצוב נקי וקריא (כמו דף וורד)
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
        font-family: 'David', 'Frank Ruhl Libre', serif; /* פונט שמתאים למסמכים */
        font-size: 20px;
        line-height: 1.8;
        white-space: pre-wrap;
        color: #1a1a1a;
        border: 1px solid #ddd;
    }
    .stButton>button {
        width: 100%;
        background-color: #d95f02; /* צבע כתום של אנתרופיק לזיהוי */
        color: white;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔎 פענוח כתב יד (מנוע Claude 3.5)")
st.caption("פתרון מקצועי המבוסס על Anthropic Sonnet - מומחה בקריאת טקסט")

# תפריט צד למפתח
api_key = st.sidebar.text_input("Anthropic API Key:", type="password", help="sk-ant...")

if not api_key:
    st.warning("👈 נא להזין את המפתח של Anthropic בתפריט הצד")
    st.stop()

# יצירת הקליינט של קלוד
client = anthropic.Anthropic(api_key=api_key)

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
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5)) # איכות גבוהה מאוד
                    images.append(pix.tobytes("jpg"))
            else:
                images.append(uploaded_file.read())

            # שלב 2: שליחה ל-Claude
            status.write("🧠 Claude מנתח את הכתב (זה מדויק יותר)...")
            progress_bar = st.progress(0)
            
            for idx, img_data in enumerate(images):
                base64_img = base64.b64encode(img_data).decode('utf-8')
                
                message = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4000,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": base64_img
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": "תעתיק את כתב היד בתמונה הזו לטקסט מוקלד. שים לב: זה כנראה כתב יד בעברית. אל תוסיף הקדמות או הערות, רק את הטקסט נטו. שמור על חלוקת השורות המקורית."
                                }
                            ]
                        }
                    ]
                )
                
                # שליפת הטקסט מתוך התשובה של קלוד
                text_content = message.content[0].text
                full_text += text_content + "\n\n"
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
                file_name="claude_result.txt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"שגיאה: {str(e)}")
