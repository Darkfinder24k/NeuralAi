import streamlit as st
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
from api import gemini_api, stability_api

# Configure Gemini
genai.configure(api_key=gemini_api)

# === LLaMA AI (via AIMLAPI) ===
def llama_ai_response(prompt):
    url = "https://api.aimlapi.com/v1/chat/completions"
    headers = {
        "Authorization": "Bearer e5b7931e7e214e1eb43ba7182d7a2176",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        try:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception:
            return "⚠️ Couldn't parse LLaMA response."
    return f"❌ LLaMA API error: {response.status_code}"

# === Gemini Response ===
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

# === UI Starts ===
st.set_page_config(page_title="🔥 Firebox AI", layout="wide")
st.title("🔥 Firebox AI – Ultimate Assistant")

if "spoken_input" not in st.session_state:
    st.session_state["spoken_input"] = ""

# Input UI
st.markdown("Ask me anything 👇")
user_input = st.text_input("Your Question:", value=st.session_state["spoken_input"])
use_web = st.checkbox("🌐 Include Web Results")
image_prompt = st.text_input("🎨 Generate an Image Prompt")

# Handle Main Logic
if user_input:
    with st.spinner("Generating response..."):
        gemini = call_firebox_gemini(user_input)
        llama = llama_ai_response(user_input)
        full_response = f"🧠 **Firebox (Gemini)**:\n{gemini}\n\n🦙 **LLaMA AI**:\n{llama}"
        if use_web:
            web = search_web(user_input)
            full_response += "\n\n" + web

        st.markdown(full_response)

        # Speak
        if platform.system() == "Windows":
            if st.button("🔊 Speak Response"):
                speak_text(full_response)

        # Export
        if st.button("📄 Export as PDF"):
            filename = export_to_pdf(full_response)
            st.success(f"PDF saved: {filename}")

# Voice Input
if platform.system() == "Windows":
    if st.button("🎙️ Speak Your Query"):
        spoken = recognize_speech()
        if spoken:
            st.session_state["spoken_input"] = spoken
            st.experimental_rerun()

# Image Generation
if image_prompt:
    with st.spinner("🎨 Generating image..."):
        image = generate_image_stability(image_prompt)
        if image:
            st.image(image, caption="🧠 Generated by Firebox", use_column_width=True)
