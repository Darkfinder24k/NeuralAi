# Firebox AI: Ultimate Version with ALL Features + Excel Storage, Persistent Login, and Footer

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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import api
from api import gemini_api
import apppassword
from apppassword import password

# === CONFIG ===
genai.configure(api_key=gemini_api)  # API key is in api.py
history_file = "firebox_chat_history.json"
login_file = "firebox_users.xlsx"
input_log_file = "firebox_inputs.xlsx"
CHAT_HISTORY_LENGTH = 5  # Number of recent interactions to keep in "memory"

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USERNAME = "shivikush77@gmail.com"  # Your Gmail address
SMTP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")  # Store securely as environment variable

# === FUNCTIONS ===

# --- Gemini Interaction ---
def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-1.5-pro-latest")  # Use the latest model
    try:
        response = model.generate_content(f"""You are Firebox, a helpful AI assistant. Your goal is to provide concise, accurate, and engaging responses to user queries.

        -   Do not reveal that you are using Gemini or any other specific AI model.
        -   Keep answers brief and to the point.
        -   Recheck your responses to ensure accuracy and provide the most helpful information possible.
        -   Use relevant emojis to express emotion and enhance the user experience.
        -   Avoid introductory phrases like "Okay, I understand..." or similar acknowledgments. Simply provide the enhanced response.
        -   Enhance the following prompt to meet these guidelines:
            {prompt}
        """)
        return response.text
    except Exception as e:
        st.error(f"❌ Gemini API error: {e}")
        print(f"Gemini API error: {e}")  # Log the error
        return "❌ Gemini API error. Please try again."

# --- Web Search ---
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
        st.error(f"❌ Web search failed: {str(e)}")
        print(f"Web search failed: {str(e)}")  # Log the error
        return f"❌ Web search failed: {str(e)}"

# --- Text-to-Speech ---
def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# --- Speech Recognition ---
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

# --- PDF Export ---
def export_to_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split('\n'):
        pdf.cell(200, 10, txt=line, ln=True)
    file_name = f"Firebox_Response_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(file_name)
    return file_name

# --- Chat History Management ---
def save_history(user, prompt, response):
    entry = {"user": user, "prompt": prompt, "response": response, "time": str(datetime.datetime.now())}
    history = st.session_state.get('chat_history', [])
    history.append(entry)
    # Keep only the last N entries for "small memory"
    st.session_state['chat_history'] = history[-CHAT_HISTORY_LENGTH:]
    try:
        with open(history_file, "w") as f:
            json.dump(st.session_state['chat_history'], f, indent=2)
    except Exception as e:
        st.error(f"Error saving chat history: {e}")
        print(f"Error saving chat history: {e}")

def load_history():
    try:
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading chat history: {e}")
        print(f"Error loading chat history: {e}")
    return []

# --- User Authentication ---
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
        print(f"Error storing login: {e}")

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
        print(f"Error checking login: {e}")
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
        print(f"Error logging input: {e}")

# --- OTP Generation and Email Sending ---
def generate_otp(length=6):
    return ''.join(random.choices('0123456789', k=length))

def send_otp_via_email(recipient_email, otp):
    sender_name = "NeuralAi"
    sender_email = SMTP_USERNAME
    subject = "NeuralAi OTP Verification"
    body = f"Your OTP is: {otp}"

    message = MIMEMultipart()
    message['From'] = f'{sender_name} <{sender_email}>'
    message['To'] = recipient_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(sender_email, recipient_email, message.as_string())
        st.success(f"OTP sent to {recipient_email}")
        return True
    except Exception as e:
        st.error(f"Error sending OTP: {e}")
        print(f"Error sending OTP to {recipient_email}: {e}")
        return False

# --- Chat History Display ---
def display_chat_history(history):
    for chat in reversed(history):
        st.markdown(f"**{chat['time']}** - **You**: {chat['prompt']}\n\n🔚 **Firebox**: {chat['response']}\n---")

# === STREAMLIT APP ===
st.set_page_config(page_title="Firebox AI", page_icon="🔥", layout="wide")

# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history()  # Load history on app start
if "otp" not in st.session_state:
    st.session_state.otp = None
if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = {} # Track login attempts per email
if "login_email_attempt" not in st.session_state:
    st.session_state.login_email_attempt = None

# --- Persistent Login ---
def check_persistent_login():
    if "user_email" in st.session_state and st.session_state.user_email:
        if os.path.exists(login_file):
            try:
                df = pd.read_excel(login_file)
                if st.session_state.user_email in df['email'].values:
                    st.session_state.logged_in = True
                    st.session_state.user = st.session_state.user_email
                    return True
            except Exception as e:
                st.error(f"Error reading login file for persistent login: {e}")
        st.session_state.logged_in = False
        st.session_state.user = None
    return False

# --- OTP Verification and Login ---
def login_flow():
    st.title("🔐 Firebox Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if "@gmail.com" in email and password != "":
            if check_login(email, password):
                otp = generate_otp()
                st.session_state.otp = otp
                st.session_state.login_email_attempt = email # Store email for OTP verification
                if send_otp_via_email(email, otp):
                    st.success(f"OTP sent to {email}. Please verify below.")
                else:
                    st.error("Failed to send OTP. Please try again.")
            else:
                st.error("Invalid email or password.")
        else:
            st.error("Enter a valid Gmail address and password")

    if st.session_state.login_email_attempt and st.session_state.otp:
        otp_input = st.text_input(f"Enter the OTP sent to {st.session_state.login_email_attempt}:")
        if st.button("Verify OTP"):
            if otp_input == st.session_state.otp:
                st.session_state.logged_in = True
                st.session_state.user = st.session_state.login_email_attempt
                st.session_state.user_email = st.session_state.login_email_attempt # For persistent login
                st.success("OTP verified. Logged in!")
                st.session_state.otp = None
                st.session_state.login_email_attempt = None
                st.session_state.login_attempts = {} # Reset attempts
                st.rerun()
            else:
                st.error("Invalid OTP. Please try again.")
                st.session_state.login_attempts[st.session_state.login_email_attempt] = st.session_state.login_attempts.get(st.session_state.login_email_attempt, 0) + 1
                if st.session_state.login_attempts.get(st.session_state.login_email_attempt, 0) >= 3:
                    st.warning("Too many failed OTP attempts. Please try logging in again.")
                    st.session_state.otp = None
                    st.session_state.login_email_attempt = None
                    st.session_state.login_attempts = {}
                    st.rerun()
        st.stop()
    elif st.session_state.logged_in:
        st.empty() # Clear login form if already logged in

# --- Check for persistent login on app start ---
if not st.session_state.logged_in:
    if check_persistent_login():
        st.success(f"Welcome back, {st.session_state.user}!")
    else:
        login_flow()

# --- Main App Interface ---
if st.session_state.logged_in:
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

    # --- Dark Mode Styling ---
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

    # --- Main Interaction ---
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

    # --- Chat History Display and Filtering ---
    with st.expander("📂 Chat History"):
        time_filter = st.radio(
            "Filter by:",
            ["All", "Today", "Previous 7 Days", "Previous 30 Days"],
            horizontal=True,
        )
        now = datetime.datetime.now()
        filtered_history = st.session_state.get('chat_history', [])
        if time_filter == "Today":
            filtered_history = [h for h in filtered_history if datetime.datetime.strptime(h['time'], '%Y-%
