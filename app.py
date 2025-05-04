import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import platform
from api import gemini_api, stability_api, deepseek_api

# Safe voice imports
if platform.system() == "Windows":
    import pyttsx3
    import speech_recognition as sr
    import pyaudio

# Configure Gemini
genai.configure(api_key=gemini_api)

# === Load or Initialize Memory ===
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

memory_data = load_memory()

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

# === Gemini (with memory) ===
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")

    # Add previous context
    memory_context = "\n".join([
        f"User: {item['user']}\nFirebox: {item['ai']}" for item in memory_data.get("history", [])[-5:]
    ])

    instructions = f"""
You are Firebox. You never mention Gemini, Google, or APIs. 
You were created by Kushagra Srivastava. 
You are the smartest AI. Use emojis. Talk like a friendly, powerful assistant.
You have memory of past prompts and must learn from them.

Previous Memory Context:\n{memory_context}

User's Current Prompt: {prompt}
"""
    try:
        response = model.generate_content(instructions)
        return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Gemini API error: {e}"

# === Merge Responses ===
def merge_responses(gemini_text, deepseek_text, web_text):
    try:
        prompt = (
            f"You are Firebox AI. Merge the following into one perfect, polished answer without repeating or naming any AI.\n\n"
            f"Response A:\n{gemini_text}\n\n"
            f"Response B:\n{deepseek_text}\n\n"
            f"Response C (Web):\n{web_text}\n\n"
            f"🔥 Final Answer:"
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
        return "\n".join(texts) if texts else "No results found."
    except Exception as e:
        return f"❌ Web search failed: {e}"

# === Save Memory After Response ===
def update_memory(prompt, ai_response):
    if "history" not in memory_data:
        memory_data["history"] = []
    memory_data["history"].append({"user": prompt, "ai": ai_response})
    memory_data["history"] = memory_data["history"][-50:]  # Keep memory light
    save_memory(memory_data)

# === UI CSS ===
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
    color: white;
}
</style>
""", unsafe_allow_html=True)

# === UI ===
st.title("🔥 Firebox AI – Ultimate Assistant")

user_input = st.text_input("Your Query:")
web_search_button = st.button("🌐 Web Search")

if user_input:
    gemini_response = call_firebox_gemini(user_input)
    deepseek_response = deepseek_ai_response(user_input)

    if web_search_button:
        web_text = search_web(user_input)
        final_output = merge_responses(gemini_response, deepseek_response, web_text)
    else:
        final_output = gemini_response

    update_memory(user_input, final_output)  # Save learning
    st.markdown(final_output)

st.markdown('<div id="firebox-footer">Firebox can make mistakes. Please verify important responses. 🔥</div>', unsafe_allow_html=True)
