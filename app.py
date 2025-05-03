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
def merge_responses(gemini_text, deepseek_text, web_text):
    try:
        prompt = (
            f"You are Firebox AI. You will now intelligently merge three responses into one final, polished answer.\n"
            f"Do not mention DeepSeek, Gemini, or any AI name.\n"
            f"Remove duplicate, wrong, or conflicting info.\n\n"
            f"Response A (Gemini):\n{gemini_text}\n\n"
            f"Response B (DeepSeek):\n{deepseek_text}\n\n"
            f"Response C (Web Search):\n{web_text}\n\n"
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

# === Image Generation (Stable Diffusion) ===
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
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

html, body {
    font-family: 'Poppins', sans-serif;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: #ffffff;
    margin: 0;
    padding: 0;
}

h1 {
    font-size: 3.5rem;
    text-align: center;
    font-weight: 700;
    background: linear-gradient(to right, #f7971e, #ffd200);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 20px;
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
}

.stTextInput input, .stTextArea textarea {
    background-color: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 15px;
    padding: 12px;
    color: #fff;
    font-size: 16px;
    transition: all 0.3s ease-in-out;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #ffd200;
    box-shadow: 0 0 12px #ffd20088;
}

div.stMarkdown {
    background: rgba(255, 255, 255, 0.05);
    padding: 25px;
    border-radius: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.2);
    margin-top: 20px;
    transition: all 0.3s ease;
}

button, .stButton > button {
    background: linear-gradient(45deg, #f7971e, #ffd200);
    color: #000;
    border: none;
    padding: 14px 24px;
    font-weight: 600;
    border-radius: 12px;
    cursor: pointer;
    font-size: 16px;
    box-shadow: 0 6px 14px rgba(0,0,0,0.4);
    transition: transform 0.2s, box-shadow 0.2s;
    width: 100%;
}

button:hover, .stButton > button:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 18px rgba(255, 210, 0, 0.7);
}

label, .stCheckbox > div, .stTextInput label {
    color: #f0f0f0 !important;
}

img {
    border-radius: 16px;
    box-shadow: 0 0 30px rgba(255, 210, 0, 0.4);
    margin-top: 25px;
    max-width: 100%;
}

.stCheckbox {
    background: rgba(255,255,255,0.05);
    padding: 10px 15px;
    border-radius: 12px;
    margin-bottom: 15px;
    transition: all 0.2s ease;
}

.stCheckbox:hover {
    background: rgba(255,255,255,0.08);
}

hr {
    border: none;
    height: 2px;
    background: linear-gradient(to right, #ffd200, #f7971e);
    margin: 30px 0;
}

#firebox-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    text-align: center;
    padding: 10px;
    font-size: 14px;
    border-radius: 10px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.6);
}

.stButton > button {
    margin-bottom: 15px;
}

.stButton {
    margin-top: 20px;
    width: 100%;
    text-align: center;
}

.search-icon {
    font-size: 1.5rem;
    cursor: pointer;
    color: white;
}

.search-button {
    padding: 10px;
    border-radius: 50%;
    background-color: transparent;
    border: 1px solid #ffd200;
    display: inline-block;
    cursor: pointer;
}

.search-button:hover {
    background-color: #ffd200;
    color: black;
}

</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# === UI Starts ===
st.title("🔥 Firebox AI – Ultimate Assistant")

# Web and Image Search buttons with icons
col1, col2 = st.columns(2)

with col1:
    web_search_button = st.button("🌐 Web Search", key="web_search")
with col2:
    image_gen_button = st.button("🎨 Image Generation", key="image_gen")

# Default input field
user_input = st.text_input("Your Query:")

# Automatically update prompt if user selects Web Search or Image Generation
if web_search_button:
    user_input = f"WebSearch: {user_input}"

elif image_gen_button:
    user_input = f"Image Generation: {user_input}"

if user_input:
    # Generate answer based on input
    if "WebSearch" in user_input:
        web_results = search_web(user_input.replace("WebSearch:", "").strip())
        gemini_response = call_firebox_gemini(user_input.replace("WebSearch:", "").strip())
        deepseek_response = deepseek_ai_response(user_input.replace("WebSearch:", "").strip())
        merged_response = merge_responses(gemini_response, deepseek_response, web_results)
        st.markdown(merged_response)
    
    elif "Image Generation" in user_input:
        generated_image = generate_image_stability(user_input.replace("Image Generation:", "").strip())
        if generated_image:
            st.image(generated_image)

# Add the message about Firebox making mistakes permanently fixed at the bottom
st.markdown('<div id="firebox-footer">Firebox can make mistakes. <span style="font-weight: bold;">A better sentence</span></div>', unsafe_allow_html=True)
