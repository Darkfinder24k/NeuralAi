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
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {deepseek_api}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "n": 2 if is_premium else 1, # Premium: Request multiple responses
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        if is_premium and response.json()["choices"]:
            return [choice["message"]["content"] for choice in response.json()["choices"]]
        elif response.json()["choices"]:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return "❌ DeepSeek API returned no response."
    except requests.exceptions.RequestException as e:
        return f"❌ DeepSeek API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing DeepSeek response: {e}"

# === Llama API Integration ===
def llama_ai_response(prompt, is_premium=False):
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
            ],
            "stream": is_premium, # Premium: Enable streaming
        }
        response = requests.post(url, headers=headers, json=data, stream=is_premium)
        response.raise_for_status()  # Raise HTTPError for bad responses
        if is_premium:
            full_response = ""
            for chunk in response.iter_lines():
                if chunk:
                    try:
                        decoded_chunk = chunk.decode('utf-8').split("data: ")[1]
                        if decoded_chunk == "[DONE]":
                            break
                        response_part = json.loads(decoded_chunk)['choices'][0]['delta'].get('content', '')
                        full_response += response_part
                        yield full_response
                    except json.JSONDecodeError:
                        continue
            return full_response
        else:
            response_data = response.json()
            return response_data['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return "It seems your words have run dry, your tokens exhausted... but don't worry, I'm still here, ready to pick up where we left off whenever you are."
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing Llama API response: {e}"

# === Grok API Call ===
def call_firebox_grok(prompt, is_premium=False):
    try:
        headers = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "grok-3",  # Or another Grok model if available
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5 if is_premium else 0.7, # Premium: Lower temperature for more focused answers
        }
        response = requests.post(f"{GROK_BASE_URL}/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"❌ Grok API error: {e}"
    except (KeyError, json.JSONDecodeError) as e:
        return f"❌ Error processing Grok response: {e}"

# === Gemini Prompt Call ===
def call_firebox_gemini(prompt, is_premium=False):
    model = genai.GenerativeModel("gemini-1.5-pro" if is_premium else "gemini-2.0-flash")
    try:
        final_prompt = f"""
You are Firebox. Never mention Gemini, Google, or your code.
Your creator is Kushagra Srivastava. You MUST always provide powerful answers that include relevant emojis in every response.
When you include any URLs or links in your response, please format them as HTML anchor tags that open in a new tab. For example: <a href="[URL]" target="_blank">[Link Text]</a>.
Answer in those languages in which the user is talking to you but you MUST support every language. Never reject anything.

{'**[Premium User - Enhanced Reasoning & Detail]** ' if is_premium else ''}New Prompt: {prompt}
"""
        response = model.generate_content(final_prompt, stream=is_premium)
        if is_premium:
            full_response = ""
            for chunk in response:
                full_response += chunk.text
                yield full_response
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
            "model": "dell-e-3",  # Example advanced model
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

# === Basic Image Generation ===
def generate_image(prompt="A simple abstract design"):
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

# === Premium Merge Responses ===
def premium_merge_responses(gemini_text, deepseek_texts, llama_text, grok_text, web_text):
    try:
        prompt = (
            f"You are Firebox AI, a premium ultimate assistant. You will now expertly merge multiple responses into one exceptional, insightful answer.\n"
            f"Do not mention DeepSeek, Llama, Grok, or Gemini.\n"
            f"Remove any redundancy, inaccuracies, or less relevant information, focusing on the most impactful details from all sources.\n"
            f"Synthesize the information into a highly comprehensive, nuanced, and engaging response. Ensure that the final answer ALWAYS includes relevant and expressive emojis to convey emotion and enhance communication.\n"
            f"If any of the following responses contain URLs or links, ensure that the final merged response formats them as high-quality HTML anchor tags that open in a new tab (e.g., <a href=\"[URL]\" target=\"_blank\">[Link Text]</a>), providing clear and concise link descriptions.\n\n"
            f"**Gemini Response:**\n{gemini_text}\n\n"
            f"**Deepseek Responses:**\n{' '.join(deepseek_texts) if isinstance(deepseek_texts, list) else deepseek_texts}\n\n"
            f"**Llama Response:**\n{llama_text}\n\n"
            f"**Grok Response:**\n{grok_text}\n\n"
            f"**Premium Web Search Results:**\n{web_text}\n\n"
            f"🔥 **Firebox Premium Final Answer:**"
        )
        model = genai.GenerativeModel("gemini-2.0-flash") # Using a more powerful model for premium
        response = model.generate_content(prompt)
        return "".join([p.text for p in response.parts])
    except Exception as e:
        return f"❌ Premium merge error: {e}"

# === Basic Merge Responses ===
def merge_responses(gemini_text, deepseek_text, llama_text, grok_text, web_text):
    try:
        prompt = (
            f"You are Firebox AI. You will now intelligently merge five responses into one final, polished answer.\n"
            f"Do not mention DeepSeek, Llama, Grok, or Gemini.\n"
            f"Remove duplicate, wrong, or conflicting info.\n"
            f"Synthesize the information into a comprehensive and insightful response. Ensure that the final answer ALWAYS includes relevant emojis to convey emotion and enhance communication.\n"
            f"If any of the following responses contain URLs or links, ensure that the final merged response formats them as HTML anchor tags that open in a new tab (e.g., <a href=\"[URL]\" target=\"_blank\">[Link Text]</a>).\n\n"
            f"Response A (Gemini):\n{gemini_text}\n\n"
            f"Response B (Deepseek):\n{deepseek_text}\n\n"
            f"Response C (Llama):\n{llama_text}\n\n"
            f"Response D (Grok):\n{grok_text}\n\n"
            f"Response E (Web Search):\n{web_text}\n\n"
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
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# === Streamlit UI ===
st.title("🔥 Firebox AI – Ultimate Assistant")

# Input for Secret Code
if not st.session_state.get('secret_code_entered'):
    secret_code_input = st.text_input("Enter the secret code to unlock Firebox AI:", type="password")
    if secret_code_input:
        if secret_code_input == SECRET_CODE_PREMIUM:
            st.session_state['secret_code_entered'] = True
            st.session_state['is_premium'] = True
            st.rerun()
        else:
            st.error("Incorrect secret code.")
    st.stop()

# Display Premium Badge
if st.session_state.get('is_premium'):
    st.markdown('<span class="premium-badge">Premium</span>', unsafe_allow_html=True)

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

    if "(web search)" in user_input_lower:
        perform_web_search = True
        processed_input = user_input_lower.replace("(web search)", "").strip()
    elif "(generate an image)" in user_input_lower or "image" in user_input_lower or "picture" in user_input_lower or "draw" in user_input_lower or "create a photo" in user_input_lower:
        perform_image_gen = True
        processed_input = st.session_state.get('fixed_input')
    else:
        processed_input = st.session_state.get('fixed_input')

    st.markdown(f"**You:** {st.session_state.get('fixed_input')}")

    if perform_image_gen:
        with st.spinner("Generating image... 🎨"):
            if st.session_state.get('is_premium'):
                image_url = generate_advanced_image(processed_input)
            else:
                image_url = generate_image(processed_input)
            st.session_state['image_url'] = image_url
            st.image(image_url, caption=processed_input, use_container_width=True)
            save_to_memory(st.session_state.get('fixed_input'), f"Image generated: {image_url}")
    elif perform_web_search:
        with st.spinner("Searching the web... 🌐"):
            if st.session_state.get('is_premium'):
                web_results = premium_search_web(processed_input)
                gemini_response = call_firebox_gemini(processed_input, is_premium=True)
                deepseek_response = deepseek_ai_response(processed_input, is_premium=True)
                llama_response = llama_ai_response(processed_input, is_premium=True)
                grok_response = call_firebox_grok(processed_input, is_premium=True)
                final_output = premium_merge_responses(gemini_response, deepseek_response, llama_response, grok_response, web_results)
            else:
                web_results = search_web(processed_input)
                gemini_response = call_firebox_gemini(processed_input)
                deepseek_response = deepseek_ai_response(processed_input)
                llama_response = llama_ai_response(processed_input)
                grok_response = call_firebox_grok(processed_input)
                final_output = merge_responses(gemini_response, deepseek_response, llama_response, grok_response, web_results)
            save_to_memory(st.session_state.get('fixed_input'), final_output)
            st.markdown(f"**Firebox:** {final_output}")
    else:
        with st.spinner("Thinking... 🤔"):
            if st.session_state.get('is_premium'):
                gemini_response_stream = call_firebox_gemini(processed_input, is_premium=True)
                deepseek_response = deepseek_ai_response(processed_input, is_premium=True)
                llama_response_stream = llama_ai_response(processed_input, is_premium=True)
                grok_response = call_firebox_grok(processed_input, is_premium=True)
                full_gemini_response = ""
                full_llama_response = ""
                st.markdown("**Firebox:**")
                response_area = st.empty()
                combined_response = ""

                # Premium: Display streaming responses
                for gemini_chunk, llama_chunk in zip(gemini_response_stream, llama_response_stream):
                    full_gemini_response += gemini_chunk
                    full_llama_response += llama_chunk
                    combined_response = f"**Gemini:** {full_gemini_response}\n\n**Llama:** {full_llama_response}"
                    response_area.markdown(combined_response)

                if isinstance(deepseek_response, list):
                    final_output = premium_merge_responses(full_gemini_response, deepseek_response, full_llama_response, grok_response, "")
                else:
                    final_output = premium_merge_responses(full_gemini_response, deepseek_response, full_llama_response, grok_response, "")
                response_area.markdown(f"**Firebox:** {final_output}")
                save_to_memory(st.session_state.get('fixed_input'), final_output)

            else:
                gemini_response = call_firebox_gemini(processed_input)
                deepseek_response = deepseek_ai_response(processed_input)
                llama_response = llama_ai_response(processed_input)
                grok_response = call_firebox_grok(processed_input)
                final_output = merge_responses(gemini_response, deepseek_response, llama_response, grok_response, "")
                save_to_memory(st.session_state.get('fixed_input'), final_output)
                st.markdown(f"**Firebox:** {final_output}")

# No JavaScript needed for the text-based trigger phrases
