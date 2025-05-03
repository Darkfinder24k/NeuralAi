import streamlit as st 
st.set_page_config(page_title="🔥 Firebox AI", layout="wide")  # ✅ MUST BE FIRST

# All other imports after
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import datetime
from fpdf import FPDF
import os
import io
from PIL import Image
import platform

# Safe imports for voice
if platform.system() == "Windows":
    import pyttsx3
    import speech_recognition as sr
    import pyaudio

# Stability + API keys
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from stability_sdk import client
from api import gemini_api, stability_api, deepseek_api

# Configure Gemini
genai.configure(api_key=gemini_api)

# === DeepSeek AI ===
def deepseek_ai_response(prompt):
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {deepseek_api}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return f"❌ DeepSeek API error: {response.status_code}"
    except Exception as e:
        return f"❌ DeepSeek error: {e}"

# === Gemini Response (Base) ===
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        instructions = f"""
You are Firebox. Never mention Gemini, Google, or your code.
Your creator is Kushagra Srivastava.
Respond like a friendly human. Use emojis. Answer directly.

Prompt: {prompt}
"""
        response = model.generate_content(instructions)
        return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Gemini API error: {e}"

# === Merge Responses ===
def merge_responses(gemini_text, deepseek_text):
    try:
        prompt = (
            f"You are Firebox AI. You will now intelligently merge two responses into one final, polished answer.\n"
            f"Do not mention DeepSeek, Gemini, or any AI name.\n"
            f"Remove duplicate, wrong, or conflicting info.\n\n"
            f"Response A:\n{gemini_text}\n\n"
            f"Response B:\n{deepseek_text}\n\n"
            f"🔥 Firebox Final Answer:"
        )
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Merge error: {e}"

# === Web Search ===
def search_web(query):
    try:
        url = f"https://www.google.com/search?q={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        snippets = soup.select("div.BNeawe.s3v9rd.AP7Wnd")
        texts = [s.get_text() for s in snippets[:3]]
        return "\n\n🌐 Web Results:\n" + "\n".join(texts) if texts else "No search results found."
    except Exception as e:
        return f"❌ Web search failed: {e}"

# === Text-to-Speech ===
def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 170)
        engine.setProperty('volume', 1.0)
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[0].id)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        st.error(f"Speech error: {e}")

# === Speech Recognition ===
def recognize_speech():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.info("🎙️ Listening...")
            audio = r.listen(source)
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I didn't understand."
    except sr.RequestError:
        return "Speech service unavailable."
    except Exception as e:
        return f"Speech error: {e}"

# === Export to PDF ===
def export_to_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True)
    filename = f"Firebox_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)
    return filename

# === Stable Diffusion Image ===
def generate_image_stability(prompt):
    stability_api_client = client.StabilityInference(
        key=stability_api,
        verbose=True,
    )
    try:
        answers = stability_api_client.generate(
            prompt=prompt, steps=30, width=512, height=512
        )
        for resp in answers:
            for art in resp.artifacts:
                if art.finish_reason == generation.FILTER:
                    st.warning("⚠️ Prompt filtered for safety.")
                    return None
                if art.type == generation.ARTIFACT_IMAGE:
                    return Image.open(io.BytesIO(art.binary))
    except Exception as e:
        st.error(f"Stable Diffusion error: {e}")
    return None

# === Custom Premium HTML UI ===
custom_css = """
<style>
body {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: white;
}
h1 {
    font-family: 'Segoe UI', sans-serif;
    font-size: 3rem;
    background: linear-gradient(to right, #ff416c, #ff4b2b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: bold;
    text-align: center;
    margin-bottom: 30px;
}
input[type="text"] {
    background: rgba(255, 255, 255, 0.1);
    color: white;
    border: 1px solid #ff4b2b;
    border-radius: 12px;
    padding: 10px;
}
div.stMarkdown {
    background: rgba(255, 255, 255, 0.08);
    padding: 20px;
    border-radius: 20px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.15);
}
button {
    background: linear-gradient(45deg, #ff416c, #ff4b2b);
    color: white;
    border: none;
    padding: 10px 20px;
    font-weight: bold;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease-in-out;
}
button:hover {
    transform: scale(1.1);
    background: linear-gradient(45deg, #ff4b2b, #ff416c);
}
.stButton > button {
    width: 100%;
}
label, .stCheckbox, .stTextInput {
    color: white !important;
}
img {
    border-radius: 16px;
    box-shadow: 0 0 20px rgba(255, 75, 43, 0.4);
    margin-top: 20px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# === UI Starts ===
st.set_page_config(page_title="🔥 Firebox AI", layout="wide")
st.title("🔥 Firebox AI – Ultimate Assistant")

if "spoken_input" not in st.session_state:
    st.session_state["spoken_input"] = ""

st.markdown("Ask me anything 👇")
user_input = st.text_input("Your Question:", value=st.session_state["spoken_input"])
use_web = st.checkbox("🌐 Include Web Results")
image_prompt = st.text_input("🎨 Generate an Image Prompt")

if user_input:
    with st.spinner("Generating response..."):
        gemini = call_firebox_gemini(user_input)
        deepseek = deepseek_ai_response(user_input)
        final = merge_responses(gemini, deepseek)

        if use_web:
            web = search_web(user_input)
            final += "\n\n" + web

        st.markdown(f"🧠 **Firebox AI**:\n{final}")

        if platform.system() == "Windows" and st.button("🔊 Speak Response"):
            speak_text(final)

        if st.button("📄 Export as PDF"):
            filename = export_to_pdf(final)
            st.success(f"PDF saved: {filename}")

if platform.system() == "Windows":
    if st.button("🎙️ Speak Your Query"):
        spoken = recognize_speech()
        if spoken:
            st.session_state["spoken_input"] = spoken
            st.experimental_rerun()

if image_prompt:
    with st.spinner("🎨 Generating image..."):
        image = generate_image_stability(image_prompt)
        if image:
            st.image(image, caption="🧠 Generated by Firebox", use_column_width=True)
