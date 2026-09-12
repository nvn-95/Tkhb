import streamlit as st
import streamlit.components.v1 as components
from asl_1 import text_to_gloss

# UI Configuration
st.set_page_config(page_title="SignAI | Avatar & Gloss", layout="centered")

# The Full UI (Avatar + Gloss + Input)
html_code = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0f0f13; --card: #1a1a21; --primary: #6366f1; --accent: #8b5cf6; }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { 
            background: var(--bg); 
            color: white; 
            font-family: 'Outfit', sans-serif; 
            text-align: center; 
            min-height: 100vh; 
            display: flex; flex-direction: column; align-items: center; justify-content: center; 
            overflow: hidden;
        }
        
        .header { margin-bottom: 25px; font-size: 2.2rem; font-weight: 600; background: linear-gradient(to right, #fff, var(--primary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        /* ── AVATAR VIEWER ── */
        .avatar-container {
            width: 90%; max-width: 600px; height: 320px; background: #000; border-radius: 20px;
            margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.08); position: relative;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6); overflow: hidden;
            display: flex; align-items: center; justify-content: center;
        }
        
        /* ── GLOSS TRANSLATION BANNER ── */
        .gloss-banner {
            background: var(--card); border-radius: 18px; padding: 25px; width: 90%; max-width: 600px;
            margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1); 
            box-shadow: 0 10px 20px rgba(0,0,0,0.4);
        }
        .gloss-text { font-family: 'JetBrains Mono', monospace; font-size: 2rem; color: var(--primary); text-transform: uppercase; letter-spacing: 0.1em; text-shadow: 0 0 10px rgba(99, 102, 241, 0.5); }
        
        /* ── INPUT BOX ── */
        .input-group { background: var(--card); border-radius: 15px; display: flex; padding: 6px; width: 90%; max-width: 600px; border: 1px solid rgba(255,255,255,0.15); }
        input { flex: 1; background: transparent; border: none; color: white; padding: 12px; font-size: 1.1rem; outline: none; }
        .btn-go { background: var(--primary); color: white; border-radius: 10px; border:none; padding: 0 25px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .btn-go:hover { transform: scale(1.05); background: #4f46e5; }

        .status { margin-top: 15px; color: #555; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="header">SignAI | ISL Avatar</div>

    <div class="avatar-container">
        <div style="color:#222; font-size:4.5rem;">🤖</div>
        <div style="position:absolute; bottom:20px; color:#333; font-size:0.8rem; letter-spacing: 3px;">3D AVATAR PLAYER</div>
    </div>

    <div class="gloss-banner">
        <div id="gloss-output" class="gloss-text">YOUR GLOSS RESULT</div>
    </div>

    <div class="input-group">
        <input type="text" id="text-input" placeholder="Type a sentence (e.g., 'I want water')">
        <button class="btn-go" id="go-btn">TRANSLATE</button>
    </div>

    <div class="status" id="status-bar">Waiting for input...</div>

    <script>
        const textInput = document.getElementById('text-input');
        const goBtn = document.getElementById('go-btn');
        const glossOutput = document.getElementById('gloss-output');
        const statusBar = document.getElementById('status-bar');

        function sendToStreamlit(text) {
            if(!text) return;
            statusBar.textContent = "Processing...";
            const url = new URL(window.parent.location.href);
            url.searchParams.set("query", text);
            window.parent.location.href = url.toString();
        }

        goBtn.onclick = () => sendToStreamlit(textInput.value);
        textInput.onkeypress = (e) => { if (e.key === 'Enter') sendToStreamlit(textInput.value); };
    </script>
</body>
</html>
"""

# Get prediction from URL query
query_params = st.query_params
user_text = query_params.get("query", "")

if user_text:
    gloss_list = text_to_gloss(user_text)
    gloss = " ".join(gloss_list)
    # Inject the Gloss results into the HTML
    final_html = html_code.replace("YOUR GLOSS RESULT", gloss).replace('placeholder="Type a sentence (e.g., \'I want water\')"', f'value="{user_text}"')
    components.html(final_html, height=850)
else:
    components.html(html_code, height=850)

# Hide Streamlit elements for a clean app look
st.markdown("<style>#MainMenu, footer, header {visibility: hidden;}</style>", unsafe_allow_html=True)

