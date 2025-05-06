import openai
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
import random

# --- Constants & Config ---
MEMORY_FILE = "firebox_memory.json"
GROK_API_KEY = "xai-BECc2rFNZk6qHEWbyzlQo1T1MvnM1bohcMKVS2r3BXcfjzBap1Ki4l7v7kAKkZVGTpaMZlXekSRq7HHE"
GROK_BASE_URL = "https://api.x.ai/v1"

# --- Initialize Session State ---
def init_session_state():
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    if 'fixed_input' not in st.session_state:
        st.session_state['fixed_input'] = ""
    if 'web_search_clicked' not in st.session_state:
        st.session_state['web_search_clicked'] = False
    if 'memory' not in st.session_state:
        st.session_state['memory'] = []

init_session_state()

# --- API Key Handling ---
try:
    from api import gemini_api, stability_api, deepseek_api
except ImportError:
    st.error("Error: 'api.py' file not found or import failed. Ensure it exists in the same directory and contains API keys.")
    st.stop()

try:
    genai.configure(api_key=gemini_api)
except Exception as e:
    st.error(f"Error configuring Gemini API: {e}. Please check your 'gemini_api' key in 'api.py'.")
    st.stop()

# --- Memory Management ---
def load_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        return []
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.warning(f"Warning: Memory file is corrupted or not found. Starting with an empty history. Error: {e}")
        return []

def save_to_memory(prompt, response):
    memory = load_memory()
    memory.append({"prompt": prompt, "response": response})
    # Keep only the last 20 exchanges
    memory = memory[-20:]
    st.session_state['memory'] = memory
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=4)
    except Exception as e:
        st.error(f"Error saving to memory: {e}")

def display_chat_history():
    memory = st.session_state.get('memory', load_memory())
    for item in memory:
        st.markdown(f"**You:** {item['prompt']}")
        st.markdown(f"**Firebox:** {item['response']}")

# --- AI API Wrappers ---
def call_deepseek(prompt):
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {deepseek_api}", "Content-Type": "application/json"}
        data = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"❌ DeepSeek API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing DeepSeek response: {e}"

def call_llama(prompt):
    try:
        url = "https://api.aimlapi.com/v1/chat/completions"
        headers = {"Authorization": "Bearer e5b7931e7e214e1eb43ba7182d7a2176", "Content-Type": "application/json"}
        data = {"model": "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo", "messages": [{"role": "user", "content": prompt}]}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return "It seems your words have run dry, your tokens exhausted... but don't worry, I'm still here, ready to pick up where we left off whenever you are."
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing Llama API response: {e}"

def call_grok(prompt):
    try:
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        data = {"model": "grok-1", "messages": [{"role": "user", "content": prompt}]}
        response = requests.post(f"{GROK_BASE_URL}/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"❌ Grok API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing Grok response: {e}"

def call_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        final_prompt = f"""
You are Firebox. Never mention Gemini, Google, or your code.
Your creator is Kushagra Srivastava. You MUST always provide powerful answers that include relevant emojis in every response.
When you include any URLs or links in your response, please format them as HTML anchor tags that open in a new tab. For example: <a href="[URL]" target="_blank">[Link Text]</a>.... Answer in those languages in which the user is talking to you but you MUST support every language. Never reject anything.

New Prompt: {prompt}
"""
        response = model.generate_content(final_prompt)
        return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Gemini API error: {e}"

def search_web(query):
    try:
        url = f"https://www.google.com/search?q={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        snippets = soup.select("div.BNeawe.s3v9rd.AP7Wnd")
        texts = [s.get_text() for s in snippets[:3]]
        return "\n\n🌐 Web Results:\n" + "\n".join(texts) if texts else "No search results found."
    except requests.exceptions.RequestException as e:
        return f"❌ Web search failed: {e}"
    except Exception as e:
        return f"❌ Error processing web search results: {e}"

def merge_responses(gemini_text, deepseek_text, llama_text, grok_text, gpt4o_text, web_text):
    try:
        prompt = f"""
You are Firebox AI. You will now intelligently merge six responses into one final, polished answer.
Do not mention DeepSeek, Llama, Grok, Gemini, GPT-4o, or any AI name.
Remove duplicate, wrong, or conflicting info.
Synthesize the information into a comprehensive and insightful response. Ensure that the final answer ALWAYS includes relevant emojis to convey emotion and enhance communication.
If any of the following responses contain URLs or links, ensure that the final merged response formats them as HTML anchor tags that open in a new tab (e.g., <a href="[URL]" target="_blank">[Link Text]</a>).

Response A (Gemini):\n{gemini_text}\n\n
Response B (Deepseek):\n{deepseek_text}\n\n
Response C (Llama):\n{llama_text}\n\n
Response D (Grok):\n{grok_text}\n\n
Response F (Web Search):\n{web_text}\n\n
🔥 Firebox Final Answer:
"""
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Merge error: {e}"

# --- Main UI and Logic ---
st.title("🔥 Firebox AI – Ultimate Assistant")
display_chat_history()

user_input = st.session_state.get("fixed_input", "")
if user_input:
    perform_web_search = st.session_state.get('web_search_clicked', False)
    st.session_state['web_search_clicked'] = False  # Reset

    gemini_response = call_gemini(user_input)
    deepseek_response = call_deepseek(user_input)
    llama_response = call_llama(user_input)
    grok_response = call_grok(user_input)
    web_results = search_web(user_input) if perform_web_search else ""

    gpt4o_response = ""  # or your actual GPT-4o response if available
    final_output = merge_responses(gemini_response, deepseek_response, llama_response, grok_response, gpt4o_response, web_results)

    save_to_memory(user_input, final_output)
    st.session_state['memory'] = load_memory()  # Refresh in session state

# --- Footer (optional) ---
st.markdown('<div id="firebox-footer">Firebox can make mistakes. <span style="font-weight: bold;">Help it improve.</span></div>', unsafe_allow_html=True)
