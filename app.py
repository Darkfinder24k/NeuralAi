# Firebox AI: Ultimate Version – Clean, Private, with AI Video Shorts

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
from PIL import Image
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
import api
from api import gemini_api

# === CONFIG ===
genai.configure(api_key=gemini_api)

# === Firebox Gemini Interaction ===
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        response = model.generate_content(f"""You are Firebox, a helpful AI assistant. 
        Respond briefly, clearly, and positively to:
        {prompt}
        """)
        return response.text
    except Exception as e:
        st.error(f"\u274c Gemini API error: {e}")
        return "\u274c Gemini API error. Please try again."

# === Save User Input to Excel ===
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

# === Web Search ===
def search_web(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://www.google.com/search?q={query}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        snippets = soup.select('div.BNeawe.s3v9rd.AP7Wnd')
        results = [s.get_text() for s in snippets[:3]]
        return "\n\n\ud83c\udf10 Web Search Results:\n" + "\n".join(results) if results else "No web results."
    except Exception as e:
        return f"\u274c Web search failed: {e}"

# === Text-to-Speech ===
def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# === Speech Recognition ===
def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("\ud83c\udfa4 Speak now...")
        try:
            audio = recognizer.listen(source)
            return recognizer.recognize_google(audio)
        except:
            return "Sorry, I couldn't understand."

# === PDF Export ===
def export_to_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True)
    file_name = f"Firebox_Response_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(file_name)
    return file_name

# === Resize Images to Vertical Format ===
def resize_to_vertical(image_path, target_height=1080):
    img = Image.open(image_path)
    aspect_ratio = 9 / 16
    new_width = int(target_height * aspect_ratio)
    img = img.resize((new_width, target_height))
    temp_path = f"resized_{os.path.basename(image_path)}"
    img.save(temp_path)
    return temp_path

# === Generate Vertical Shorts Video ===
def generate_vertical_short_video(image_paths, text, bg_music_path=None, output_file="firebox_short.mp4"):
    clips = []
    for img_path in image_paths:
        resized = resize_to_vertical(img_path)
        img_clip = ImageClip(resized).set_duration(3)
        text_clip = TextClip(text, fontsize=40, color='white', font="Arial-Bold", bg_color="black", size=img_clip.size)
        text_clip = text_clip.set_duration(3).set_position("bottom")
        final = CompositeVideoClip([img_clip, text_clip])
        clips.append(final)

    final_video = concatenate_videoclips(clips, method="compose")

    if bg_music_path:
        audio = AudioFileClip(bg_music_path).subclip(0, final_video.duration)
        final_video = final_video.set_audio(audio)

    final_video.write_videofile(output_file, fps=24)
    return output_file

# === Streamlit UI ===
st.set_page_config(page_title="Firebox AI", page_icon="\ud83d\udd25", layout="wide")

st.title("\ud83d\udd25 Firebox AI – Ultimate Mode")
st.markdown("Ask me anything \ud83d\udc47")
user_input = st.text_input("Enter your question")

if user_input:
    with st.spinner("Thinking..."):
        response = call_firebox_gemini(user_input)
        save_input_to_excel(user_input)
        st.success("\u2705 Response Generated!")
        st.markdown(f"**\ud83e\udde0 Firebox**: {response}")

        if st.button("\ud83d\udd0a Speak"):
            speak_text(response)
        if st.button("\ud83d\udcc4 Export as PDF"):
            pdf_file = export_to_pdf(response)
            st.success(f"PDF saved as {pdf_file}")

# === Optional: Speech Input ===
if st.button("\ud83c\udfa4 Speak Your Query"):
    spoken_text = recognize_speech()
    if spoken_text:
        st.text_input("Spoken Input", value=spoken_text, key="spoken_input")

# === Video Generation ===
st.markdown("### \ud83c\udfac Generate YouTube Shorts-style Video")
uploaded_images = st.file_uploader("Upload Images", accept_multiple_files=True, type=["png", "jpg", "jpeg"])
uploaded_music = st.file_uploader("Upload Background Music (mp3)", type=["mp3"])

if uploaded_images and response:
    image_paths = []
    os.makedirs("uploads", exist_ok=True)
    for img in uploaded_images:
        path = f"uploads/{img.name}"
        with open(path, "wb") as f:
            f.write(img.read())
        image_paths.append(path)

    music_path = None
    if uploaded_music:
        music_path = f"uploads/{uploaded_music.name}"
        with open(music_path, "wb") as f:
            f.write(uploaded_music.read())

    if st.button("\ud83d\ude80 Create Vertical Short Video"):
        output_video = generate_vertical_short_video(image_paths, response, music_path)
        st.video(output_video)
        st.success(f"Video saved as {output_video}")
