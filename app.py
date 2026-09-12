"""
SignAI — ASL Avatar Generator
==============================
Flask backend that converts English text to sign language gloss
and serves the avatar UI.

Usage:
    python app.py
    → Open http://localhost:5000
"""

import os
import sys
from flask import Flask, render_template, request, jsonify

# Import the gloss pipeline (no mediapipe needed)
from asl_1 import text_to_gloss, BVH_MAP

# Automatically find index.html locally or on GitHub
if os.path.exists("templates/index.html"):
    app = Flask(__name__, template_folder="templates")
else:
    app = Flask(__name__, template_folder=".")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/translate", methods=["POST"])
def translate():
    """Accept English text, return ISL gloss tokens."""
    data = request.get_json(silent=True)
    if not data or not data.get("text", "").strip():
        return jsonify({"error": "No text provided"}), 400

    text = data["text"].strip()
    try:
        gloss = text_to_gloss(text)
        return jsonify({
            "status": "success",
            "original_text": text,
            "isl_gloss": gloss,
            "has_sign": {token: token in BVH_MAP for token in gloss},
        })
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/vocabulary")
def vocabulary():
    """Return the full list of supported sign words."""
    return jsonify({"words": sorted(BVH_MAP.keys())})


if __name__ == "__main__":
    print("\n[SignAI] Avatar Generator")
    print("  Open http://localhost:5000 in your browser\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
