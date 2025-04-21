# Firebox AI: Cleanest Version – No Login, No History, No Tracking

import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import datetime
from fpdf import FPDF
import pandas as pd
import os
import io
from PIL import Image
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from stability_sdk import client
import platform

# Conditional imports for voice modules
enable_voice = platform.system() == "Windows"

if enable_voice:
    try:
        import pyttsx3
        import speech_recognition as sr
    except ImportError:
        enable_voice = False
        st.warning("Voice modules not installed or unsupported on this system.")

# Import your local API keys
import api
from api import gemini_api, stability_api

# === CONFIG ===
genai.configure(api_key=gemini_api)

# --- Gemini Interaction ---
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        response = model.generate_content(f"""You are Firebox, a helpful AI assistant. 
        Respond briefly, clearly, and positively, use emojies to add feeling to:
        {prompt}
        , and always also try to give better response than the before answer""")
        return response.text
    except Exception as e:
        st.error(f"❌ Gemini API error: {e}")
        return "❌ Gemini API error. Please try again."

# --- Save Input to Excel ---
def save_input_to_excel(user_input):
    file_name = "firebox_inputs.xlsx"
    new_data = {"Timestamp": [datetime.datetime.now()], "User Input": [user_input]}
    new_df = pd.DataFrame(new_data)

    if os.path.exists(file_name):
        existing_df = pd.read_excel(file_name)
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    updated_df.to_excel(file_name, index=False)

# --- Web Search ---
def search_web(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://www.google.com/search?q={query}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        snippets = soup.select('div.BNeawe.s3v9rd.AP7Wnd')
        results = [s.get_text() for s in snippets[:3]]
        return "\n\n🌐 Web Search Results:\n" + "\n".join(results) if results else "No web results found."
    except Exception as e:
        return f"❌ Web search failed: {e}"

# --- Text-to-Speech ---
def speak_text(text):
    if not enable_voice:
        st.warning("Text-to-Speech is not supported on this platform.")
        return
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# --- Speech Recognition ---
def recognize_speech():
    if not enable_voice:
        st.warning("Speech Recognition is not supported on this platform.")
        return "Speech recognition is disabled."
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Speak now...")
        try:
            audio = recognizer.listen(source)
            return recognizer.recognize_google(audio)
        except:
            return "Sorry, I couldn't understand."

# --- PDF Export ---
def export_to_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True)
    file_name = f"Firebox_Response_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(file_name)
    return file_name

# --- Image Generation with Stability AI ---
def generate_image_stability(prompt):
    stability_api_client = client.StabilityInference(
        key=stability_api,
        verbose=True,
    )
    answers = stability_api_client.generate(prompt=prompt, steps=30, width=512, height=512)
    for resp in answers:
        for artifact in resp.artifacts:
            if artifact.finish_reason == generation.FILTER:
                st.warning("⚠️ Prompt was filtered for safety.")
                return None
            if artifact.type == generation.ARTIFACT_IMAGE:
                image = Image.open(io.BytesIO(artifact.binary))
                return image
    return None

# === STREAMLIT APP ===
st.set_page_config(page_title="Firebox AI", page_icon="🔥", layout="wide")
st.title("🔥 Firebox AI – Pure Mode")

# Input Section
st.markdown("Ask me anything 👇")
user_input = st.text_input("Enter your question")
use_web = st.checkbox("🌐 Enhance with Web Search")
image_prompt = st.text_input("🎨 Want to generate an image? Enter a prompt")

# Text Answer
if user_input:
    with st.spinner("Thinking..."):
        save_input_to_excel(user_input)
        gemini_response = call_firebox_gemini(user_input)
        web_results = search_web(user_input) if use_web else ""
        full_response = gemini_response + ("\n\n" + web_results if web_results else "")
        st.success("✅ Response Generated!")
        st.markdown(f"**🧠 Firebox**: {full_response}")

        if st.button("🔊 Speak"):
            speak_text(full_response)
        if st.button("📄 Export as PDF"):
            pdf_file = export_to_pdf(full_response)
            st.success(f"PDF saved as {pdf_file}")

# Voice Input
if st.button("🎙️ Speak Your Query") and enable_voice:
    spoken_text = recognize_speech()
    if spoken_text:
        st.text_input("Spoken Input", value=spoken_text, key="spoken_input")

# Image Generation
if image_prompt:
    with st.spinner("🎨 Generating image..."):
        img = generate_image_stability(image_prompt)
        if img:
            st.image(img, caption="Generated by Firebox (Stable Diffusion)", use_container_width=True)
