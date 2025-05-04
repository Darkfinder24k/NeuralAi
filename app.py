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
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory[-20:], f, indent=4)  # Save last 20 exchanges
    except Exception as e:
        st.error(f"Error saving to memory: {e}")

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
        return f"❌ Llama API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing Llama API response: {e}"

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
def merge_responses(gemini_text, deepseek_text, llama_text, web_text):
    try:
        prompt = (
            f"You are Firebox AI. You will now intelligently merge four responses into one final, polished answer.\n"
            f"Do not mention DeepSeek, Llama, Gemini, or any AI name.\n"
            f"Remove duplicate, wrong, or conflicting info.\n"
            f"Synthesize the information into a comprehensive and insightful response.\n\n"
            f"Response A (Gemini):\n{gemini_text}\n\n"
            f"Response B (DeepSeek):\n{deepseek_text}\n\n"
            f"Response C (Llama):\n{llama_text}\n\n"
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
custom_css += """
<style>
div.stTextInput {
    position: fixed;
    bottom: 50px; /* Adjust as needed to account for the footer */
    left: 0;
    width: 100%;
    background-color: rgba(0, 0, 0, 0.5); /* Optional background for better visibility */
    padding: 10px;
    box-sizing: border-box;
    z-index: 1000; /* Ensure it's on top of other elements */
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
.stButtonContainer {
    position: fixed;
    bottom: 10px; /* Adjust as needed */
    left: 0;
    width: 100%;
    display: flex;
    justify-content: center; /* Center the buttons */
    gap: 10px; /* Space between buttons */
    padding: 10px;
    box-sizing: border-box;
    background-color: rgba(0, 0, 0, 0.3); /* Optional background */
    z-index: 999; /* Ensure buttons are above other elements */
}
.stButtonContainer > div > button {
    width: auto !important; /* Allow buttons to size based on content */
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# === Streamlit UI ===
st.title("🔥 Firebox AI – Ultimate Assistant")

# Move the chat history display to the top
display_chat_history()

# Create a container for the fixed input and buttons
fixed_input_container = st.container()
with fixed_input_container:
    user_input = st.text_input("Your Query:", key="fixed_input")
    col1, col2 = st.columns(2)
    with col1:
        web_search_button = st.button("🌐 Web Search", key="fixed_web_search")
    # You can add more buttons here if needed

# Footer message
st.markdown('<div id="firebox-footer">Firebox can make mistakes. <span style="font-weight: bold;">Help it improve.</span></div>', unsafe_allow_html=True)

# === Response Logic ===
if user_input:
    gemini_response = call_firebox_gemini(user_input)
    deepseek_response = deepseek_ai_response(user_input)
    llama_response = llama_ai_response(user_input)
    web_results = search_web(user_input) if web_search_button else ""

    final_output = merge_responses(gemini_response, deepseek_response, llama_response, web_results)

    # Save to memory
    save_to_memory(user_input, final_output)

    # Display current prompt and response at the top
    st.markdown(f"**You:** {user_input}")
    st.markdown(f"**Firebox:** {final_output}")

    # Clear the input field after submission (optional)
    fixed_input_container.empty() # This will clear the container, including the input
    with fixed_input_container:
        user_input = st.text_input("Your Query:", key="fixed_input") # Re-render the input
