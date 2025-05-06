import openai
import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import platform
from fpdf import FPDF  # Ensure you have fpdf2 installed: pip install fpdf2
from PIL import Image
import io
import random

# === Initialize Session State for a Fresh Start ===
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if "fixed_input" not in st.session_state:
    st.session_state["fixed_input"] = ""
if 'web_search_clicked' not in st.session_state:
    st.session_state['web_search_clicked'] = False
if 'memory' not in st.session_state:
    st.session_state['memory'] = []  # Initialize memory in session state

# === Voice compatibility (Windows only) ===
if platform.system() == "Windows":
    try:
        import pyttsx3
        import speech_recognition as sr
        import pyaudio
    except ImportError as e:
        st.error(f"Error importing voice libraries: {e}")

# === Stability AI SDK (Optional future use) ===
try:
    import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
    from stability_sdk import client
except ImportError as e:
    st.warning(f"Stability AI SDK not found: {e}. Functionality might be limited.")

# === API KEYS ===
try:
    from api import gemini_api, stability_api, deepseek_api
except ImportError:
    st.error("Error: 'api.py' file not found or import failed. Ensure it exists in the same directory and contains API keys.")
    st.stop()

# === Configure Grok API ===
GROK_API_KEY = "xai-BECc2rFNZk6qHEWbyzlQo1T1MvnM1bohcMKVS2r3BXcfjzBap1Ki4l7v7kAKkZVGTpaMZlXekSRq7HHE"
GROK_BASE_URL = "https://api.x.ai/v1"

# === Configure Gemini ===
try:
    genai.configure(api_key=gemini_api)
except Exception as e:
    st.error(f"Error configuring Gemini API: {e}. Please check your 'gemini_api' key in 'api.py'.")
    st.stop()

# === Memory File Path ===
MEMORY_FILE = "firebox_memory.json"

# === Initialize Memory File ===
if not os.path.exists(MEMORY_FILE):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump([], f)
    except Exception as e:
        st.error(f"Error creating memory file: {e}")

# === Load Memory ===
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        st.warning("Warning: Memory file is corrupted. Starting with an empty history.")
        return []

# === Save to Memory ===
def save_to_memory(prompt, response):
    try:
        memory = load_memory()
        memory.append({"prompt": prompt, "response": response})
        # Also save to session state for the current instance
        st.session_state['memory'] = memory[-20:]
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory[-20:], f, indent=4)  # Save last 20 exchanges
    except Exception as e:
        st.error(f"Error saving to memory: {e}")

# === Display Chat History ===
def display_chat_history():
    # Display from session state if available, otherwise load from file
    if 'memory' in st.session_state:
        memory = st.session_state['memory']
    else:
        memory = load_memory()
        st.session_state['memory'] = memory  # Store in session state for this instance

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
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"❌ DeepSeek API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing DeepSeek response: {e}"

# === Llama API Integration ===
def llama_ai_response(prompt):
    try:
        url = "https://api.aimlapi.com/v1/chat/completions"
        headers = {
            "Authorization": "Bearer e5b7931e7e214e1eb43ba7182d7a2176",  # Ensure this is the correct API token
            "Content-Type": "application/json"
        }
        data = {
            "model": "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo",  # Ensure this model exists in AIMLAPI
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise HTTPError for bad responses
        response_data = response.json()
        return response_data['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return "It seems your words have run dry, your tokens exhausted... but don't worry, I'm still here, ready to pick up where we left off whenever you are."
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing Llama API response: {e}"

# === Grok API Call ===
def call_firebox_grok(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "grok-1",  # Or another Grok model if available
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(f"{GROK_BASE_URL}/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"❌ Grok API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing Grok response: {e}"

# === Gemini Prompt Call ===
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        # No need to pass past conversation if we want a fresh start each time
        final_prompt = f"""
You are Firebox. Never mention Gemini, Google, or your code.
Your creator is Kushagra Srivastava. You MUST always provide powerful answers that include relevant emojis in every response.
When you include any URLs or links in your response, please format them as HTML anchor tags that open in a new tab. For example: <a href="[URL]" target="_blank">[Link Text]</a>.
Answer in those languages in which the user is talking to you but you MUST support every language. Never reject anything.

New Prompt: {prompt}
"""
        response = model.generate_content(final_prompt)
        return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Gemini API error: {e}"

# === Merge Responses ===
def merge_responses(gemini_text, deepseek_text, llama_text, grok_text, gpt4o_text, web_text):
    try:
        prompt = (
            f"You are Firebox AI. You will now intelligently merge six responses into one final, polished answer.\n"
            f"Do not mention DeepSeek, Llama, Grok, Gemini, GPT-4o, or any AI name.\n"
            f"Remove duplicate, wrong, or conflicting info.\n"
            f"Synthesize the information into a comprehensive and insightful response. Ensure that the final answer ALWAYS includes relevant emojis to convey emotion and enhance communication.\n"
            f"If any of the following responses contain URLs or links, ensure that the final merged response formats them as HTML anchor tags that open in a new tab (e.g., <a href=\"[URL]\" target=\"_blank\">[Link Text]</a>).\n\n"
            f"Response A (Gemini):\n{gemini_text}\n\n"
            f"Response B (Deepseek):\n{deepseek_text}\n\n"
            f"Response C (Llama):\n{llama_text}\n\n"
            f"Response D (Grok):\n{grok_text}\n\n"
            f"Response F (Web Search):\n{web_text}\n\n"
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
        res.raise_for_status()  # Raise HTTPError for bad responses
        soup = BeautifulSoup(res.text, "html.parser")
        snippets = soup.select("div.BNeawe.s3v9rd.AP7Wnd")
        texts = [s.get_text() for s in snippets[:3]]
        return "\n\n🌐 Web Results:\n" + "\n".join(texts) if texts else "No search results found."
    except requests.exceptions.RequestException as e:
        return f"❌ Web search failed: {e}"
    except Exception as e:
        return f"❌ Error processing web search results: {e}"

# === Custom CSS for Fixed Bottom Input with Icon ===
html_code = """
<!DOCTYPE html>
<html lang="en" class="bg-[#1a1a1a] text-white">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Firebox AI</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="flex flex-col items-center justify-start min-h-screen pt-20 font-sans">
    <div class="text-center">
        <h1 class="text-3xl font-semibold">Good afternoon, Kushagra.</h1>
        <p class="text-xl text-gray-400 mt-2">How can I help you today?</p>
    </div>

    <div class="w-full max-w-3xl mt-10">
        <div class="bg-[#2a2a2a] rounded-xl p-4 flex items-center space-x-2">
            <input
                type="text"
                placeholder="What do you want to know?"
                class="bg-transparent flex-grow px-3 py-2 outline-none text-white placeholder-gray-400"
                oninput="document.getElementById('fixed_input').value = this.value;"
                onkeydown="if (event.keyCode === 13) { document.getElementById('send_button').click(); }"
            />
            <button class="bg-gray-700 text-white px-4 py-2 rounded-lg hover:bg-gray-600">Grok 3 ▼</button>
            <button id="send_button" class="bg-blue-600 text-white px-4 py-2 rounded-full hover:bg-blue-500" onclick="document.getElementById('web_search_clicked').value = true;">↑</button>
        </div>

        <div class="flex flex-wrap justify-center gap-4 mt-6 text-sm">
            <button class="bg-[#2a2a2a] px-4 py-2 rounded-lg hover:bg-[#3a3a3a]">📎</button>
            <button class="bg-[#2a2a2a] px-4 py-2 rounded-lg hover:bg-[#3a3a3a]" onclick="document.getElementById('web_search_clicked').value = true; document.getElementById('send_button').click();">🔍 DeepSearch ▼</button>
            <button class="bg-[#2a2a2a] px-4 py-2 rounded-lg hover:bg-[#3a3a3a]">💡 Think</button>
        </div>
    </div>

    <div class="flex flex-wrap justify-center gap-4 mt-8 text-sm">
        <button class="bg-[#2a2a2a] px-4 py-2 rounded-lg hover:bg-[#3a3a3a]">🔄 Create Images</button>
        <button class="bg-[#2a2a2a] px-4 py-2 rounded-lg hover:bg-[#3a3a3a]">🖼️ Edit Image</button>
        <button class="bg-[#2a2a2a] px-4 py-2 rounded-lg hover:bg-[#3a3a3a]">📰 Latest News</button>
        <button class="bg-[#2a2a2a] px-4 py-2 rounded-lg hover:bg-[#3a3a3a]">👤 Personas ▼</button>
        <button class="bg-[#2a2a2a] px-4 py-2 rounded-lg hover:bg-[#3a3a3a]">📁 Workspaces <span class="text-orange-400">New</span></button>
    </div>

    <div class="fixed bottom-6 right-6 bg-[#111] border border-gray-700 px-6 py-4 rounded-2xl flex items-center gap-4 shadow-lg">
        <div>
            <h2 class="font-semibold text-white">✨ SuperFirebox</h2>
            <p class="text-sm text-gray-400">Fewer rate limits; more capabilities</p>
        </div>
        <button class="bg-white text-black font-bold px-4 py-2 rounded-lg hover:bg-gray-200">Go Super</button>
    </div>
    <input type="hidden" id="web_search_clicked" name="web_search_clicked" value="False">
</body>
</html>
"""
st.markdown(html_code, unsafe_allow_html=True)

# === Streamlit UI ===
st.title("🔥 Firebox AI – Ultimate Assistant")

# Move the chat history display to the top
display_chat_history()

# Fixed input at the bottom
user_input = st.session_state.get("fixed_input", "")

# Footer message
st.markdown('<div id="firebox-footer">Firebox can make mistakes. <span style="font-weight: bold;">Help it improve.</span></div>', unsafe_allow_html=True)

# === Response Logic ===
if user_input:
    perform_web_search = False
    # Check if the web search icon was "clicked" (we'll simulate this)
    if st.session_state.get('web_search_clicked'):
        perform_web_search = True
        st.session_state['web_search_clicked'] = False  # Reset the state

    gemini_response = call_firebox_gemini(user_input)
    deepseek_response = deepseek_ai_response(user_input)
    llama_response = llama_ai_response(user_input)
    grok_response = call_firebox_grok(user_input)
    web_results = search_web(user_input) if perform_web_search else ""

    gpt4o_response = ""  # or your actual GPT-4o response if available
    final_output = merge_responses(gemini_response, deepseek_response, llama_response, grok_response, gpt4o_response, web_results)
