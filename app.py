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
MEMORY_FILE = "firebox_memory.xlsx"

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
div.stTextInput {
    position: fixed;
    bottom: 50px; /* Adjust as needed to account for the footer */
    left: 0;
    width: 100%;
    padding: 10px 50px 10px 10px; /* Add padding for the icon */
    box-sizing: border-box;
    z-index: 1000; /* Ensure it's on top of other elements */
    background-color: rgba(0, 0, 0, 0.3); /* Optional background */
    border-radius: 15px;
    border: 1px solid rgba(255, 255, 255, 0.2);
}
div.stTextInput > label > div {
    color: #fff !important; /* Style the input label */
}
div.stTextInput > div > input {
    background-color: transparent !important;
    color: #fff !important;
    border: none !important;
    border-radius: 0 !important;
    padding-left: 0 !important;
}
div.stTextInput::after {
    content: "🌐"; /* Unicode for a globe icon */
    position: absolute;
    bottom: 18px; /* Adjust vertical position */
    right: 15px; /* Adjust horizontal position */
    font-size: 20px; /* Adjust icon size */
    color: #f7971e; /* Icon color */
    cursor: pointer;
    z-index: 1001; /* Ensure icon is clickable */
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
    z-index: 1001; /* Ensure footer is on top of the input if desired */
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# === Streamlit UI ===
st.title("🔥 Firebox AI – Ultimate Assistant")

# Move the chat history display to the top
display_chat_history()

# Fixed input at the bottom
user_input = st.text_input("Your Query:", key="fixed_input")

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


    # Save to memory (also updates session state)
    save_to_memory(user_input, final_output)

    # Display current prompt and response at the top
    st.markdown(f"**You:** {user_input}")
    st.markdown(f"**Firebox:** {final_output}")
