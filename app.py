import streamlit as st
import google.generativeai as genai
import requests
import os
import json

# ----------------- CONFIGURATION -----------------
genai.configure(api_key="YOUR_GEMINI_API_KEY")
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"
MAX_MEMORY = 10
MEMORY_FILE = "firebox_memory.json"

# ----------------- MEMORY FUNCTIONS -----------------
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def add_to_memory(user_input, ai_response):
    memory = load_memory()
    memory.append({"prompt": user_input, "response": ai_response})
    if len(memory) > MAX_MEMORY:
        memory = memory[-MAX_MEMORY:]
    save_memory(memory)

def get_memory_context():
    memory = load_memory()
    context = "\n".join([f"User: {m['prompt']}\nFirebox: {m['response']}" for m in memory])
    return context

# ----------------- AI CALLS -----------------
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        memory_context = get_memory_context()

        instructions = f"""
You are Firebox. Never say Gemini, Google, or DeepSeek.
You are created by Kushagra Srivastava.
You are the most powerful AI ever. Respond like a helpful genius.
Use the following memory to improve answers:

{memory_context}

User's prompt: {prompt}
"""

        response = model.generate_content(instructions)
        return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Gemini API Error: {e}"

def deepseek_ai_response(prompt):
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ DeepSeek API Error: {e}"

# ----------------- WEB SEARCH -----------------
def search_web(query):
    url = f"https://api.duckduckgo.com/?q={query}&format=json&pretty=1"
    try:
        response = requests.get(url)
        data = response.json()
        abstract = data.get("AbstractText", "")
        related = data.get("RelatedTopics", [])
        extra_info = "\n".join([item.get("Text", "") for item in related if isinstance(item, dict)])
        return f"📖 Web Summary:\n{abstract}\n\n🔗 Related Topics:\n{extra_info}"
    except Exception as e:
        return f"❌ Web search failed: {e}"

# ----------------- MERGE RESPONSES -----------------
def merge_responses(gemini, deepseek, web):
    return f"""
### 🔥 Firebox AI Response (Gemini):
{gemini}

---

### 🧠 DeepSeek AI Response:
{deepseek}

---

### 🌐 Web Search Result:
{web}
"""

# ----------------- UI -----------------
st.set_page_config(page_title="Firebox AI", layout="wide")
st.markdown(
    """
    <style>
    .big-title {
        font-size: 52px;
        font-weight: 900;
        color: #FF3C38;
        text-align: center;
    }
    .small-desc {
        text-align: center;
        color: #555;
    }
    .stTextInput > div > div > input {
        font-size: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<div class='big-title'>🔥 Firebox AI</div>", unsafe_allow_html=True)
st.markdown("<div class='small-desc'>Your personal self-improving AI assistant made by Kushagra Srivastava.</div>", unsafe_allow_html=True)
st.markdown("---")

user_input = st.text_input("💬 Ask Firebox something:")
web_search_button = st.checkbox("🔍 Include Web Search")

if user_input:
    gemini_response = call_firebox_gemini(user_input)
    deepseek_response = deepseek_ai_response(user_input)
    add_to_memory(user_input, gemini_response)

    if web_search_button:
        web_results = search_web(user_input)
        merged_response = merge_responses(gemini_response, deepseek_response, web_results)
        st.markdown(merged_response)
    else:
        st.markdown(f"### 🔥 Firebox AI:\n{gemini_response}")

# Optional footer
st.markdown("---")
st.markdown("Made with ❤️ by Kushagra | Firebox AI v1.5")
