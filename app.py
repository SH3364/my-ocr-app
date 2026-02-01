import streamlit as st
import requests
import base64

st.set_page_config(page_title="מפענח כתב יד", layout="centered")

st.title("📝 פענוח כתב יד (גרסת תיקון)")

api_key = st.sidebar.text_input("הכנס מפתח גוגל:", type="password")
uploaded_file = st.file_uploader("העלה תמונה", type=["jpg", "png", "jpeg"])

if uploaded_file and api_key:
    # המרת התמונה לבייס 64
    img_b64 = base64.b64encode(uploaded_file.read()).decode('utf-8')
    
    # כתובת חלופית לשרת של גוגל
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": "Transcribe this Hebrew handwriting. Return only the text."},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]
        }]
    }
    
    if st.button("פענח עכשיו"):
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()['candidates'][0]['content']['parts'][0]['text']
            st.text_area("הטקסט שזוהה:", value=result, height=300)
        else:
            st.error(f"שגיאה: {response.text}")
