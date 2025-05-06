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

# === Grok API Call ===
def call_firebox_grok(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "grok-3",  # Or another Grok model if available
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

# === Image Generation API Call ===
def generate_image(prompt="A futuristic city skyline at sunset"):
    try:
        url = "https://api.aimlapi.com/v1/images/generations"  # Example endpoint, update if needed
        headers = {
            "Authorization": "Bearer e5b7931e7e214e1eb43ba7182d7a2176",
            "Content-Type": "application/json"
        }
        data = {
            "model": "dall-e-3",  # Replace with your specific model name if different
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024"
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        image_url = response.json()['data'][0]['url']
        return image_url

    except requests.exceptions.RequestException:
        return "⚠️ Unable to connect to the image generation API. Please try again later."

    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing image API response: {e}"

# === Merge Responses ===
def merge_responses(gemini_text, deepseek_text, grok_text, web_text):
    try:
        prompt = (
            f"You are Firebox AI. You will now intelligently merge four responses into one final, polished answer.\n"
            f"Do not mention DeepSeek, Grok, or Gemini.\n"
            f"Remove duplicate, wrong, or conflicting info.\n"
            f"Synthesize the information into a comprehensive and insightful response. Ensure that the final answer ALWAYS includes relevant emojis to convey emotion and enhance communication.\n"
            f"If any of the following responses contain URLs or links, ensure that the final merged response formats them as HTML anchor tags that open in a new tab (e.g., <a href=\"[URL]\" target=\"_blank\">[Link Text]</a>).\n\n"
            f"Response A (Gemini):\n{gemini_text}\n\n"
            f"Response B (Deepseek):\n{deepseek_text}\n\n"
            f"Response C (Grok):\n{grok_text}\n\n"
            f"Response D (Web Search):\n{web_text}\n\n"
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

# === Custom CSS for Fixed Bottom Input ===
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
    z-index: 1001; /* Ensure footer is on top of the input if desired */
}
</style>
"""
# Full version of your Firebox AI assistant (Streamlit app)
# Split into two parts due to length

# Part 1: Main logic and API setup
[Already shared above - starting from your code]

# PART 2: CONTINUED STREAMLIT UI AND FUNCTIONALITY

# === Display Firebox UI ===
st.markdown(custom_css, unsafe_allow_html=True)
st.title("🔥 Firebox AI - Your Ultimate Assistant")

# === Chat Input ===
st.markdown("""
    <style>
        .stTextInput>div>div>input {
            font-size: 20px;
            border-radius: 12px;
            padding: 10px;
            border: 2px solid #f7971e;
            background-color: #1c1c1c;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

user_input = st.text_input("Ask Firebox something...", value=st.session_state.get("fixed_input", ""))

if user_input:
    st.session_state["fixed_input"] = user_input
    with st.spinner("Firebox is thinking..."):
        gemini_response = call_firebox_gemini(user_input)
        deepseek_response = deepseek_ai_response(user_input)
        grok_response = call_firebox_grok(user_input)
        web_result = search_web(user_input) if st.session_state.get("web_search_clicked") else ""

        final_response = merge_responses(gemini_response, deepseek_response, grok_response, web_result)

        # Save interaction
        save_to_memory(user_input, final_response)

        # Display result
        st.markdown(f"**Firebox:** {final_response}", unsafe_allow_html=True)

# === Display Past Chat ===
st.subheader("🧠 Firebox Memory")
display_chat_history()

# === Image Generation Button ===
if st.button("🖼️ Generate Image"):
    st.session_state["image_gen_clicked"] = True
    image_prompt = st.text_input("Enter image prompt:", key="image_prompt")
    if image_prompt:
        with st.spinner("Creating image..."):
            image_url = generate_image(image_prompt)
            if image_url.startswith("http"):
                st.image(image_url, caption="AI Generated Image")
                st.session_state["image_url"] = image_url
            else:
                st.error(image_url)

# === Web Search Button ===
if st.button("🌐 Search Web"):
    st.session_state["web_search_clicked"] = True
    st.success("Web search will be included in the next answer.")

# === Clear Memory Button ===
if st.button("🧹 Clear Memory"):
    st.session_state['memory'] = []
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    st.success("Memory cleared.")

# === Voice Input (if on Windows and libraries are present) ===
if platform.system() == "Windows" and 'pyttsx3' in globals():
    if st.button("🎙️ Voice Input"):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("Listening...")
            audio = recognizer.listen(source)
            try:
                voice_text = recognizer.recognize_google(audio)
                st.session_state["fixed_input"] = voice_text
                st.success(f"You said: {voice_text}")
            except sr.UnknownValueError:
                st.error("Could not understand the audio.")
            except sr.RequestError as e:
                st.error(f"Speech recognition error: {e}")

# === Text-to-Speech ===
if platform.system() == "Windows" and 'pyttsx3' in globals():
    if st.button("🔊 Speak Last Reply"):
        if st.session_state.get("memory"):
            last_reply = st.session_state["memory"][-1]["response"]
            engine = pyttsx3.init()
            engine.say(last_reply)
            engine.runAndWait()
        else:
            st.warning("No previous response to speak.")
