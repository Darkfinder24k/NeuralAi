# Firebox AI: Cleanest Version – No Login, No History, No Tracking

import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import datetime
from fpdf import FPDF
import pyttsx3
import speech_recognition as sr
import pandas as pd
import os
import api
from api import gemini_api

# === CONFIG ===
genai.configure(api_key=gemini_api)

# --- Gemini Interaction ---
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        response = model.generate_content(f"""You are Firebox, a helpful AI assistant. 
        Respond briefly, clearly, and positively to:
        {prompt}
        """)
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

# --- Web Search (optional feature) ---
def search_web(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://www.google.com/search?q={query}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        snippets = soup.select('div.BNeawe.s3v9rd.AP7Wnd')
        results = [s.get_text() for s in snippets[:3]]
        return "\n\n🌐 Web Search Results:\n" + "\n".join(results) if results else "No web results."
    except Exception as e:
        return f"❌ Web search failed: {e}"

# --- Text-to-Speech ---
def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# --- Speech Recognition ---
def recognize_speech():
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

# === STREAMLIT APP ===
st.set_page_config(page_title="Firebox AI", page_icon="🔥", layout="wide")
st.title("🔥 Firebox AI – Pure Mode")

# Input Section
st.markdown("Ask me anything 👇")
user_input = st.text_input("Enter your question")

if user_input:
    with st.spinner("Thinking..."):
        response = call_firebox_gemini(user_input)
        save_input_to_excel(user_input)  # ✅ Save the input to Excel
        st.success("✅ Response Generated!")
        st.markdown(f"**🧠 Firebox**: {response}")
        if st.button("🔊 Speak"):
            speak_text(response)
        if st.button("📄 Export as PDF"):
            pdf_file = export_to_pdf(response)
            st.success(f"PDF saved as {pdf_file}")

# Optional: Speak Input
if st.button("🎙️ Speak Your Query"):
    spoken_text = recognize_speech()
    if spoken_text:
        st.text_input("Spoken Input", value=spoken_text, key="spoken_input")
