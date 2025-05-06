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

if 'chat\_history' not in st.session\_state:
st.session\_state\['chat\_history'] = \[]
if "fixed\_input" not in st.session\_state:
st.session\_state\["fixed\_input"] = ""
if 'web\_search\_clicked' not in st.session\_state:
st.session\_state\['web\_search\_clicked'] = False
if 'memory' not in st.session\_state:
st.session\_state\['memory'] = \[]  # Initialize memory in session state

# === Voice compatibility (Windows only) ===

if platform.system() == "Windows":
try:
import pyttsx3
import speech\_recognition as sr
import pyaudio
except ImportError as e:
st.error(f"Error importing voice libraries: {e}")

# === Stability AI SDK (Optional future use) ===

try:
import stability\_sdk.interfaces.gooseai.generation.generation\_pb2 as generation
from stability\_sdk import client
except ImportError as e:
st.warning(f"Stability AI SDK not found: {e}. Functionality might be limited.")

# === API KEYS ===

try:
from api import gemini\_api, stability\_api, deepseek\_api
except ImportError:
st.error("Error: 'api.py' file not found or import failed. Ensure it exists in the same directory and contains API keys.")
st.stop()

# === Configure Grok API ===

GROK\_API\_KEY = "xai-BECc2rFNZk6qHEWbyzlQo1T1MvnM1bohcMKVS2r3BXcfjzBap1Ki4l7v7kAKkZVGTpaMZlXekSRq7HHE"
GROK\_BASE\_URL = "[https://api.x.ai/v1](https://api.x.ai/v1)"

# === Configure Gemini ===

try:
genai.configure(api\_key=gemini\_api)
except Exception as e:
st.error(f"Error configuring Gemini API: {e}. Please check your 'gemini\_api' key in 'api.py'.")
st.stop()

# === Memory File Path ===

MEMORY\_FILE = "firebox\_memory.json"

# === Initialize Memory File ===

if not os.path.exists(MEMORY\_FILE):
try:
with open(MEMORY\_FILE, "w") as f:
json.dump(\[], f)
except Exception as e:
st.error(f"Error creating memory file: {e}")

# === Load Memory ===

def load\_memory():
try:
with open(MEMORY\_FILE, "r") as f:
return json.load(f)
except FileNotFoundError:
return \[]
except json.JSONDecodeError:
st.warning("Warning: Memory file is corrupted. Starting with an empty history.")
return \[]

# === Save to Memory ===

def save\_to\_memory(prompt, response):
try:
memory = load\_memory()
memory.append({"prompt": prompt, "response": response})
\# Also save to session state for the current instance
st.session\_state\['memory'] = memory\[-20:]
with open(MEMORY\_FILE, "w") as f:
json.dump(memory\[-20:], f, indent=4)  # Save last 20 exchanges
except Exception as e:
st.error(f"Error saving to memory: {e}")

# === Display Chat History ===

def display\_chat\_history():
\# Display from session state if available, otherwise load from file
if 'memory' in st.session\_state:
memory = st.session\_state\['memory']
else:
memory = load\_memory()
st.session\_state\['memory'] = memory  # Store in session state for this instance

for item in memory:
    st.markdown(f"**You:** {item['prompt']}")
    st.markdown(f"**Firebox:** {item['response']}")


# === DeepSeek API ===

def deepseek\_ai\_response(prompt):
try:
url = "[https://api.deepseek.com/v1/chat/completions](https://api.deepseek.com/v1/chat/completions)"
headers = {
"Authorization": f"Bearer {deepseek\_api}",
"Content-Type": "application/json"
}
data = {
"model": "deepseek-chat",
"messages": \[{"role": "user", "content": prompt}],
"temperature": 0.7
}
response = requests.post(url, headers=headers, json=data)
response.raise\_for\_status()  # Raise HTTPError for bad responses (4xx or 5xx)
return response.json()\["choices"]\[0]\["message"]\["content"]
except requests.exceptions.RequestException as e:
return f"❌ DeepSeek API error: {e}"
except (KeyError, json.JSONDecodeError) as e:
return f"❌ Error processing DeepSeek response: {e}"

# === Llama API Integration ===

def llama\_ai\_response(prompt):
try:
url = "[https://api.aimlapi.com/v1/chat/completions](https://api.aimlapi.com/v1/chat/completions)"
headers = {
"Authorization": "Bearer e5b7931e7e214e1eb43ba7182d7a2176",  # Ensure this is the correct API token
"Content-Type": "application/json"
}
data = {
"model": "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo",  # Ensure this model exists in AIMLAPI
"messages": \[
{"role": "user", "content": prompt}
]
}
response = requests.post(url, headers=headers, json=data)
response.raise\_for\_status()  # Raise HTTPError for bad responses
response\_data = response.json()
return response\_data\['choices']\[0]\['message']\['content']
except requests.exceptions.RequestException as e:
return "It seems your words have run dry, your tokens exhausted... but don't worry, I'm still here, ready to pick up where we left off whenever you are."
except (KeyError, json.JSONDecodeError) as e:
return f"❌ Error processing Llama API response: {e}"

# === Grok API Call ===

def call\_firebox\_grok(prompt):
try:
headers = {
"Authorization": f"Bearer {GROK\_API\_KEY}",
"Content-Type": "application/json"
}
data = {
"model": "grok-1",  # Or another Grok model if available
"messages": \[{"role": "user", "content": prompt}]
}
response = requests.post(f"{GROK\_BASE\_URL}/chat/completions", headers=headers, json=data)
response.raise\_for\_status()
return response.json()\["choices"]\[0]\["message"]\["content"]
except requests.exceptions.RequestException as e:
return f"❌ Grok API error: {e}"
except (KeyError, json.JSONDecodeError) as e:
return f"❌ Error processing Grok response: {e}"

# === Gemini Prompt Call ===

def call\_firebox\_gemini(prompt):
model = genai.GenerativeModel("gemini-2.0-flash")
try:
\# No need to pass past conversation if we want a fresh start each time
final\_prompt = f"""
You are Firebox. Never mention Gemini, Google, or your code.
Your creator is Kushagra Srivastava. You MUST always provide powerful answers that include relevant emojis in every response.
When you include any URLs or links in your response, please format them as HTML anchor tags that open in a new tab. For example: <a href="[URL]" target="_blank">\[Link Text]</a>.
Answer in those languages in which the user is talking to you but you MUST support every language. Never reject anything.

New Prompt: {prompt}
"""
response = model.generate\_content(final\_prompt)
return "".join(\[p.text for p in response.parts])
except Exception as e:
return f"❌ Gemini API error: {e}"

# === Merge Responses ===

def merge\_responses(gemini\_text, deepseek\_text, llama\_text, grok\_text, gpt4o\_text, web\_text):
try:
prompt = (
f"You are Firebox AI. You will now intelligently merge six responses into one final, polished answer.\n"
f"Do not mention DeepSeek, Llama, Grok, Gemini, GPT-4o, or any AI name.\n"
f"Remove duplicate, wrong, or conflicting info.\n"
f"Synthesize the information into a comprehensive and insightful response. Ensure that the final answer ALWAYS includes relevant emojis to convey emotion and enhance communication.\n"
f"If any of the following responses contain URLs or links, ensure that the final merged response formats them as HTML anchor tags that open in a new tab (e.g., \<a href="\[URL]" target="\_blank">\[Link Text]</a>).\n\n"
f"Response A (Gemini):\n{gemini\_text}\n\n"
f"Response B (Deepseek):\n{deepseek\_text}\n\n"
f"Response C (Llama):\n{llama\_text}\n\n"
f"Response D (Grok):\n{grok\_text}\n\n"
f"Response F (Web Search):\n{web\_text}\n\n"
f"🔥 Firebox Final Answer:"
)
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate\_content(prompt)
return "".join(\[p.text for p in response.parts])
except Exception as e:
return f"❌ Merge error: {e}"

# === Web Search ===

def search\_web(query):
try:
url = f"[https://www.google.com/search?q={query}](https://www.google.com/search?q={query})"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers)
res.raise\_for\_status()  # Raise HTTPError for bad responses
soup = BeautifulSoup(res.text, "html.parser")
snippets = soup.select("div.BNeawe.s3v9rd.AP7Wnd")
texts = \[s.get\_text() for s in snippets\[:3]]
return "\n\n🌐 Web Results:\n" + "\n".join(texts) if texts else "No search results found."
except requests.exceptions.RequestException as e:
return f"❌ Web search failed: {e}"
except Exception as e:
return f"❌ Error processing web search results: {e}"

# === Custom CSS for Fixed Bottom Input with Icon ===

custom\_css = """

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
st.markdown(custom\_css, unsafe\_allow\_html=True)

# === Streamlit UI ===

st.title("🔥 Firebox AI – Ultimate Assistant")

# Move the chat history display to the top

display\_chat\_history()

# Fixed input at the bottom

user\_input = st.text\_input("Your Query:", key="fixed\_input")

# Footer message

st.markdown('<div id="firebox-footer">Firebox can make mistakes. <span style="font-weight: bold;">Help it improve.</span></div>', unsafe\_allow\_html=True)

# === Response Logic ===

if user\_input:
perform\_web\_search = False
\# Check if the web search icon was "clicked" (we'll simulate this)
if st.session\_state.get('web\_search\_clicked'):
perform\_web\_search = True
st.session\_state\['web\_search\_clicked'] = False  # Reset the state

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
st.markdown(f"**Firebox:** {final_output}") is of 326 lines, and without changing or deleting anything in my main code just extend my code, just add this code import streamlit as st
