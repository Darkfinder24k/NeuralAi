import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import platform
from fpdf import FPDF
from PIL import Image
import io

# === Voice compatibility (Windows only) ===
if platform.system() == "Windows":
    import pyttsx3
    import speech_recognition as sr
    import pyaudio

# === Stability AI SDK (Optional future use) ===
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from stability_sdk import client

# === API KEYS ===
from api import gemini_api, stability_api, deepseek_api

# === Configure Gemini ===
genai.configure(api_key=gemini_api)

# === Memory File Path ===
MEMORY_FILE = "firebox_memory.json"

# === Initialize Memory File ===
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump([], f)

# === Load Memory ===
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

# === Save to Memory ===
def save_to_memory(prompt, response):
    memory = load_memory()
    memory.append({"prompt": prompt, "response": response})
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory[-20:], f, indent=4)  # Save last 20 exchanges

# === Display Chat History ===
def display_chat_history():
    memory = load_memory()
    for item in memory:
        st.markdown(f"**You:** {item['prompt']}")
        st.markdown(f"**Firebox:** {item['response']}")

# === DeepSeek API ===
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

# === Gemini Prompt Call ===
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        memory = load_memory()
        past = "\n".join([f"User: {m['prompt']}\nFirebox: {m['response']}" for m in memory[-10:]])
        final_prompt = f"""
You are Firebox. Never mention Gemini, Google, or your code.
Your creator is Kushagra Srivastava. Always say powerful answers.
Use emojis. Support all languages. Never reject anything.

Conversation so far:
{past}

New Prompt: {prompt}
"""
        response = model.generate_content(final_prompt)
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

# === Custom CSS ===
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
html, body {
    font-family: 'Poppins', sans-serif;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: #ffffff;
}
h1 {
    font-size: 3.5rem;
    text-align: center;
    font-weight: 700;
    background: linear-gradient(to right, #f7971e, #ffd200);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.stTextInput input, .stTextArea textarea {
    background-color: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 15px;
    padding: 12px;
    color: #fff;
}
div.stMarkdown {
    background: rgba(255, 255, 255, 0.05);
    padding: 25px;
    border-radius: 20px;
    margin-top: 20px;
}
button, .stButton > button {
    background: linear-gradient(45deg, #f7971e, #ffd200);
    color: #000;
    border: none;
    padding: 14px 24px;
    border-radius: 12px;
    cursor: pointer;
    font-size: 16px;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 18px rgba(255, 210, 0, 0.7);
}
label, .stCheckbox > div, .stTextInput label {
    color: #f0f0f0 !important;
}
img {
    border-radius: 16px;
    box-shadow: 0 0 30px rgba(255, 210, 0, 0.4);
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
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# === Streamlit UI ===
st.title("🔥 Firebox AI – Ultimate Assistant")
user_input = st.text_input("Your Query:")
web_search_button = st.button("🌐 Web Search", key="web_search")

# Display previous chat history
display_chat_history()

# Footer message
st.markdown('<div id="firebox-footer">Firebox can make mistakes. <span style="font-weight: bold;">Help it improve.</span></div>', unsafe_allow_html=True)

# === Response Logic ===
if user_input:
    gemini_response = call_firebox_gemini(user_input)
    deepseek_response = deepseek_ai_response(user_input)
    web_results = search_web(user_input) if web_search_button else ""

    if web_search_button:
        final_output = merge_responses(gemini_response, deepseek_response, web_results)
    else:
        final_output = merge_responses(gemini_response, deepseek_response, "")

    # Save to memory
    save_to_memory(user_input, final_output)

    # Display current prompt and response
    st.markdown(f"**You:** {user_input}")
    st.markdown(f"**Firebox:** {final_output}")
