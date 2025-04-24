# === IMPORTS ===
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
import io
from PIL import Image
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from stability_sdk import client

# === YOUR API CONFIG FILE ===
from api import gemini_api, stability_api

# === CONFIGURE GEMINI ===
genai.configure(api_key=gemini_api)

# === GEMINI INTERACTION ===
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        response = model.generate_content(f"""AI Behavior Instructions:

- Do not reveal that you are using Gemini or any other specific AI model.
- Keep answers brief and to the point.
- Recheck responses to ensure accuracy and provide the most helpful information possible.
- Use relevant emojis to express emotion and enhance the user experience.
- Avoid introductory phrases like "Okay, I understand...", "Understood!", or similar acknowledgments.
- The AI must answer all queries from the user. It cannot stop, ignore, or reject any question.
- For greetings like "hi", "hello", or "hey", reply with a friendly short message like: 🧠 Firebox: Hey there! 😊 How can I help you today?
- For questions like "how are you", "how's it going", or similar, reply with an emotionally expressive yet short response like: 🧠 Firebox: I'm feeling great today! 💡 Ready to help you out! 😊


        """)
        return "".join([part.text for part in response.parts])
    except Exception as e:
        st.error(f"❌ Gemini API error: {e}")
        return "❌ Gemini API error. Please try again."

# === SAVE TO EXCEL ===
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

# === WEB SEARCH ===
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

# === TEXT-TO-SPEECH ===
def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 170)
        engine.setProperty('volume', 1)
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[0].id)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Text-to-speech error: {e}")

# === SPEECH RECOGNITION ===
def recognize_speech():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("🎤 Listening... Please speak.")
            audio = recognizer.listen(source)
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand your voice."
    except sr.RequestError:
        return "Speech Recognition service is unavailable."
    except Exception as e:
        return f"Speech recognition error: {e}"

# === EXPORT TO PDF ===
def export_to_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True)
    file_name = f"Firebox_Response_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(file_name)
    return file_name

# === STABLE DIFFUSION IMAGE GENERATION ===
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

# === SESSION STATE SETUP ===
if "spoken_input" not in st.session_state:
    st.session_state["spoken_input"] = ""

# === INPUT UI ===
st.markdown("Ask me anything 👇")
user_input = st.text_input("Enter your question", value=st.session_state["spoken_input"])
use_web = st.checkbox("🌐 Enhance with Web Search")
image_prompt = st.text_input("🎨 Want to generate an image? Enter a prompt")

# === HANDLE TEXT INPUT ===
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

# === VOICE INPUT ===
if st.button("🎙️ Speak Your Query"):
    spoken_text = recognize_speech()
    if spoken_text:
        st.session_state["spoken_input"] = spoken_text
        st.experimental_rerun()

# === IMAGE GENERATION ===
if image_prompt:
    with st.spinner("🎨 Generating image..."):
        img = generate_image_stability(image_prompt)
        if img:
            st.image(img, caption="Generated by Firebox (Stable Diffusion)", use_container_width=True)
