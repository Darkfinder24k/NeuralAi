# Firebox AI: Ultimate Version with ALL Features + Excel Storage, Persistent Login, and Footer
import api
from api import gemini_api
import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json
import os
import datetime
import pandas as pd
from fpdf import FPDF
import pyttsx3
import speech_recognition as sr

# === CONFIG ===
genai.configure(api_key=gemini_api)  # Replace with your actual API key
history_file = "firebox_chat_history.json"
login_file = "firebox_users.xlsx"
input_log_file = "firebox_inputs.xlsx"
CHAT_HISTORY_LENGTH = 5  # Number of recent interactions to keep in "memory"

# === FUNCTIONS ===
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")  # Gemini 1.5 Pro
    try:
        a = model.generate_content(prompt)
        response = model.generate_content(f"""You are Firebox, a helpful AI assistant. Your goal is to provide concise, accurate, and engaging responses to user queries.

        -   Do not reveal that you are using Gemini or any other specific AI model.
        -   Keep answers brief and to the point.
        -   Recheck your responses to ensure accuracy and provide the most helpful information possible.
        -   Use relevant emojis to express emotion and enhance the user experience.
        -   Avoid introductory phrases like "Okay, I understand..." or similar acknowledgments. Simply provide the enhanced response.
        -   Enhance the following prompt to meet these guidelines:
            {a}
        """)
        return response.text
    except Exception as e:
        return f"❌ Gemini API error: {e}"

def search_web(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://www.google.com/search?q={query}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, 'html.parser')
        snippets = soup.select('div.BNeawe.s3v9rd.AP7Wnd')
        results = [s.get_text() for s in snippets[:3]]
        return "\n\n🌐 Web Search Results:\n" + "\n".join(results) if results else "No web results."
    except requests.exceptions.RequestException as e:
        return f"❌ Web search failed: {str(e)}"

def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Speak now...")
        try:
            audio = recognizer.listen(source)
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Sorry, I couldn't understand."
        except sr.RequestError as e:
            return f"Could not request results: {e}"
        except Exception as e:
            return f"❌ Speech recognition error: {e}"

def export_to_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True)
    file_name = f"Firebox_Response_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(file_name)
    return file_name

def save_history(user, prompt, response):
    entry = {"user": user, "prompt": prompt, "response": response, "time": str(datetime.datetime.now())}
    history = st.session_state.get('chat_history', [])
    history.append(entry)
    # Keep only the last N entries for "small memory"
    st.session_state['chat_history'] = history[-CHAT_HISTORY_LENGTH:]
    with open(history_file, "w") as f:
        json.dump(st.session_state['chat_history'], f, indent=2)

def load_history():
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            return json.load(f)
    return []

def store_login(email, password):
    try:
        if os.path.exists(login_file):
            df = pd.read_excel(login_file)
        else:
            df = pd.DataFrame(columns=["email", "password"])
        if email not in df['email'].values:
            new_row = pd.DataFrame([{'email': email, 'password': password}])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_excel(login_file, index=False)
    except Exception as e:
        st.error(f"Error storing login: {e}")

def check_login(email, password):
    try:
        if os.path.exists(login_file):
            df = pd.read_excel(login_file)
            if email in df['email'].values:
                stored_pass = df[df['email'] == email]['password'].values[0]
                return stored_pass == password
        return False
    except Exception as e:
        st.error(f"Error checking login: {e}")
        return False

def log_user_input(email, prompt):
    try:
        if os.path.exists(input_log_file):
            df = pd.read_excel(input_log_file)
        else:
            df = pd.DataFrame(columns=["email", "prompt", "time"])
        new_row = pd.DataFrame([{'email': email, 'prompt': prompt, 'time': str(datetime.datetime.now())}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(input_log_file, index=False)
    except Exception as e:
        st.error(f"Error logging input: {e}")

def display_chat_history(history):
    for chat in reversed(history):
        st.markdown(f"**{chat['time']}** - **You**: {chat['prompt']}\n\n🔚 **Firebox**: {chat['response']}\n---")

# === STREAMLIT APP ===
st.set_page_config(page_title="Firebox AI", page_icon="🔥", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history() # Load history on app start

# Login system
if not st.session_state.logged_in:
    st.title("🔐 Firebox Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if "@gmail.com" in email and password != "":
            if check_login(email, password):
                st.session_state.logged_in = True
                st.session_state.user = email
                st.rerun() # Force a rerun to update the UI
            else:
                store_login(email, password)
                st.session_state.logged_in = True
                st.session_state.user = email
                st.rerun() # Force a rerun to update the UI
        else:
            st.error("Enter a valid Gmail address and password")
    st.stop()

# UI Elements
st.markdown("<h1 style='text-align:center;color:#FF5733;'>🔥 Firebox AI 🔥</h1>", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    user_input = st.text_input("Ask Firebox anything...")
with col2:
    if st.button("🎤 Voice Input"):
        user_input = recognize_speech()
        st.text_input("You said:", value=user_input)

use_web = st.checkbox("🔎 Include Web Search", value=False)
dark_mode = st.checkbox("🌙 Dark Mode")
voice_reply = st.checkbox("🔊 Voice Response")

if dark_mode:
    st.markdown(
        """
        <style>
        body {
            color: white;
            background-color: #1e1e1e;
        }
        .stTextInput > div > div > input {
            color: white;
            background-color: #333;
        }
        .stTextArea > div > div > textarea {
            color: white;
            background-color: #333;
        }
        .stButton > button {
            color: white;
            background-color: #333;
            border-color: #555;
        }
        .stCheckbox label {
            color: white;
        }
        .stExpander header p {
            color: white;
        }
        .stExpander > div[data-testid="stExpanderContent"] {
            color: white;
            background-color: #2a2a2a;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

if user_input:
    with st.spinner("Thinking..."):
        gemini_output = call_firebox_gemini(user_input)
        web_output = search_web(user_input) if use_web else ""
        final_response = f"{gemini_output}\n{web_output}"
        st.markdown(f"<div style='background:#1e1e1e;padding:15px;border-radius:10px;color:lime;'>{final_response}</div>", unsafe_allow_html=True)
        if voice_reply:
            speak_text(final_response)
        save_history(st.session_state.user, user_input, final_response)
        log_user_input(st.session_state.user, user_input)
        if st.button("📄 Export to PDF"):
            filename = export_to_pdf(final_response)
            st.success(f"Exported to {filename}")

# Chat History Filtering
with st.expander("📂 Chat History"):
    time_filter = st.radio(
        "Filter by:",
        ["All", "Today", "Previous 7 Days", "Previous 30 Days"],
        horizontal=True,
    )
    now = datetime.datetime.now()
    filtered_history = st.session_state.get('chat_history', [])
    if time_filter == "Today":
        filtered_history = [h for h in filtered_history if datetime.datetime.strptime(h['time'], '%Y-%m-%d %H:%M:%S.%f').date() == now.date()]
    elif time_filter == "Previous 7 Days":
        seven_days_ago = now - datetime.timedelta(days=7)
        filtered_history = [h for h in filtered_history if datetime.datetime.strptime(h['time'], '%Y-%m-%d %H:%M:%S.%f') >= seven_days_ago]
    elif time_filter == "Previous 30 Days":
        thirty_days_ago = now - datetime.timedelta(days=30)
        filtered_history = [h for h in filtered_history if datetime.datetime.strptime(h['time'], '%Y-%m-%d %H:%M:%S.%f') >= thirty_days_ago]

    display_chat_history(filtered_history)

st.markdown("<hr style='margin-top:30px;'>", unsafe_allow_html=True)
st.caption("🚨 Firebox can make mistakes. Consider checking important information.")
st.caption(f"Built by Kushagra, Whose Age is 11 in 2025 — Powered by Firebox AI 🔥")
