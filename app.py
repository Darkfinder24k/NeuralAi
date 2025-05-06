import google.generativeai as genai
import requests
import json

def call_firebox_gemini(prompt):
    model = genai.GenerativeModel("gemini-2.5-pro")
    try:
        if "image" in prompt.lower() or "picture" in prompt.lower() or "generate" in prompt.lower() and ("photo" in prompt.lower() or "drawing" in prompt.lower() or "artwork" in prompt.lower()):
            print("🤖 Firebox is processing your image generation request! 🖼️")
            image_url = generate_image(prompt)
            return f"🎨 Here's the image you requested: <a href=\"{image_url}\" target=\"_blank\">View Image</a>"
        else:
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
