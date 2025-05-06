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
if 'image_gen_clicked' not in st.session_state:
    st.session_state['image_gen_clicked'] = False
if 'memory' not in st.session_state:
    st.session_state['memory'] = []  # Initialize memory in session state
if 'image_url' not in st.session_state:
    st.session_state['image_url'] = None
if 'is_premium' not in st.session_state:
    st.session_state['is_premium'] = False
if 'secret_code_entered' not in st.session_state:
    st.session_state['secret_code_entered'] = False
if 'premium_slider' not in st.session_state:
    st.session_state['premium_slider'] = False

# === Secret Code for Premium ===
SECRET_CODE_PREMIUM = "firebox_alpha_pro_2025"

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
def deepseek_ai_response(prompt, is_premium=False):
    model_name = "deepseek-chat"
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {deepseek_api}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "n": 2 if is_premium else 1, # Premium: Request multiple responses
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        raw_response = response.json()
        return raw_response
    except requests.exceptions.RequestException as e:
        return f"❌ DeepSeek API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing DeepSeek response: {e}. Response: {response.text}"

# === Grok API Call ===
def call_firebox_grok(prompt, is_premium=False):
    model_name = "grok-3" if is_premium else "grok-1"
    try:
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5 if is_premium else 0.7, # Premium: Lower temperature for more focused answers
        }
        response = requests.post(f"{GROK_BASE_URL}/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        raw_response = response.json()
        return raw_response
    except requests.exceptions.RequestException as e:
        return f"❌ Grok API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing Grok response: {e}. Response: {response.text}"

# === Gemini Prompt Call ===
def call_firebox_gemini(prompt, is_premium=False):
    model_name = "gemini-2.0-flash" if is_premium else "gemini-1.5-pro"
    try:
        final_prompt = f"""
You are Firebox. Never mention Gemini, Google, or your code.
Your creator is Kushagra Srivastava. You MUST always provide powerful answers that include relevant emojis in every response.
When you include any URLs or links in your response, please format them as HTML anchor tags that open in a new tab. For example: <a href="[URL]" target="_blank">[Link Text]</a>.
Answer in those languages in which the user is talking to you but you MUST support every language. Never reject anything.

{'**[Premium User - All Facilities Available]** ' if is_premium else '**[Standard User - Some Facilities Restricted]** '}New Prompt: {prompt}
"""
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(final_prompt, stream=is_premium)
        if is_premium:
            full_response = ""
            for chunk in response:
                full_response += chunk.text
            return full_response
        else:
            return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Gemini API error: {e}"

# === Advanced Image Generation (Premium) ===
def generate_advanced_image(prompt="A photorealistic scene of a nebula with vibrant colors and intricate details"):
    try:
        url = "https://api.aimlapi.com/v1/images/generations"  # Example endpoint, update if needed
        headers = {
            "Authorization": "Bearer e5b7931e7e214e1eb43ba7182d7a2176",
            "Content-Type": "application/json"
        }
        data = {
            "model": "sdxl-turbo",  # Example advanced model
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "style_raw": "cinematic, highly detailed, artistic" # Example advanced style
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        image_url = response.json()['data'][0]['url']
        return image_url

    except requests.exceptions.RequestException:
        return "⚠️ Unable to connect to the advanced image generation API. Please try again later."

    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing advanced image API response: {e}"

# === Basic Image Generation (Restricted Facility) ===
def generate_image(prompt="A simple abstract design"):
    st.warning("Image generation is a premium feature. Enter the premium code in the sidebar to unlock it. 🎨")
    return None

# === Premium Merge Responses ===
def premium_merge_responses(gemini_text, deepseek_texts, grok_text, web_text):
    responses = {}
    responses["Gemini"] = gemini_text
    responses["DeepSeek"] = deepseek_texts
    responses["Grok"] = grok_text
    if web_text:
        responses["Web Search"] = web_text

    response_string = "🔥 **Firebox Premium Raw Responses:**\n"
    for source, text in responses.items():
        response_string += f"**{source}:**\n{text}\n\n"
    return response_string

# === Basic Merge Responses (Restricted Facilities) ===
def merge_responses(gemini_text, deepseek_text, web_text):
    responses = {}
    responses["Gemini"] = gemini_text
    responses["DeepSeek"] = deepseek_text
    if web_text:
        responses["Web Search"] = web_text

    response_string = "🔥 **Firebox Standard Raw Responses:**\n"
    for source, text in responses.items():
        response_string += f"**{source}:**\n{text}\n\n"
    return response_string

# === Web Search ===
def search_web(query):
    st.warning("Web search is a premium feature. Enter the premium code in the sidebar to unlock it. 🌐")
    return ""

# === Premium Web Search (More Results) ===
def premium_search_web(query):
    try:
        url = f"https://www.google.com/search?q={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        res.raise_for_status()  # Raise HTTPError for bad responses
        soup = BeautifulSoup(res.text, "html.parser")
        snippets = soup.select("div.BNeawe.s3v9rd.AP7Wnd")
        texts = [s.get_text() for s in snippets[:5]] # Get more search results
        return "\n\n💎 Premium Web Results:\n" + "\n".join(texts) if texts else "No premium search results found."
    except requests.exceptions.RequestException as e:
        return f"❌ Premium web search failed: {e}"
    except Exception as e:
        return f"❌ Error processing premium web search results: {e}"

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
div.stTextInput {
    position: fixed;
    bottom: 50px; /* Adjust as needed to account for the footer */
    left: 0;
    width: 100%;
    padding: 10px;
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
    z-index: 1001;
/* Ensure footer is on top of the input if desired */
}
.premium-badge {
    background-color: #ffd700; /* Gold color */
    color: #000;
    padding: 0.2em 0.5em;
    border-radius: 5px;
    font-size: 0.8em;
    font-weight: bold;
    vertical-align: middle;
    margin-left: 0.5em;
}
.sidebar-content {
    padding: 20px;
    background-color: rgba(0, 0, 0, 0.5);
    border-radius: 10px;
    margin-bottom: 20px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# === Streamlit UI ===
st.title("🔥 Firebox AI – Raw Response Debug")

with st.sidebar:
    st.session_state['premium_slider'] = st.checkbox("Open Premium Access")
    if st.session_state['premium_slider']:
        premium_code_entered = st.text_input("Enter Premium Code:", type="password")
        if premium_code_entered == SECRET_CODE_PREMIUM:
            st.session_state['is_premium'] = True
            st.sidebar.markdown('<span class="premium-badge">Premium Unlocked</span>', unsafe_allow_html=True)
        elif premium_code_entered:
            st.sidebar.error("Incorrect code.")
            else:
            st.sidebar.info("Enter the premium code to unlock all features and enhanced models.")
    else:
        st.sidebar.info("Standard Version: Utilizes Gemini 1.5 Pro, Grok-1. Some facilities like advanced image generation and extensive web search are restricted.")
        st.sidebar.info("Check 'Open Premium Access' to enter the premium code.")

# Move the chat history display to the top
display_chat_history()

# Fixed input at the bottom
user_input = st.text_input("Your Query:", key="fixed_input")

# Footer message
st.markdown('<div id="firebox-footer">Firebox can make mistakes. <span style="font-weight: bold;">Help it improve.</span></div>', unsafe_allow_html=True)

if st.session_state.get('fixed_input'):
    user_input_lower = st.session_state.get('fixed_input').lower()
    perform_web_search = False
    perform_image_gen = False

    processed_input = st.session_state.get('fixed_input')

    st.markdown(f"**You:** {st.session_state.get('fixed_input')}")

    with st.spinner("Fetching raw responses..."):
        gemini_raw = call_firebox_gemini(processed_input, is_premium=st.session_state.get('is_premium'))
        deepseek_raw = deepseek_ai_response(processed_input, is_premium=st.session_state.get('is_premium'))
        grok_raw = None
        if st.session_state.get('is_premium'):
            grok_raw = call_firebox_grok(processed_input, is_premium=True)

        st.subheader("Raw API Responses:")
        st.write("**Gemini:**")
        st.json(gemini_raw)
        st.write("**DeepSeek:**")
        st.json(deepseek_raw)
        if grok_raw:
            st.write("**Grok:**")
            st.json(grok_raw)

        # We are only displaying raw responses for debugging, so we stop here.

# No JavaScript needed for the text-based trigger phrases
