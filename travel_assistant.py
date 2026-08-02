#!/usr/bin/env python3
"""
Travel Tripy - AI-Powered Luxury Travel Planner
Copyright (c) 2025 Vrushabh Patil. All Rights Reserved.
Contact: vrushabhpatil97711@gmail.com
"""

import os
import re
import json
import time
import base64
import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import requests
import streamlit as st
import plotly.express as px
import pandas as pd
from dotenv import load_dotenv
from fpdf import FPDF

try:
    import folium
    from streamlit_folium import folium_static
    from geopy.geocoders import Nominatim
    MAPS_AVAILABLE = True
except ImportError:
    MAPS_AVAILABLE = False
    folium = None
    folium_static = None
    Nominatim = None

# Load environment variables (for local .env usage; st.secrets is used for deployed secrets)
load_dotenv()

# Configure Streamlit page
st.set_page_config(
    page_title="Travel Tripy✈️",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# API CONFIGURATION
# =============================================================================
# FIXED: st.secrets[...] raises a hard KeyError/crash if a secret is missing,
# which brings down the *entire* app before anything can render. Using
# st.secrets.get(...) with a fallback lets the app load and show a friendly
# warning instead of a stack trace.
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
# GROQ_MODEL: swapped from "llama-3.1-8b-instant" to "gemma2-9b-it" — same
# free-tier request/day quota, but roughly 2.5x the tokens-per-minute
# allowance (15,000 TPM vs 6,000 TPM as of mid-2026), which gives more
# headroom before hitting 429s during the sequential budget/itinerary/
# local-experience calls. Trade-off is an 8K context window instead of
# 128K, which isn't a constraint for this app's prompt sizes. Change this
# one constant to switch models again later.
GROQ_MODEL = os.getenv("GROQ_MODEL", "gemma2-9b-it")
# NOTE: OPENTRIPMAP_API_KEY was previously loaded but never used anywhere in
# the app. It's kept here (for the real-geocoding improvement suggested
# below) but is optional, so a missing key won't crash startup.
OPENTRIPMAP_API_KEY = st.secrets.get("OPENTRIPMAP_API_KEY", os.getenv("OPENTRIPMAP_API_KEY", ""))


def render_missing_keys_warning():
    """Show a non-fatal warning banner if required API keys are missing."""
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if missing:
        st.warning(
            f"⚠️ Missing API key(s): {', '.join(missing)}. "
            "Add them to your Streamlit secrets (`.streamlit/secrets.toml`) "
            "or a local `.env` file. The app will still load, but AI "
            "generation features will return fallback/default content until "
            "the keys are configured."
        )


# =============================================================================
# CUSTOM CSS
# =============================================================================
def load_css():
    """Load all custom CSS in one place (moved from being scattered across
    multiple render_* functions, which re-injected <style> blocks on every
    Streamlit rerun)."""

    def get_base64_of_bin_file(bin_file):
        try:
            with open(bin_file, 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode()
        except Exception:
            return None

    # FIXED: removed the hardcoded D:\Travel Agent\... absolute Windows path
    # that only ever worked on one developer's machine. Fallback paths are
    # now all relative/deployment-friendly.
    possible_image_paths = [
        "image01.jpg",
        "images/image01.jpg",
        "static/image01.jpg",
        "assets/image01.jpg",
        "background.jpg",
        "images/background.jpg",
        "static/background.jpg",
        "assets/background.jpg",
        "image.jpeg",
        "images/image.jpeg",
        "./image.jpeg",
        "./images/image.jpeg",
        "../image.jpeg",
    ]

    bg_base64 = None
    for image_path in possible_image_paths:
        if os.path.exists(image_path):
            bg_base64 = get_base64_of_bin_file(image_path)
            if bg_base64:
                break

    base_css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700;800;900&family=Cinzel:wght@400;600;700;800;900&family=Montserrat:wght@300;400;500;600;700;800&display=swap');

        /* ===== BASE STYLES ===== */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #2c3e50;
        }

        @keyframes luxuryGradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        @keyframes textGlow {
            0%, 100% {
                text-shadow: 0 0 25px rgba(102, 126, 234, 0.8),
                            0 0 45px rgba(240, 147, 251, 0.4);
            }
            50% {
                text-shadow: 0 0 35px rgba(44, 62, 80, 1),
                            0 0 45px rgba(52, 73, 94, 0.8),
                            0 0 65px rgba(15, 23, 42, 0.4);
            }
        }

        @keyframes floatEmoji {
            0%, 100% {
                transform: translateY(0px) rotate(0deg) scale(1);
                filter: drop-shadow(0 6px 15px rgba(44, 62, 80, 0.5));
            }
            25% {
                transform: translateY(-10px) rotate(-6deg) scale(1.12);
                filter: drop-shadow(0 10px 20px rgba(52, 73, 94, 0.6));
            }
            50% {
                transform: translateY(-6px) rotate(0deg) scale(1.08);
                filter: drop-shadow(0 8px 18px rgba(26, 32, 44, 0.7));
            }
            75% {
                transform: translateY(-8px) rotate(6deg) scale(1.1);
                filter: drop-shadow(0 9px 19px rgba(15, 23, 42, 0.6));
            }
        }

        @keyframes underlineFlow {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .luxury-gradient-title {
            font-family: 'Cinzel', 'Playfair Display', serif;
            font-size: clamp(2.5rem, 8vw, 5rem);
            background: linear-gradient(
            135deg,
            #667eea 0%,
            #764ba2 25%,
            #f093fb 50%,
            #f5576c 75%,
            #667eea 100%
            );
            background-size: 300% 300%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: luxuryGradient 6s ease infinite, textGlow 5s ease-in-out infinite;
            text-align: center;
            margin-bottom: 0.5rem;
            font-weight: 900;
            letter-spacing: 0.08em;
            line-height: 1.1;
            text-transform: uppercase;
            position: relative;
            padding: 0 1rem;
        }

        .title-emoji {
            display: inline-block;
            font-size: clamp(2rem, 6vw, 3.5rem);
            animation: floatEmoji 4s ease-in-out infinite;
            margin-left: clamp(0.5rem, 2vw, 1.2rem);
            vertical-align: middle;
            filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.5));
            text-shadow: 0 3px 8px rgba(0, 0, 0, 0.4);
            transform-origin: center;
        }

        .title-underline {
            height: 4px;
            background: linear-gradient(90deg,
            #667eea,
            #764ba2,
            #f093fb,
            #f5576c,
            #667eea
            );
            background-size: 300% 300%;
            border-radius: 4px;
            animation: underlineFlow 6s ease infinite;
            margin: 1rem auto 2rem auto;
            width: clamp(150px, 40vw, 250px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }

        .feature-card {
            background: linear-gradient(135deg,
                rgba(255, 255, 255, 0.95) 0%,
                rgba(255, 255, 255, 0.85) 100%);
            -webkit-backdrop-filter: blur(15px);
            backdrop-filter: blur(15px);
            border-radius: clamp(15px, 3vw, 20px);
            padding: clamp(1rem, 3vw, 1.5rem);
            margin: clamp(0.25rem, 1vw, 0.5rem);
            min-height: clamp(140px, 25vh, 220px);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            width: 100%;
        }

        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
            background: linear-gradient(135deg,
                rgba(255, 255, 255, 0.98) 0%,
                rgba(255, 255, 255, 0.9) 100%);
        }

        .metric-card {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%);
            color: white;
            border-radius: clamp(15px, 3vw, 20px);
            padding: clamp(0.8rem, 2vw, 1.2rem);
            margin: clamp(0.25rem, 1vw, 0.5rem);
            text-align: center;
            -webkit-backdrop-filter: blur(10px);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            min-height: clamp(80px, 15vh, 120px);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .experience-card {
            background: rgba(255, 255, 255, 0.95);
            -webkit-backdrop-filter: blur(15px);
            backdrop-filter: blur(15px);
            border-radius: clamp(15px, 3vw, 20px);
            padding: clamp(1rem, 3vw, 1.5rem);
            margin: 0.5rem auto;
            width: 95%;
            max-width: 1000px;
            min-height: clamp(150px, 20vh, 200px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            border-left: clamp(4px, 1vw, 6px) solid #667eea;
            border: 1px solid rgba(255, 255, 255, 0.3);
            transition: all 0.3s ease;
        }

        .experience-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
        }

        .day-card {
            background: linear-gradient(135deg, rgba(240, 147, 251, 0.9) 0%, rgba(245, 87, 108, 0.9) 100%);
            color: white;
            border-radius: clamp(15px, 3vw, 20px);
            padding: clamp(1rem, 3vw, 1.5rem);
            margin: 0.5rem auto;
            width: 95%;
            max-width: 1000px;
            min-height: clamp(120px, 15vh, 180px);
            -webkit-backdrop-filter: blur(10px);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        }

        .sidebar .sidebar-content {
            background: linear-gradient(180deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.95) 100%);
            -webkit-backdrop-filter: blur(20px);
            backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
        }

        .stButton>button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: clamp(10px, 2vw, 15px);
            padding: clamp(0.6rem, 2vw, 0.75rem) clamp(1rem, 3vw, 2rem);
            font-weight: 600;
            font-size: clamp(0.9rem, 2vw, 1rem);
            transition: all 0.3s ease;
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
            width: 100%;
        }

        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(102, 126, 234, 0.4);
        }

        .stSelectbox, .stTextInput, .stNumberInput, .stDateInput {
            background: rgba(255, 255, 255, 0.9);
            border-radius: clamp(8px, 2vw, 12px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            font-size: clamp(0.9rem, 2vw, 1rem);
        }

        .stSelectbox>div>div,
        .stTextInput>div>div>input,
        .stNumberInput>div>div>input,
        .stDateInput>div>div>input {
            font-size: clamp(0.9rem, 2vw, 1rem) !important;
        }

        .section-title {
            font-size: clamp(1.5rem, 5vw, 2.2rem);
            background: linear-gradient(135deg, #4a5d7a 0%, #5a4a7a 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin: clamp(1rem, 3vw, 2rem) 0;
            font-weight: 700;
            line-height: 1.2;
        }

        .feature-icon {
            font-size: clamp(2rem, 5vw, 2.8rem);
            margin-bottom: clamp(0.5rem, 2vw, 1rem);
        }

        .feature-title {
            font-size: clamp(1rem, 3vw, 1.3rem);
            color: #2c3e50;
            margin-bottom: clamp(0.3rem, 1vw, 0.5rem);
            font-weight: 600;
            line-height: 1.3;
        }

        .feature-desc {
            font-size: clamp(0.8rem, 2vw, 0.95rem);
            color: #555555;
            line-height: 1.4;
        }

        .travel-motivation {
            font-family: 'Playfair Display', serif;
            font-size: clamp(1.5rem, 4vw, 2.5rem);
            font-weight: 800;
            text-align: center;
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 50%, #2c3e50 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 3px 3px 12px rgba(0,0,0,0.3);
            line-height: 1.3;
            margin: clamp(1rem, 3vw, 1.5rem) 0 clamp(1.5rem, 4vw, 2.5rem) 0;
            padding: clamp(1rem, 3vw, 1.5rem);
            background-color: rgba(255,255,255,0.05);
            border-radius: clamp(15px, 4vw, 25px);
            -webkit-backdrop-filter: blur(20px);
            backdrop-filter: blur(20px);
            border: 2px solid rgba(44, 62, 80, 0.3);
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            position: relative;
            letter-spacing: -0.01em;
        }

        .travel-motivation::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(44, 62, 80, 0.1) 0%, transparent 50%, rgba(44, 62, 80, 0.1) 100%);
            border-radius: inherit;
            pointer-events: none;
        }

        .travel-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: clamp(0.9rem, 2.5vw, 1.2rem);
            font-weight: 400;
            text-align: center;
            color: #2c3e50;
            margin-bottom: clamp(1.5rem, 4vw, 2.5rem);
            font-style: italic;
            text-shadow: 1px 1px 6px rgba(0,0,0,0.1);
            background: rgba(255, 255, 255, 0.8);
            padding: clamp(0.8rem, 2vw, 1rem) clamp(1rem, 3vw, 2rem);
            border-radius: clamp(10px, 3vw, 15px);
            -webkit-backdrop-filter: blur(10px);
            backdrop-filter: blur(10px);
            line-height: 1.4;
        }

        .premium-features-section {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 249, 250, 0.9) 100%);
            -webkit-backdrop-filter: blur(25px);
            backdrop-filter: blur(25px);
            border-radius: clamp(15px, 4vw, 25px);
            padding: clamp(1rem, 3vw, 2rem);
            margin: clamp(1rem, 3vw, 2rem) auto;
            width: 95%;
            max-width: 1200px;
            border: 2px solid rgba(255, 255, 255, 0.5);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.12);
            position: relative;
            overflow: hidden;
        }

        .premium-features-section::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%);
            pointer-events: none;
        }

        .premium-features-title {
            font-family: 'Playfair Display', serif;
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin: 0 0 clamp(1.5rem, 3vw, 2rem) 0;
            font-weight: 800;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.2);
            letter-spacing: -0.01em;
            line-height: 1.2;
        }

        .progress-bar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
        }

        ::-webkit-scrollbar {
            width: 6px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .fade-in {
            animation: fadeIn 0.6s ease-out;
        }

        .card-content {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
        }

        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }

        button:focus-visible,
        [role="button"]:focus-visible {
            outline: 2px solid #667eea;
            outline-offset: 2px;
        }

        /* ===== Research / Itinerary / Experiences section styles
           (previously injected repeatedly per-tab; consolidated here) ===== */
        .research-container, .itinerary-container {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 2rem;
            margin: 1rem 0;
            color: #2c3e50;
        }
        .research-section {
            background: rgba(255,255,255,0.9);
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1rem 0;
            border-left: 4px solid #667eea;
            color: #2c3e50;
        }
        .research-list-item {
            background: rgba(255,255,255,0.8);
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 10px;
            border-left: 3px solid #764ba2;
            color: #2c3e50;
        }
        .attraction-card, .hidden-gem-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            margin: 1rem 0;
            border-radius: 12px;
            border-left: 5px solid #f093fb;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .destination-image {
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            margin: 1rem 0;
            transition: transform 0.3s ease;
            width: 100%;
            height: 250px;
            object-fit: cover;
        }
        .destination-image:hover {
            transform: scale(1.02);
        }
        .image-caption {
            text-align: center;
            font-style: italic;
            color: #666;
            margin-top: 0.5rem;
            font-size: 0.9rem;
        }
        .images-section {
            background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,249,250,0.9) 100%);
            border-radius: 20px;
            padding: 2rem;
            margin: 2rem 0;
            border: 2px solid rgba(255,255,255,0.5);
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
        .itinerary-day-card {
            background: linear-gradient(135deg, rgba(240, 147, 251, 0.9) 0%, rgba(245, 87, 108, 0.9) 100%);
            color: white;
            border-radius: 20px;
            padding: clamp(1.5rem, 3vw, 2rem);
            margin: 1rem auto;
            width: 95%;
            max-width: 1000px;
            min-height: 180px;
            -webkit-backdrop-filter: blur(10px);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
        }
        .activity-item {
            background: rgba(255,255,255,0.9);
            padding: 0.8rem;
            margin: 0.3rem 0;
            border-radius: 8px;
            color: #2c3e50;
            border-left: 3px solid #667eea;
        }
        .notes-section {
            background: rgba(102, 126, 234, 0.1);
            padding: 1.5rem;
            border-radius: 15px;
            border-left: 4px solid #667eea;
            margin: 1rem 0;
            color: #2c3e50;
        }
        .experience-header {
            color: #000000 !important;
            font-weight: 700;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }
        .special-section {
            background: linear-gradient(135deg, #fff9db, #fff3bf);
            border: 1px solid #ffd8a8;
            border-left: 4px solid #ff922b;
            padding: 1.2rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        .timing-section {
            background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            border: 1px solid #90caf9;
            border-left: 4px solid #1976d2;
            padding: 1.2rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        .tips-section {
            background: linear-gradient(135deg, #e8f5e8, #c8e6c9);
            border: 1px solid #a5d6a7;
            border-left: 4px solid #388e3c;
            padding: 1.2rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        .section-header {
            display: flex;
            align-items: center;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #1a365d;
        }
        .section-icon {
            font-size: 1.2rem;
            margin-right: 0.5rem;
        }
        .tip-item {
            background: rgba(255,255,255,0.7);
            padding: 0.5rem 0.8rem;
            margin: 0.3rem 0;
            border-radius: 6px;
            border-left: 3px solid #4caf50;
        }

        /* ===== ENHANCED MOBILE RESPONSIVENESS ===== */
        @media (max-width: 480px) {
            .luxury-gradient-title {
                font-size: clamp(2rem, 10vw, 3rem);
                letter-spacing: 0.05em;
                padding: 0 0.5rem;
            }
            .title-emoji {
                font-size: clamp(1.8rem, 8vw, 2.5rem);
                margin-left: 0.3rem;
            }
            .title-underline {
                width: clamp(120px, 35vw, 180px);
                margin: 0.8rem auto 1.5rem auto;
            }
            .feature-card {
                min-height: 120px;
                padding: 0.8rem;
                margin: 0.2rem;
            }
            .metric-card {
                min-height: 70px;
                padding: 0.6rem;
            }
            .premium-features-section {
                width: 98%;
                padding: 1rem;
                border-radius: 15px;
                margin: 0.5rem auto;
            }
            .travel-motivation {
                padding: 1rem;
                margin: 1rem 0.5rem;
            }
        }

        @media (max-width: 768px) {
            .luxury-gradient-title {
                font-size: clamp(2.2rem, 8vw, 3.5rem);
                letter-spacing: 0.06em;
            }
            .title-emoji {
                font-size: clamp(2rem, 7vw, 3rem);
                margin-left: 0.5rem;
            }
            .feature-card {
                min-height: 140px;
                padding: 1rem;
                margin: 0.3rem;
            }
            .metric-card {
                min-height: 90px;
                padding: 0.8rem;
            }
            .premium-features-section {
                width: 97%;
                padding: 1.5rem;
                margin: 1rem auto;
            }
            .sidebar .sidebar-content {
                padding: 1rem 0.5rem;
            }
        }

        @media (max-width: 1024px) and (orientation: landscape) {
            .luxury-gradient-title {
                font-size: clamp(2rem, 6vw, 3rem);
            }
            .feature-card {
                min-height: 130px;
            }
            .travel-motivation {
                font-size: clamp(1.3rem, 3vw, 2rem);
                padding: 1rem;
            }
        }

        @media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
            .feature-card, .metric-card, .experience-card, .day-card {
                -webkit-backdrop-filter: blur(30px);
                backdrop-filter: blur(30px);
            }
        }

        @media (prefers-reduced-motion: reduce) {
            .luxury-gradient-title, .title-emoji, .title-underline,
            .feature-card, .experience-card {
                animation: none !important;
                transition: none !important;
            }
        }

        @media (prefers-color-scheme: dark) {
            .stApp {
                background: linear-gradient(135deg, #4a5d7a 0%, #2c3e50 100%);
            }
        }
        </style>
    """

    if bg_base64:
        image_css = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{bg_base64}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
            background-repeat: no-repeat !important;
            background-blend-mode: overlay !important;
        }}
        .stApp::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.7) 0%, rgba(118, 75, 162, 0.7) 100%);
            z-index: -1;
        }}
        .main-container {{
            position: relative;
            z-index: 1;
        }}
        @media (max-width: 768px) {{
            .stApp {{
                background-attachment: scroll !important;
                background-position: center center !important;
            }}
        }}
        </style>
        """
        st.markdown(image_css, unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <style>
            .stApp {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                background-size: cover !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(base_css, unsafe_allow_html=True)


# =============================================================================
# BACKGROUND MUSIC
# =============================================================================
def setup_background_music():
    """Setup background music controls with an autoplay workaround."""
    if 'music_playing' not in st.session_state:
        st.session_state.music_playing = True
    if 'user_interacted' not in st.session_state:
        st.session_state.user_interacted = False

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🎵 Background Music")

        if st.session_state.music_playing:
            if st.session_state.user_interacted:
                st.success("🔊 Music Playing")
            else:
                st.warning("👆 Click anywhere to start music")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Play", use_container_width=True, key="play_btn"):
                st.session_state.music_playing = True
                st.session_state.user_interacted = True
                st.rerun()
        with col2:
            if st.button("⏹️ Stop", use_container_width=True, key="stop_btn"):
                st.session_state.music_playing = False
                st.rerun()


def render_background_music():
    """Music player. Browsers block autoplay until a user gesture occurs;
    the visible fallback button handles that case."""
    if st.session_state.music_playing:

        def get_audio_data_url(audio_path):
            try:
                with open(audio_path, "rb") as audio_file:
                    audio_data = audio_file.read()
                    audio_b64 = base64.b64encode(audio_data).decode()
                    return f"data:audio/mp3;base64,{audio_b64}"
            except Exception:
                return None

        # FIXED: removed the hardcoded D:\Travel Agent\... absolute Windows
        # paths that only worked on one developer's machine.
        possible_audio_paths = [
            "background_music.mp3",
            "audio/background_music.mp3",
            "static/background_music.mp3",
            "assets/background_music.mp3",
            "music.mp3",
            "audio/music.mp3",
            "static/music.mp3",
            "assets/music.mp3",
            "Valleys.mp3",
            "valleys.mp3",
        ]

        local_audio_data_url = None
        for audio_path in possible_audio_paths:
            if os.path.exists(audio_path):
                local_audio_data_url = get_audio_data_url(audio_path)
                if local_audio_data_url:
                    break

        if local_audio_data_url:
            music_sources = [local_audio_data_url]
        else:
            music_sources = [
                "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                "https://assets.mixkit.co/music/preview/mixkit-tech-house-vibes-130.mp3",
            ]

        music_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Background Music</title>
            <style>
                #musicFallback {{
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 10000;
                    background: rgba(102, 126, 234, 0.95);
                    color: white;
                    padding: 12px 16px;
                    border-radius: 10px;
                    border: none;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                }}
                #musicFallback:hover {{
                    background: rgba(102, 126, 234, 1);
                    transform: translateY(-2px);
                }}
            </style>
        </head>
        <body>
            <audio id="backgroundMusic" loop style="display: none;">
                <source src="{music_sources[0]}" type="audio/mp3">
                {f'<source src="{music_sources[1]}" type="audio/mp3">' if len(music_sources) > 1 else ''}
            </audio>

            <div id="musicFallback" style="display: none;">
                <button onclick="playMusic()" style="background: none; border: none; color: white; cursor: pointer; font-size: 14px;">
                    🔊 Click to Play Music
                </button>
            </div>

            <script>
                const audio = document.getElementById('backgroundMusic');
                const fallback = document.getElementById('musicFallback');
                let musicStarted = false;

                audio.volume = 0.3;
                audio.preload = "auto";

                function playMusic() {{
                    if (musicStarted) return;
                    audio.play()
                        .then(() => {{
                            musicStarted = true;
                            fallback.style.display = 'none';
                        }})
                        .catch(() => {{
                            fallback.style.display = 'block';
                        }});
                }}

                function initMusic() {{
                    playMusic();
                    document.addEventListener('click', function handleFirstClick() {{
                        playMusic();
                        document.removeEventListener('click', handleFirstClick);
                    }});
                    document.addEventListener('keydown', function handleFirstKey() {{
                        playMusic();
                        document.removeEventListener('keydown', handleFirstKey);
                    }});
                    setTimeout(() => {{
                        if (!musicStarted) {{
                            fallback.style.display = 'block';
                        }}
                    }}, 2000);
                }}

                if (audio.readyState >= 3) {{
                    initMusic();
                }} else {{
                    audio.addEventListener('canplaythrough', initMusic);
                    audio.addEventListener('loadeddata', initMusic);
                    setTimeout(initMusic, 1000);
                }}

                const retryInterval = setInterval(() => {{
                    if (!musicStarted && audio.readyState >= 3) {{
                        playMusic();
                    }}
                    setTimeout(() => clearInterval(retryInterval), 30000);
                }}, 5000);
            </script>
        </body>
        </html>
        '''
        st.components.v1.html(music_html, height=0)
    else:
        stop_html = '''
        <script>
            const audio = document.getElementById('backgroundMusic');
            if (audio) {
                audio.pause();
                audio.currentTime = 0;
            }
            const fallback = document.getElementById('musicFallback');
            if (fallback) {
                fallback.style.display = 'none';
            }
        </script>
        '''
        st.components.v1.html(stop_html, height=0)


# =============================================================================
# SESSION STATE
# =============================================================================
def init_session_state():
    defaults = {
        'travel_plan': None,
        'research_data': None,
        'budget_data': None,
        'itinerary_data': None,
        'local_experiences': None,
        'plan_generated': False,
        'current_section': 'home',
        'full_plan': None,
        'local_experiences_data': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@dataclass
class TravelPlan:
    destination: str
    budget: float
    duration_days: int
    travel_style: str
    interests: List[str]
    start_date: str


# =============================================================================
# AGENTS
# =============================================================================
class BaseAgent:
    """Base class for all travel agents."""

    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def _extract_retry_after_seconds(response) -> float:
        """Figure out how long to wait before retrying a 429 response.

        Prefers the standard `Retry-After` header; falls back to parsing
        the "Please try again in Xs" hint that Groq/Gemini include in their
        429 error body (e.g. "Please try again in 2.219999999s").
        """
        header_val = response.headers.get("Retry-After") if response is not None else None
        if header_val:
            try:
                return max(float(header_val), 0.5)
            except ValueError:
                pass

        try:
            body = response.text if response is not None else ""
            match = re.search(r'try again in\s+([\d.]+)s', body, re.IGNORECASE)
            if match:
                return max(float(match.group(1)), 0.5)
        except Exception:
            pass

        return 3.0  # sensible default if no hint is present

    def _post_with_retry(self, url: str, headers: Optional[Dict[str, str]], payload: Dict[str, Any],
                          max_retries: int = 4, timeout: int = 60):
        """POST with automatic retry/backoff on HTTP 429 (rate limit).

        Rate limits on free API tiers (e.g. Groq's 6000 TPM) are transient —
        the previous implementation treated a 429 exactly like any other
        error and immediately gave up, falling back to default/sample data.
        This retries a handful of times, waiting the amount of time the API
        itself reports (or an exponential backoff if it doesn't say), so a
        momentary rate-limit bump doesn't need to nuke the whole generation
        step.
        """
        last_response = None
        for attempt in range(max_retries + 1):
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)

            if response.status_code != 429:
                return response

            last_response = response
            if attempt < max_retries:
                wait_seconds = self._extract_retry_after_seconds(response)
                # small buffer on top of the API's own estimate, plus mild
                # growth as a safety net if repeated 429s occur
                wait_seconds = wait_seconds + 0.5 + attempt
                st.info(f"⏳ Rate limit hit — retrying in {wait_seconds:.1f}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_seconds)

        return last_response

    def call_gemini(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call Gemini AI API with error handling and 429 retry/backoff."""
        if not GEMINI_API_KEY:
            return "🔑 Gemini API key not configured. Please check your secrets/.env file"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7,
            },
        }

        try:
            response = self._post_with_retry(url, None, payload)
            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    return data['candidates'][0]['content']['parts'][0]['text']
                return "❌ No content in response from Gemini API"
            return f"❌ Gemini API Error {response.status_code}: {response.text}"
        except requests.exceptions.Timeout:
            return "⏰ Request timeout. Please try again."
        except Exception as e:
            return f"🔴 Gemini Error: {str(e)}"

    def call_groq(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call Groq API for fast responses, with 429 retry/backoff."""
        if not GROQ_API_KEY:
            return "🔑 Groq API key not configured. Please check your secrets/.env file"

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        try:
            response = self._post_with_retry(url, headers, payload)
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                return "❌ No response content from Groq API"
            return f"❌ Groq API Error {response.status_code}: {response.text}"
        except requests.exceptions.Timeout:
            return "⏰ Request timeout. Please try again."
        except Exception as e:
            return f"🔴 Groq Error: {str(e)}"

    def safe_json_parse(self, response: str, agent_type: str) -> Any:
        """Safely parse a JSON response with cleaning and multi-stage recovery.

        FIXED: `re` was previously imported *inside* this method, which only
        binds the name in this method's local scope. `_manual_json_recovery`
        and `_parse_activity_list` called `re.findall(...)` without their own
        import, causing a guaranteed NameError whenever the recovery path
        was hit. `re` is now imported once at module level.
        """
        if response.startswith("❌") or response.startswith("🔴") or response.startswith("⏰"):
            st.error(f"API Error in {agent_type}: {response}")
            return None

        try:
            cleaned_response = response.strip()
            cleaned_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned_response)

            if "```json" in cleaned_response:
                start_index = cleaned_response.find("```json") + len("```json")
                end_index = cleaned_response.find("```", start_index)
                json_str = cleaned_response[start_index:end_index].strip() if end_index != -1 else cleaned_response[start_index:].strip()
            elif "```" in cleaned_response:
                start_index = cleaned_response.find("```") + len("```")
                end_index = cleaned_response.find("```", start_index)
                json_str = cleaned_response[start_index:end_index].strip() if end_index != -1 else cleaned_response[start_index:].strip()
            else:
                json_str = cleaned_response

            json_str = json_str.replace('```', '').strip()
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            st.warning(f"JSON parsing error in {agent_type}: {e}")
            try:
                array_match = re.search(r'\[\s*\{.*\}\s*\]', json_str, re.DOTALL)
                if array_match:
                    return json.loads(array_match.group())

                json_str = re.sub(r'^[^\[\{]*', '', json_str)
                json_str = re.sub(r'[^\]\}]*$', '', json_str)
                return json.loads(json_str)
            except Exception:
                st.info(f"Attempting manual JSON reconstruction for {agent_type}...")
                return self._manual_json_recovery(json_str, agent_type)

        except Exception as e:
            st.error(f"Unexpected error in {agent_type}: {e}")
            return None

    def _manual_json_recovery(self, json_str: str, agent_type: str) -> Any:
        """Manual JSON recovery when automatic parsing fails."""
        try:
            if agent_type == "itinerary":
                day_pattern = r'"day"\s*:\s*(\d+)'
                theme_pattern = r'"theme"\s*:\s*"([^"]*)"'
                morning_pattern = r'"morning"\s*:\s*\[(.*?)\]'
                afternoon_pattern = r'"afternoon"\s*:\s*\[(.*?)\]'
                evening_pattern = r'"evening"\s*:\s*\[(.*?)\]'

                days = re.findall(day_pattern, json_str)
                themes = re.findall(theme_pattern, json_str)
                morning_activities = re.findall(morning_pattern, json_str, re.DOTALL)
                afternoon_activities = re.findall(afternoon_pattern, json_str, re.DOTALL)
                evening_activities = re.findall(evening_pattern, json_str, re.DOTALL)

                if days:
                    itinerary = []
                    for i, day_num in enumerate(days):
                        if i < len(themes) and i < len(morning_activities) and i < len(afternoon_activities) and i < len(evening_activities):
                            day_data = {
                                "day": int(day_num),
                                "theme": themes[i],
                                "morning": self._parse_activity_list(morning_activities[i]),
                                "afternoon": self._parse_activity_list(afternoon_activities[i]),
                                "evening": self._parse_activity_list(evening_activities[i]),
                                "notes": "",
                            }
                            itinerary.append(day_data)

                    if itinerary:
                        st.success(f"✅ Successfully recovered itinerary with {len(itinerary)} days")
                        return itinerary

            return None

        except Exception as e:
            st.error(f"Manual JSON recovery failed: {e}")
            return None

    def _parse_activity_list(self, activity_string: str) -> List[str]:
        """Parse an activity list from its string representation."""
        try:
            activities = re.findall(r'"([^"]*)"', activity_string)
            if activities:
                return activities
            activities = [act.strip().strip('"') for act in activity_string.split(',')]
            return [act for act in activities if act]
        except Exception:
            return ["Activity details unavailable"]


class DestinationResearchAgent(BaseAgent):
    """Researches destinations and provides comprehensive insights."""

    def research_destination(self, destination: str, interests: List[str]) -> Dict[str, Any]:
        with st.spinner(f"🔍 Researching {destination}..."):
            prompt = f"""
            Provide comprehensive travel research for {destination} focusing on {', '.join(interests)}.

            Return a valid JSON object with these exact fields:
            - "overview" (string): Detailed overview of the destination
            - "best_time_to_visit" (string): Best seasons/months to visit
            - "top_attractions" (array): List of top attractions
            - "local_culture" (string): Information about local culture and customs
            - "safety_notes" (string): Safety information and tips
            - "budget_tips" (array): Money-saving tips
            - "local_cuisine" (string): Information about local food
            - "transportation" (string): Transportation options and tips
            - "hidden_gems" (array): Lesser-known attractions
            - "essential_phrases" (array): Useful local phrases

            Make the response detailed and practical for travelers.
            Return ONLY the JSON object, no additional text.
            """
            response = self.call_gemini(prompt)
            parsed_data = self.safe_json_parse(response, "research")

            if parsed_data is None:
                st.warning("Using default research data due to API issues.")
                return self._get_default_research_data(destination)

            return parsed_data

    def _get_default_research_data(self, destination: str) -> Dict[str, Any]:
        """Fallback data used when the API call fails."""
        return {
            "overview": f"{destination} is a fascinating travel destination with rich culture and diverse attractions. Perfect for explorers seeking authentic experiences and memorable adventures.",
            "best_time_to_visit": "Spring (March-May) and Fall (September-November) typically offer the best weather with comfortable temperatures and fewer crowds.",
            "top_attractions": [
                "Historic city center and old town districts",
                "Local markets and traditional shopping areas",
                "Museums and cultural heritage centers",
                "Parks, gardens, and natural attractions",
                "Architectural landmarks and monuments",
                "Local cuisine and food experiences",
            ],
            "local_culture": "Rich cultural heritage with friendly locals. Respect local customs and traditions. Dress modestly when visiting religious sites.",
            "safety_notes": "Generally safe for tourists. Take normal precautions with valuables and be aware of your surroundings. Keep copies of important documents.",
            "budget_tips": [
                "Travel during shoulder season for better prices",
                "Use public transportation instead of taxis",
                "Eat at local restaurants away from tourist areas",
                "Look for free walking tours and museum days",
                "Book accommodation in advance for better deals",
            ],
            "local_cuisine": "Diverse culinary scene with local specialties worth trying. Don't miss street food markets and traditional restaurants.",
            "transportation": "Efficient public transport system available including buses, trains, and metro. Consider getting a travel card for unlimited rides.",
            "hidden_gems": [
                "Local neighborhood markets away from tourist centers",
                "Scenic viewpoints known only to locals",
                "Traditional craft workshops and studios",
                "Local festivals and cultural events",
            ],
            "essential_phrases": [
                "Hello / Thank you",
                "How much does this cost?",
                "Where is...?",
                "Can you help me please?",
                "I would like to order...",
            ],
        }


class BudgetPlanningAgent(BaseAgent):
    """Creates detailed budget plans with smart allocation."""

    def create_budget_plan(self, travel_plan: TravelPlan) -> Dict[str, Any]:
        with st.spinner("💰 Creating budget plan..."):
            prompt = f"""
            Create detailed budget plan for {travel_plan.destination} for {travel_plan.duration_days} days
            with ${travel_plan.budget} total budget and {travel_plan.travel_style} travel style.

            Return a valid JSON object with these exact fields:
            - "total_budget" (number): Total budget amount
            - "accommodation" (object): {{"daily": number, "total": number}}
            - "food_dining" (object): {{"daily": number, "total": number}}
            - "transportation" (object): {{"total": number}}
            - "activities_entertainment" (object): {{"total": number}}
            - "miscellaneous" (object): {{"total": number}}
            - "daily_average" (number): Daily average spending
            - "money_saving_strategies" (array): List of money-saving tips

            Ensure the total of all categories equals the total_budget.
            Make the budget realistic for the destination and travel style.
            Return ONLY the JSON object, no additional text.
            """
            # This payload is small and structured, so it doesn't need the
            # full 2000-token default — trimming it reduces pressure on
            # Groq's free-tier tokens-per-minute limit.
            response = self.call_groq(prompt, max_tokens=900)
            parsed_data = self.safe_json_parse(response, "budget")

            if parsed_data is None:
                st.warning("Using smart budget calculation due to API issues")
                return self._create_smart_budget(travel_plan)

            if abs(parsed_data.get('total_budget', 0) - travel_plan.budget) > 100:
                parsed_data['total_budget'] = travel_plan.budget

            return parsed_data

    def _create_smart_budget(self, travel_plan: TravelPlan) -> Dict[str, Any]:
        total = travel_plan.budget
        days = travel_plan.duration_days

        style_multipliers = {
            "budget": {"accommodation": 0.3, "food": 0.25, "transport": 0.2, "activities": 0.15, "misc": 0.1},
            "mid-range": {"accommodation": 0.4, "food": 0.25, "transport": 0.15, "activities": 0.12, "misc": 0.08},
            "luxury": {"accommodation": 0.5, "food": 0.2, "transport": 0.15, "activities": 0.1, "misc": 0.05},
            "backpacker": {"accommodation": 0.25, "food": 0.3, "transport": 0.25, "activities": 0.15, "misc": 0.05},
            "family": {"accommodation": 0.45, "food": 0.25, "transport": 0.15, "activities": 0.1, "misc": 0.05},
        }

        multipliers = style_multipliers.get(travel_plan.travel_style, style_multipliers["mid-range"])

        return {
            "total_budget": total,
            "accommodation": {
                "daily": round((total * multipliers["accommodation"]) / days, 2),
                "total": round(total * multipliers["accommodation"], 2),
            },
            "food_dining": {
                "daily": round((total * multipliers["food"]) / days, 2),
                "total": round(total * multipliers["food"], 2),
            },
            "transportation": {
                "total": round(total * multipliers["transport"], 2),
            },
            "activities_entertainment": {
                "total": round(total * multipliers["activities"], 2),
            },
            "miscellaneous": {
                "total": round(total * multipliers["misc"], 2),
            },
            "daily_average": round(total / days, 2),
            "money_saving_strategies": [
                "Book flights and accommodation 2-3 months in advance",
                "Use public transportation instead of taxis",
                "Eat at local restaurants away from tourist areas",
                "Travel during shoulder season for better prices",
                "Look for free walking tours and museum days",
                "Consider vacation rentals instead of hotels",
            ],
        }


class ItineraryPlanningAgent(BaseAgent):
    """Creates detailed daily itineraries."""

    def create_itinerary(self, travel_plan: TravelPlan, research_data: Dict) -> List[Dict[str, Any]]:
        with st.spinner("📅 Planning detailed itinerary..."):
            prompt = f"""
            Create a detailed {travel_plan.duration_days}-day itinerary for {travel_plan.destination}
            focusing on {travel_plan.travel_style} travel style and interests: {', '.join(travel_plan.interests)}.

            Return a valid JSON array where each object has these exact fields:
            - "day" (number): Day number
            - "theme" (string): Daily theme or focus
            - "morning" (array): Morning activities as simple strings
            - "afternoon" (array): Afternoon activities as simple strings
            - "evening" (array): Evening activities as simple strings
            - "notes" (string): Optional tips or recommendations

            IMPORTANT: Each activity should be a simple string description, NOT an object with time and notes.
            Example of CORRECT format:
            "morning": ["Arrive at airport", "Check into hotel", "Explore local area"]

            Example of INCORRECT format:
            "morning": [{{"activity": "Arrive", "time": "9:00 AM"}}]

            Make it realistic with proper timing, logical flow between days, and include:
            - Cultural experiences
            - Local cuisine
            - Key attractions
            - Relaxation time
            - Transportation considerations

            Return ONLY the JSON array, no additional text.
            """
            response = self.call_groq(prompt)
            parsed_data = self.safe_json_parse(response, "itinerary")

            if parsed_data is None:
                st.warning("Using sample itinerary due to API issues")
                return self._create_sample_itinerary(travel_plan)

            if isinstance(parsed_data, list):
                if len(parsed_data) != travel_plan.duration_days:
                    st.warning(f"Adjusting itinerary from {len(parsed_data)} to {travel_plan.duration_days} days")
                    return self._create_sample_itinerary(travel_plan)

                for day in parsed_data:
                    if not all(key in day for key in ['day', 'theme', 'morning', 'afternoon', 'evening']):
                        st.error("Itinerary data missing required fields")
                        return self._create_sample_itinerary(travel_plan)

                return parsed_data
            else:
                st.error("Itinerary data is not in expected list format")
                return self._create_sample_itinerary(travel_plan)

    def _create_sample_itinerary(self, travel_plan: TravelPlan) -> List[Dict[str, Any]]:
        itinerary = []

        for day in range(1, travel_plan.duration_days + 1):
            if day == 1:
                itinerary.append({
                    "day": day,
                    "theme": f"Arrival and First Impressions of {travel_plan.destination}",
                    "morning": [
                        "Arrive at airport/train station",
                        "Transfer to accommodation",
                        "Check-in and freshen up",
                    ],
                    "afternoon": [
                        "Orientation walk around neighborhood",
                        "Visit local market for lunch",
                        "Explore nearby attractions and get bearings",
                    ],
                    "evening": [
                        "Welcome dinner at traditional restaurant",
                        "Evening stroll to get familiar with area",
                        "Relax and adjust to time zone",
                    ],
                    "notes": "Take it easy on arrival day. Focus on acclimating and getting oriented. Try local street food for an authentic experience.",
                })
            elif day == travel_plan.duration_days:
                itinerary.append({
                    "day": day,
                    "theme": "Final Explorations and Departure Preparations",
                    "morning": [
                        "Last-minute souvenir shopping at local markets",
                        "Visit favorite spots for final photos",
                        "Enjoy local breakfast specialty one last time",
                    ],
                    "afternoon": [
                        "Check out from accommodation",
                        "Last local lunch experience at recommended spot",
                        "Travel to airport/station with buffer time",
                    ],
                    "evening": [
                        "Departure from destination",
                        "Flight/train journey home",
                        "Reflect on amazing travel experiences",
                    ],
                    "notes": "Leave extra time for traffic and airport security. Keep essential items and documents in carry-on. Double-check flight times.",
                })
            else:
                theme_options = [
                    f"Cultural Heritage Day in {travel_plan.destination}",
                    "Nature and Outdoor Adventures",
                    "Local Life and Neighborhood Exploration",
                    "Food and Culinary Experiences",
                    "Arts and Historical Discovery",
                ]
                theme = theme_options[(day - 2) % len(theme_options)]
                current_interest = travel_plan.interests[(day - 2) % len(travel_plan.interests)] if travel_plan.interests else "local culture"

                itinerary.append({
                    "day": day,
                    "theme": theme,
                    "morning": [
                        "Breakfast at highly-rated local cafe",
                        f"Visit main {current_interest} sites or museums",
                        "Guided tour or cultural workshop",
                    ],
                    "afternoon": [
                        "Local cuisine experience for lunch",
                        "Explore different neighborhoods or natural sites",
                        "Shopping at authentic local markets",
                    ],
                    "evening": [
                        "Dinner at recommended restaurant featuring regional specialties",
                        "Evening entertainment, cultural show, or night market",
                        "Relaxation and planning for next day's adventures",
                    ],
                    "notes": f"Day {day} focuses on {current_interest}. Wear comfortable walking shoes and carry water. Don't forget your camera for amazing photo opportunities!",
                })
        return itinerary


class LocalExperienceAgent(BaseAgent):
    """Finds unique local experiences."""

    def get_local_attractions(self, destination: str, interests: List[str]) -> List[Dict[str, Any]]:
        with st.spinner("🌟 Discovering unique local experiences..."):
            prompt = f"""
            Find unique local experiences and hidden gems in {destination} for interests: {', '.join(interests)}.

            Return a valid JSON array of 5-7 experiences where each object has:
            - "name" (string): Experience name
            - "description" (string): Detailed description
            - "type" (string): Experience type (Cultural, Food, Nature, Adventure, Shopping, etc.)
            - "cost" (string): Budget, Moderate, or Expensive
            - "duration" (string): Time required (e.g., "2-3 hours", "Half day")
            - "why_special" (string): What makes it unique
            - "best_time_to_visit" (string): Best time of day or season
            - "tips" (array): Practical tips for visitors

            Focus on experiences that are:
            - Off the beaten path
            - Locally loved and authentic
            - Memorable and special
            - Align with the specified interests

            Return ONLY the JSON array, no additional text.
            """
            response = self.call_groq(prompt)
            parsed_data = self.safe_json_parse(response, "local experiences")

            if parsed_data is None:
                st.warning("Using default local experiences due to API issues")
                return self._get_default_experiences()

            if isinstance(parsed_data, list):
                return parsed_data
            else:
                st.error("Local experiences data is not in expected list format")
                return self._get_default_experiences()

    def _get_default_experiences(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Local Market Tour",
                "description": "Explore vibrant local markets with fresh produce, authentic street food, and traditional crafts. Experience the daily life of locals and taste seasonal specialties while learning about regional ingredients and cooking techniques.",
                "type": "Cultural/Food",
                "cost": "Budget",
                "duration": "2-3 hours",
                "why_special": "Authentic local experience away from tourist crowds, chance to interact with vendors and learn about local ingredients and culinary traditions from passionate food experts.",
                "best_time_to_visit": "Morning when markets are most active",
                "tips": [
                    "Go early for the freshest selections and fewer crowds",
                    "Bring small change for easier transactions with vendors",
                    "Don't be afraid to try free samples and ask questions",
                    "Ask vendors for preparation tips and recipe suggestions",
                ],
            },
            {
                "name": "Traditional Craft Workshop",
                "description": "Participate in hands-on workshops learning traditional local crafts from master artisans. Create your own souvenirs while preserving cultural heritage and learning ancient techniques passed down through generations.",
                "type": "Cultural/Educational",
                "cost": "Moderate",
                "duration": "3-4 hours",
                "why_special": "Unique opportunity to learn ancient techniques directly from local masters and create meaningful memories while supporting traditional arts and local artisans.",
                "best_time_to_visit": "Afternoon sessions",
                "tips": [
                    "Book in advance as classes often fill quickly",
                    "Wear comfortable clothing that can get dirty",
                    "Ask about the history and cultural significance behind each craft",
                    "Consider shipping fragile finished items home",
                ],
            },
            {
                "name": "Hidden Viewpoint Sunset Experience",
                "description": "Discover a secluded viewpoint known only to locals, offering breathtaking panoramic views of the cityscape during golden hour and sunset. Escape the crowded tourist spots for a peaceful, authentic viewing experience.",
                "type": "Nature/Photography",
                "cost": "Budget",
                "duration": "1-2 hours",
                "why_special": "Escape the crowded tourist viewpoints and enjoy a peaceful, authentic sunset experience with stunning photo opportunities and local insights about the best viewing spots.",
                "best_time_to_visit": "Evening, 45 minutes before sunset",
                "tips": [
                    "Arrive 45 minutes before sunset for best light and seating",
                    "Bring a tripod for stable photography in low light",
                    "Pack a light picnic to enjoy the view comfortably",
                    "Check weather conditions in advance for clear skies",
                ],
            },
            {
                "name": "Neighborhood Food Crawl",
                "description": "Explore residential neighborhoods and sample authentic local cuisine at family-run eateries, street food stalls, and hidden culinary gems. Discover where locals really eat beyond the tourist restaurant reviews.",
                "type": "Food/Cultural",
                "cost": "Moderate",
                "duration": "3-4 hours",
                "why_special": "Go beyond restaurant reviews and discover where locals really eat, with personalized recommendations from food-loving residents and insights into regional culinary traditions.",
                "best_time_to_visit": "Lunch or dinner time when locals dine",
                "tips": [
                    "Come hungry and pace yourself between stops",
                    "Try dishes you can't find in tourist areas",
                    "Ask about seasonal specials and chef recommendations",
                    "Learn a few food-related phrases in local language",
                ],
            },
            {
                "name": "Early Morning Temple/Garden Visit",
                "description": "Experience the serenity of ancient temples or traditional gardens during the peaceful early morning hours before tourist crowds arrive. Enjoy magical atmosphere with soft morning light and opportunity for quiet contemplation.",
                "type": "Cultural/Spiritual",
                "cost": "Budget",
                "duration": "2-3 hours",
                "why_special": "Magical atmosphere with soft morning light, peaceful ambiance, and opportunity for quiet contemplation and photography without the crowds, plus chance to observe morning rituals.",
                "best_time_to_visit": "Early morning right at opening",
                "tips": [
                    "Check specific opening hours in advance",
                    "Dress respectfully for religious sites (covered shoulders, knees)",
                    "Bring cash for entrance fees and donations",
                    "Observe silence to enjoy the peaceful morning atmosphere",
                ],
            },
        ]


class TravelCoordinator:
    """Orchestrates all travel agents."""

    def __init__(self):
        self.research_agent = DestinationResearchAgent("ResearchAgent")
        self.budget_agent = BudgetPlanningAgent("BudgetAgent")
        self.itinerary_agent = ItineraryPlanningAgent("ItineraryAgent")
        self.local_agent = LocalExperienceAgent("LocalAgent")

    def create_complete_travel_plan(self, travel_plan: TravelPlan) -> Dict[str, Any]:
        plan = {}

        progress_bar = st.progress(0)
        status_text = st.empty()

        tasks = [
            ("🔍 Researching destination...", 0.2),
            ("💰 Creating budget...", 0.4),
            ("📅 Planning itinerary...", 0.7),
            ("🌟 Finding local experiences...", 0.9),
            ("🎉 Finalizing...", 1.0),
        ]

        try:
            for task_name, progress in tasks:
                status_text.text(task_name)
                progress_bar.progress(progress)

                if "Researching" in task_name:
                    plan['research'] = self.research_agent.research_destination(
                        travel_plan.destination, travel_plan.interests or [])
                elif "Creating budget" in task_name:
                    plan['budget'] = self.budget_agent.create_budget_plan(travel_plan)
                elif "Planning itinerary" in task_name:
                    research_data = plan.get('research', {})
                    if not research_data:
                        research_data = self.research_agent._get_default_research_data(travel_plan.destination)
                    plan['itinerary'] = self.itinerary_agent.create_itinerary(travel_plan, research_data)
                elif "Finding local experiences" in task_name:
                    plan['local_experiences'] = self.local_agent.get_local_attractions(
                        travel_plan.destination, travel_plan.interests or [])

                # Budget, itinerary, and local-experiences all call Groq in
                # sequence. A slightly longer pause here (vs. the original
                # 0.5s) gives the free-tier tokens-per-minute window a
                # little more room to recover between calls, on top of the
                # retry/backoff already built into call_groq().
                time.sleep(1.5)

            plan['travel_plan'] = travel_plan
            plan['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            status_text.text("✅ Travel plan completed!")

        except Exception as e:
            st.error(f"Error during plan generation: {str(e)}")
            status_text.text("❌ Error generating travel plan")

        finally:
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()

        return plan


# =============================================================================
# UI COMPONENTS
# =============================================================================
def render_hero_section():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('''
            <h1 class="luxury-gradient-title">
                TRAVEL TRIPY<span class="title-emoji">✈️</span>
            </h1>
            <div class="title-underline"></div>
        ''', unsafe_allow_html=True)
        st.markdown('<div class="travel-motivation">Discover the World, Create Memories That Last Forever</div>', unsafe_allow_html=True)
        st.markdown('<div class="travel-subtitle">Every journey begins with a single step. Let us help you take that step in style.</div>', unsafe_allow_html=True)


def render_input_section():
    st.markdown('<h2 style="text-align: center; color: #ecf0f1; margin-bottom: 2rem; text-shadow: 2px 2px 8px rgba(0,0,0,0.3);">✈️ Design Your Dream Journey</h2>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🏙️ Destination")
        destination = st.text_input("Destination", value="Kyoto, Japan", placeholder="Enter city, country...", label_visibility="collapsed")

        st.markdown("### 💰 Budget")
        budget = st.number_input("Budget", min_value=100, max_value=50000, value=7500, step=100, label_visibility="collapsed")

        st.markdown("### 📅 Duration")
        duration = st.slider("Duration", min_value=2, max_value=30, value=10, label_visibility="collapsed")

    with col2:
        st.markdown("### 🎯 Travel Style")
        travel_style = st.selectbox(
            "Travel Style",
            ["budget", "mid-range", "luxury", "backpacker", "family"],
            index=2,
            label_visibility="collapsed",
        )

        st.markdown("### ❤️ Interests")
        interests = st.text_input("Interests", value="history, food, temples, gardens, art", placeholder="Your interests...", label_visibility="collapsed")

        st.markdown("### 🗓️ Start Date")
        start_date = st.date_input("Start Date", datetime.date.today(), label_visibility="collapsed")

    with col3:
        st.markdown("### 💎 Premium Features")
        st.write("• **AI-Powered Research**")
        st.write("• **Smart Budget Planning**")
        st.write("• **Daily Itineraries**")
        st.write("• **Local Experiences**")
        st.write("• **Real-time Updates**")

    return destination, budget, duration, travel_style, interests, start_date


def _display_named_items(items, css_class, label="item"):
    """Helper used by the research tab to render either a dict, list-of-str,
    or list-of-dict of named/described items with a consistent card style."""
    if not items:
        st.markdown(f'<div class="research-section">No {label}s available</div>', unsafe_allow_html=True)
        return

    if isinstance(items, dict):
        processed = {}
        current_name = None
        for key, value in items.items():
            if 'name' in key.lower() or label in key.lower():
                current_name = value
            elif 'description' in key.lower() and current_name:
                processed[current_name] = value
                current_name = None
            elif current_name and str(value).strip():
                processed[current_name] = value
                current_name = None
        for i, (name, description) in enumerate(processed.items(), 1):
            st.markdown(f'''
            <div class="{css_class}">
                <strong style="color: white; font-size: 1.2rem; display: block; margin-bottom: 0.8rem;">{i}. {name}</strong>
                <p style="color: white; margin: 0; opacity: 0.95; line-height: 1.5;">{description}</p>
            </div>
            ''', unsafe_allow_html=True)

    elif isinstance(items, list):
        for i, item in enumerate(items, 1):
            if isinstance(item, str):
                st.markdown(f'''
                <div class="{css_class}">
                    <strong style="color: white; font-size: 1.2rem;">{i}. {item}</strong>
                </div>
                ''', unsafe_allow_html=True)
            elif isinstance(item, dict):
                name = None
                description = None
                for key, value in item.items():
                    if 'name' in key.lower():
                        name = value
                    elif 'description' in key.lower():
                        description = value
                if name:
                    html = f'''
                    <div class="{css_class}">
                        <strong style="color: white; font-size: 1.2rem; display: block; margin-bottom: 0.8rem;">{i}. {name}</strong>
                    '''
                    if description:
                        html += f'<p style="color: white; margin: 0; opacity: 0.95; line-height: 1.5;">{description}</p>'
                    html += '</div>'
                    st.markdown(html, unsafe_allow_html=True)


def render_research_tab():
    if not st.session_state.get('research_data'):
        st.markdown("""
        <div style='text-align: center; padding: 3rem; background: rgba(255,255,255,0.9); border-radius: 20px; margin: 2rem 0;'>
            <h3 style='color: #333;'>🔍 Destination Research</h3>
            <p style='color: #666;'>Generate a travel plan to see comprehensive destination insights here!</p>
        </div>
        """, unsafe_allow_html=True)
        return

    research = st.session_state.research_data
    travel_plan = st.session_state.travel_plan

    st.markdown('<div class="research-container fade-in">', unsafe_allow_html=True)
    st.markdown('<h2 style="color: #2c3e50; text-align: center; margin-bottom: 2rem;">📍 Destination Research Report</h2>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🌟 Overview")
        st.markdown(f'<div class="research-section">{research.get("overview", "No overview available")}</div>', unsafe_allow_html=True)

        st.markdown("### 🏛️ Top Attractions")
        _display_named_items(research.get('top_attractions', []), "attraction-card", "attraction")

        st.markdown("### 🎭 Local Culture")
        st.markdown(f'<div class="research-section">{research.get("local_culture", "No cultural information available")}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### 🌤️ Best Time to Visit")
        st.markdown(f'<div class="research-section">{research.get("best_time_to_visit", "No timing information available")}</div>', unsafe_allow_html=True)

        st.markdown("### 🍽️ Local Cuisine")
        st.markdown(f'<div class="research-section">{research.get("local_cuisine", "No cuisine information available")}</div>', unsafe_allow_html=True)

        st.markdown("### 🚗 Transportation")
        st.markdown(f'<div class="research-section">{research.get("transportation", "No transportation information available")}</div>', unsafe_allow_html=True)

    st.markdown("### 💡 Budget Tips")
    tips = research.get('budget_tips', [])
    if isinstance(tips, dict):
        for value in tips.values():
            st.markdown(f'<div class="research-list-item">💡 {value}</div>', unsafe_allow_html=True)
    elif isinstance(tips, list):
        for tip in tips:
            st.markdown(f'<div class="research-list-item">💡 {tip}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="research-list-item">No budget tips available</div>', unsafe_allow_html=True)

    st.markdown("### 💎 Hidden Gems")
    _display_named_items(research.get('hidden_gems', []), "hidden-gem-card", "gem")

    st.markdown("### 🗣️ Essential Phrases")
    phrases = research.get('essential_phrases', [])
    if isinstance(phrases, dict):
        for value in phrases.values():
            st.markdown(f'<div class="research-list-item">🗣️ {value}</div>', unsafe_allow_html=True)
    elif isinstance(phrases, list):
        for phrase in phrases:
            st.markdown(f'<div class="research-list-item">🗣️ {phrase}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="research-list-item">No essential phrases available</div>', unsafe_allow_html=True)

    # ===== Destination images =====
    st.markdown("---")
    st.markdown("### 🖼️ Destination Visuals")
    destination = travel_plan.destination if travel_plan else "travel"

    # NOTE: these are random stock placeholder images (picsum.photos), not
    # images of the actual destination. Flagged clearly here rather than
    # implying they depict the real place.
    image_urls = [
        "https://picsum.photos/800/600?random=1&gravity=center",
        "https://picsum.photos/800/600?random=2&gravity=center",
    ]
    captions = [
        f"Illustrative scenery (not an actual photo of {destination})",
        f"Illustrative travel imagery (not an actual photo of {destination})",
    ]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'''
        <div style="text-align: center;">
            <img src="{image_urls[0]}" class="destination-image" alt="{captions[0]}">
            <div class="image-caption">{captions[0]}</div>
        </div>
        ''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''
        <div style="text-align: center;">
            <img src="{image_urls[1]}" class="destination-image" alt="{captions[1]}">
            <div class="image-caption">{captions[1]}</div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; margin-top: 1rem;">
        <p style="color: #666; font-size: 0.9rem; font-style: italic;">
            🎨 Placeholder visuals to inspire your travel journey
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_budget_tab():
    if not st.session_state.get('budget_data'):
        st.markdown("""
        <div style='text-align: center; padding: 3rem; background: rgba(255,255,255,0.9); border-radius: 20px; margin: 2rem 0;'>
            <h3 style='color: #333;'>💰 Budget Planning</h3>
            <p style='color: #666;'>Generate a travel plan to see detailed budget breakdown here!</p>
        </div>
        """, unsafe_allow_html=True)
        return

    budget = st.session_state.budget_data

    st.markdown("### 📊 Budget Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = budget.get('total_budget', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>Total Budget</h4>
            <h2>${total:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        daily_avg = budget.get('daily_average', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>Daily Average</h4>
            <h2>${daily_avg:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        accommodation = budget.get('accommodation', {}).get('total', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>Accommodation</h4>
            <h2>${accommodation:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        activities = budget.get('activities_entertainment', {}).get('total', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h4>Activities</h4>
            <h2>${activities:,.0f}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.markdown("### 💰 Budget Distribution")

    categories = ['Accommodation', 'Food & Dining', 'Transportation', 'Activities', 'Miscellaneous']
    values = [
        budget.get('accommodation', {}).get('total', 0),
        budget.get('food_dining', {}).get('total', 0),
        budget.get('transportation', {}).get('total', 0),
        budget.get('activities_entertainment', {}).get('total', 0),
        budget.get('miscellaneous', {}).get('total', 0),
    ]

    fig = px.pie(
        names=categories,
        values=values,
        hole=0.5,
        color_discrete_sequence=['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'],
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 💡 Money Saving Strategies")
    tips = budget.get('money_saving_strategies', [])
    for tip in tips:
        st.markdown(f'<div style="background: rgba(255,255,255,0.8); padding: 1rem; margin: 0.5rem 0; border-radius: 10px; border-left: 3px solid #667eea;">• {tip}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_itinerary_tab():
    if not st.session_state.get('itinerary_data'):
        st.markdown("""
        <div style='text-align: center; padding: 3rem; background: rgba(255,255,255,0.9); border-radius: 20px; margin: 2rem 0;'>
            <h3 style='color: #333;'>📅 Travel Itinerary</h3>
            <p style='color: #666;'>Generate a travel plan to see your detailed daily itinerary here!</p>
        </div>
        """, unsafe_allow_html=True)
        return

    itinerary = st.session_state.itinerary_data

    render_map_visualization()
    st.markdown("---")

    st.markdown('<div class="itinerary-container">', unsafe_allow_html=True)
    st.markdown('<h2 style="color: #2c3e50; text-align: center; margin-bottom: 2rem;">📅 Your Travel Itinerary</h2>', unsafe_allow_html=True)

    for day in itinerary:
        st.markdown(f"""
        <div class="itinerary-day-card fade-in">
            <h3 style="color: white; margin: 0;">🗓️ Day {day['day']}: {day.get('theme', 'Exploring')}</h3>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### 🌅 Morning")
            for activity in day.get('morning', []):
                st.markdown(f'<div class="activity-item">• {activity}</div>', unsafe_allow_html=True)

        with col2:
            st.markdown("#### ☀️ Afternoon")
            for activity in day.get('afternoon', []):
                st.markdown(f'<div class="activity-item">• {activity}</div>', unsafe_allow_html=True)

        with col3:
            st.markdown("#### 🌙 Evening")
            for activity in day.get('evening', []):
                st.markdown(f'<div class="activity-item">• {activity}</div>', unsafe_allow_html=True)

        if day.get('notes'):
            st.markdown(f'<div class="notes-section"><strong>💡 Notes:</strong> {day["notes"]}</div>', unsafe_allow_html=True)

        st.markdown("---")

    st.markdown('</div>', unsafe_allow_html=True)


def render_map_visualization():
    """Render an OpenStreetMap visualization of the itinerary.

    NOTE (see review): the day-by-day stop locations plotted here are
    randomly scattered around the destination's center point with generic
    placeholder names (e.g. "Museum", "Historic District") — they are NOT
    real, geocoded points of interest tied to the actual itinerary text. A
    banner below makes this explicit. To show genuinely accurate stops,
    each activity string from the itinerary would need to be geocoded
    individually (e.g. via the OpenTripMap API using OPENTRIPMAP_API_KEY,
    which is currently unused) rather than randomly placed.
    """
    if not st.session_state.get('itinerary_data'):
        return

    itinerary = st.session_state.itinerary_data
    destination = st.session_state.travel_plan.destination if st.session_state.get('travel_plan') else "Kyoto, Japan"

    st.markdown("### 🗺️ Interactive Itinerary Map")

    if not MAPS_AVAILABLE:
        st.error("🗺️ Map features unavailable. Please install: `pip install folium streamlit-folium geopy`")
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea, #764ba2); color: white;
                    padding: 2rem; border-radius: 15px; text-align: center; margin: 1rem 0;'>
            <h3>🚀 Enhanced Map Visualization</h3>
            <p>Install the required packages for interactive itinerary mapping:</p>
            <code style='background: rgba(255,255,255,0.2); padding: 10px; border-radius: 5px;
                         display: block; margin: 10px auto; width: fit-content;'>
                pip install folium streamlit-folium geopy
            </code>
        </div>
        """, unsafe_allow_html=True)
        render_itinerary_table_fallback(itinerary)
        return

    st.info(
        "ℹ️ Map pins show approximate, illustrative stops scattered around "
        f"{destination} — they are not geocoded to the specific activities "
        "listed in your itinerary text."
    )

    import random

    try:
        geolocator = Nominatim(user_agent="travel_assistant_app", timeout=10)

        with st.spinner("📍 Geocoding destination and planning routes..."):
            try:
                location = geolocator.geocode(destination)
                if location:
                    center_lat, center_lon = location.latitude, location.longitude
                    st.success(f"Found location: {location.address}")
                else:
                    fallback_locations = {
                        "kyoto": (35.0116, 135.7681),
                        "tokyo": (35.6762, 139.6503),
                        "paris": (48.8566, 2.3522),
                        "london": (51.5074, -0.1278),
                        "new york": (40.7128, -74.0060),
                        "bangkok": (13.7563, 100.5018),
                        "bali": (-8.4095, 115.1889),
                        "rome": (41.9028, 12.4964),
                        "dubai": (25.2048, 55.2708),
                        "singapore": (1.3521, 103.8198),
                    }
                    destination_lower = destination.lower()
                    center_lat, center_lon = 35.0116, 135.7681  # default: Kyoto
                    for key, coords in fallback_locations.items():
                        if key in destination_lower:
                            center_lat, center_lon = coords
                            break
            except Exception as e:
                st.warning(f"Using default coordinates: {str(e)}")
                center_lat, center_lon = 35.0116, 135.7681

        m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles='OpenStreetMap')

        folium.TileLayer(
            tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            name='Light Theme',
            control=True,
        ).add_to(m)

        folium.TileLayer(
            tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            name='Dark Theme',
            control=True,
        ).add_to(m)

        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                  '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
                  '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2']

        all_day_locations = []
        day_routes = []

        for day_idx, day in enumerate(itinerary):
            day_number = day['day']
            theme = day.get('theme', '').lower()
            color = colors[day_idx % len(colors)]

            day_locations = []
            num_locations = random.randint(3, 4)

            for _ in range(num_locations):
                spread_factor = min(0.03 + (day_idx * 0.005), 0.08)
                lat_variation = random.uniform(-spread_factor, spread_factor)
                lon_variation = random.uniform(-spread_factor, spread_factor)

                location_lat = center_lat + lat_variation
                location_lon = center_lon + lon_variation

                location_types = {
                    'cultural': ['Museum', 'Art Gallery', 'Cultural Center', 'Historic Site', 'Theater'],
                    'food': ['Restaurant', 'Food Market', 'Cafe', 'Street Food', 'Bakery'],
                    'nature': ['Park', 'Garden', 'Viewpoint', 'Nature Trail', 'Lake'],
                    'shopping': ['Shopping District', 'Local Market', 'Boutique', 'Mall', 'Artisan Shop'],
                    'historical': ['Historic District', 'Ancient Temple', 'Castle', 'Monument', 'Ruins'],
                    'religious': ['Temple', 'Shrine', 'Church', 'Mosque', 'Monastery'],
                }

                loc_type = 'sightseeing'
                for key in location_types:
                    if key in theme:
                        loc_type = key
                        break

                location_name = random.choice(location_types.get(loc_type, ['Landmark', 'Attraction', 'Point of Interest']))

                day_locations.append({
                    'name': location_name,
                    'lat': location_lat,
                    'lon': location_lon,
                    'type': loc_type,
                    'day': day_number,
                    'theme': theme,
                    'color': color,
                })

            all_day_locations.extend(day_locations)
            day_routes.append(day_locations)

        def create_day_marker(day_number, color):
            return f"""
            <div style="
                background: {color};
                color: white;
                border: 3px solid white;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 14px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif;
            ">
                {day_number}
            </div>
            """

        for day_idx, day_locations in enumerate(day_routes):
            color = colors[day_idx % len(colors)]
            day_number = itinerary[day_idx]['day']

            for loc_idx, location in enumerate(day_locations):
                day_icon = folium.DivIcon(
                    html=create_day_marker(day_number, color),
                    icon_size=(40, 40),
                    icon_anchor=(20, 20),
                    popup_anchor=(0, -20),
                )

                popup_content = f"""
                <div style="width: 280px; font-family: Arial, sans-serif;">
                    <div style="background: {color}; color: white; padding: 12px; border-radius: 8px 8px 0 0; margin: -12px -12px 12px -12px;">
                        <h4 style="margin: 0; font-size: 16px;">📍 {location['name']}</h4>
                    </div>
                    <div style="padding: 8px 0;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span style="font-weight: bold;">📅 Day {day_number}</span>
                            <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">
                                Stop {loc_idx + 1}/{len(day_locations)}
                            </span>
                        </div>
                        <div style="margin-bottom: 8px;">
                            <span style="font-weight: bold;">🎯 Type:</span> {location['type'].title()}
                        </div>
                        <div style="margin-bottom: 8px;">
                            <span style="font-weight: bold;">🏷️ Theme:</span> {location['theme'].title()}
                        </div>
                    </div>
                    <div style="border-top: 1px solid #eee; padding-top: 8px; font-size: 12px; color: #666;">
                        <em>{itinerary[day_idx].get('theme', 'Daily exploration')}</em>
                    </div>
                </div>
                """

                folium.Marker(
                    location=[location['lat'], location['lon']],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=f"Day {day_number}: {location['name']}",
                    icon=day_icon,
                ).add_to(m)

            if len(day_locations) > 1:
                route_coords = [[loc['lat'], loc['lon']] for loc in day_locations]
                folium.PolyLine(
                    route_coords,
                    color=color,
                    weight=4,
                    opacity=0.7,
                    popup=f"Day {day_number} Route: {itinerary[day_idx].get('theme', 'Exploring')}",
                    dash_array='5, 10' if day_idx % 2 == 0 else None,
                ).add_to(m)

            if day_locations:
                folium.CircleMarker(
                    location=[day_locations[0]['lat'], day_locations[0]['lon']],
                    radius=6,
                    popup=f"Day {day_number} Start",
                    color=color,
                    fillColor=color,
                    fillOpacity=0.3,
                    weight=2,
                ).add_to(m)

                folium.CircleMarker(
                    location=[day_locations[-1]['lat'], day_locations[-1]['lon']],
                    radius=6,
                    popup=f"Day {day_number} End",
                    color=color,
                    fillColor='white',
                    fillOpacity=0.8,
                    weight=2,
                ).add_to(m)

        for day_idx in range(len(day_routes) - 1):
            current_day_locations = day_routes[day_idx]
            next_day_locations = day_routes[day_idx + 1]

            if current_day_locations and next_day_locations:
                start_point = [current_day_locations[-1]['lat'], current_day_locations[-1]['lon']]
                end_point = [next_day_locations[0]['lat'], next_day_locations[0]['lon']]

                folium.PolyLine(
                    [start_point, end_point],
                    color='#666666',
                    weight=2,
                    opacity=0.4,
                    dash_array='8, 8',
                    popup=f"Travel: Day {day_idx + 1} → Day {day_idx + 2}",
                ).add_to(m)

        folium.LayerControl().add_to(m)

        legend_html = f'''
        <div style="position: fixed;
                    bottom: 50px; left: 50px; width: 300px; height: auto;
                    background: rgba(255,255,255,0.95); border: 1px solid #ddd; z-index: 9999;
                    font-size: 13px; padding: 15px; border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15); backdrop-filter: blur(5px);
                    font-family: Arial, sans-serif;">
            <h4 style="margin: 0 0 12px 0; color: #333; border-bottom: 1px solid #eee;
                      padding-bottom: 8px; font-size: 15px;">
                🗺️ Itinerary Overview
            </h4>
            <p style="margin: 0 0 12px 0; font-size: 12px; color: #666;">
                <strong>{destination.title()}</strong><br>
                {len(itinerary)} days • {len(all_day_locations)} locations
            </p>
        '''

        legend_html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px;">'
        for i in range(min(8, len(itinerary))):
            day = itinerary[i]
            legend_html += f'''
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 16px; height: 16px; background-color: {colors[i]};
                          border-radius: 50%; border: 2px solid white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"></div>
                <span style="font-size: 12px;">Day {day['day']}</span>
            </div>
            '''
        legend_html += '</div>'

        if len(itinerary) > 8:
            legend_html += f'<div style="margin-top: 8px; font-size: 11px; color: #999;">+ {len(itinerary) - 8} more days</div>'

        legend_html += '''
            <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid #eee;
                       font-size: 11px; color: #888;">
                <div>● Day number on markers</div>
                <div>━━ Colored daily routes</div>
                <div>┄┄ Gray travel routes</div>
            </div>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        st.markdown("#### 🎯 Interactive Map Features:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("• **Clean day numbers on pins**")
            st.write("• **Color-coded daily routes**")
        with col2:
            st.write("• **Professional styling**")
            st.write("• **Interactive popups**")
        with col3:
            st.write("• **Multiple map themes**")
            st.write("• **Daily progression**")

        # NOTE: fixed pixel dimensions here don't adapt to mobile screens
        # (unlike the rest of the app's responsive CSS). Consider using
        # `use_container_width`-style behavior or a smaller fixed size for
        # small viewports if mobile support matters.
        folium_static(m, width=800, height=600)

        st.markdown("---")
        st.markdown("#### 📊 Itinerary Statistics")

        total_activities = sum([
            len(day.get('morning', [])) +
            len(day.get('afternoon', [])) +
            len(day.get('evening', []))
            for day in itinerary
        ])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Days", len(itinerary))
        with col2:
            st.metric("Map Locations", len(all_day_locations))
        with col3:
            st.metric("Total Activities", total_activities)
        with col4:
            st.metric("Daily Avg Locations", f"{len(all_day_locations) / len(itinerary):.1f}")

    except Exception as e:
        st.error(f"🗺️ Could not render map: {str(e)}")
        render_itinerary_table_fallback(itinerary)


def render_itinerary_table_fallback(itinerary):
    """Fallback itinerary display used when maps aren't available."""
    st.markdown("#### 📅 Detailed Daily Itinerary")

    for day in itinerary:
        with st.container():
            st.markdown(f"""
            <div style='background: rgba(102, 126, 234, 0.1); padding: 1.5rem;
                        border-radius: 10px; margin: 1rem 0; border-left: 4px solid #667eea;'>
                <h4>🗓️ Day {day['day']}: {day.get('theme', 'Exploring')}</h4>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)

            time_slots = [
                ("🌅 Morning", day.get('morning', [])),
                ("☀️ Afternoon", day.get('afternoon', [])),
                ("🌙 Evening", day.get('evening', [])),
            ]

            for col, (time_label, activities) in zip([col1, col2, col3], time_slots):
                with col:
                    st.write(f"**{time_label}**")
                    for activity in activities:
                        st.write(f"• {activity}")

            if day.get('notes'):
                st.info(f"💡 **Notes:** {day['notes']}")


def render_local_experiences_tab():
    """Render the Local Experiences tab."""
    st.markdown("## ✨ Unique Local Experiences")
    st.markdown("Discover authentic activities and hidden gems recommended by locals.")
    st.markdown("---")

    experiences = st.session_state.get("local_experiences_data", [])

    if not experiences:
        st.info("🎯 Generate a travel plan to explore unique local experiences!")
        return

    for i, exp in enumerate(experiences, 1):
        st.markdown(f'<div class="experience-header">{i}. {exp.get("name", "Unnamed Experience")}</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Cost", exp.get('cost', 'N/A'))
        with col2:
            st.metric("🎯 Type", exp.get('type', 'N/A'))
        with col3:
            st.metric("⏱️ Duration", exp.get('duration', 'N/A'))

        st.markdown("#### 📖 About this Experience")
        st.write(exp.get('description', 'No description available.'))

        why_special_content = exp.get('why_special', 'A unique local experience that offers authentic cultural immersion.')
        st.markdown(f"""
            <div class="special-section">
                <div class="section-header">
                    <span class="section-icon">🌟</span> Why This Experience Is Special
                </div>
                <div style="color: #1a365d; line-height: 1.6;">
                    {why_special_content}
                </div>
            </div>
        """, unsafe_allow_html=True)

        best_time_content = exp.get('best_time_to_visit', 'Flexible timing suitable for most visitors.')
        st.markdown(f"""
            <div class="timing-section">
                <div class="section-header">
                    <span class="section-icon">⏰</span> Ideal Timing & Conditions
                </div>
                <div style="color: #1a365d; line-height: 1.6;">
                    {best_time_content}
                </div>
            </div>
        """, unsafe_allow_html=True)

        tips = exp.get("tips", [])
        if tips:
            tips_html = "".join(f'<div class="tip-item">💡 {tip}</div>' for tip in tips)
            st.markdown(f"""
                <div class="tips-section">
                    <div class="section-header">
                        <span class="section-icon">🎯</span> Pro Tips & Recommendations
                    </div>
                    <div style="margin-top: 0.8rem;">
                        {tips_html}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")


def render_export_section():
    """Export functionality to download the travel plan."""
    if not st.session_state.get('full_plan'):
        st.warning("Please generate a travel plan first before exporting.")
        return

    st.markdown("---")
    st.markdown("### 📤 Export Your Travel Plan")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Export as PDF", use_container_width=True):
            export_as_pdf()

    with col2:
        export_travel_plan()

    st.markdown("---")
    st.markdown("### 👀 Export Preview")

    plan = st.session_state.full_plan
    travel_plan = st.session_state.travel_plan

    with st.expander("📋 Travel Plan Summary", expanded=True):
        st.write(f"**Destination:** {travel_plan.destination}")
        st.write(f"**Duration:** {travel_plan.duration_days} days")
        st.write(f"**Budget:** ${travel_plan.budget:,.2f}")
        st.write(f"**Travel Style:** {travel_plan.travel_style.title()}")
        st.write(f"**Interests:** {', '.join(travel_plan.interests)}")

        st.markdown("---")
        st.markdown("#### 📊 Export Statistics")

        col1, col2, col3 = st.columns(3)
        with col1:
            if plan.get('research'):
                st.metric("Research Sections", len(plan['research']))
        with col2:
            if plan.get('itinerary'):
                st.metric("Itinerary Days", len(plan['itinerary']))
        with col3:
            if plan.get('local_experiences'):
                st.metric("Local Experiences", len(plan['local_experiences']))


def _safe_pdf_text(text):
    """Convert text to a Latin-1-safe string for FPDF's core (non-Unicode)
    fonts. Non-Latin1 characters (e.g. accented names, CJK text) are
    replaced rather than crashing the export.

    NOTE: the previous implementation attempted to load a bundled
    'DejaVuSans.ttf' Unicode font that isn't shipped with this app, so it
    silently fell back to core Arial every time — meaning any non-Latin1
    destination name or activity text was already being mangled by the
    final `.encode('latin-1', 'replace')` step. To properly support
    Unicode names, ship an actual DejaVuSans.ttf file alongside this script
    and register it with `pdf.add_font(..., uni=True)`.
    """
    if text is None:
        return "N/A"
    text = str(text)
    return text.encode('latin-1', 'replace').decode('latin-1')


def export_as_pdf():
    """Export the travel plan as a PDF."""
    if not st.session_state.get('full_plan'):
        st.error("No travel plan available to export.")
        return

    plan = st.session_state.full_plan
    travel_plan = st.session_state.travel_plan

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.set_auto_page_break(auto=True, margin=15)

        safe_text = _safe_pdf_text

        # Title Section
        pdf.set_fill_color(102, 126, 234)
        pdf.rect(0, 0, 210, 40, 'F')

        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 15, safe_text("TRAVEL TRIPY"), ln=True, align='C')
        pdf.set_font("Arial", 'I', 12)
        pdf.cell(0, 10, safe_text("Luxury Travel Plan"), ln=True, align='C')

        pdf.ln(20)
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 10, safe_text("Travel Details"), ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        details_data = [
            ["Destination", travel_plan.destination],
            ["Duration", f"{travel_plan.duration_days} days"],
            ["Total Budget", f"${travel_plan.budget:,.2f}"],
            ["Travel Style", travel_plan.travel_style.title()],
            ["Interests", ", ".join(travel_plan.interests)],
            ["Start Date", travel_plan.start_date],
        ]

        pdf.set_font("Arial", '', 10)
        for label, value in details_data:
            pdf.set_text_color(102, 126, 234)
            pdf.cell(40, 8, safe_text(f"{label}:"), ln=0)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(0, 8, safe_text(value), ln=True)

        pdf.ln(10)

        if plan.get('research'):
            pdf.set_font("Arial", 'B', 14)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(0, 10, safe_text("Destination Research"), ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

            research = plan['research']
            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(102, 126, 234)
            pdf.cell(0, 8, safe_text("Overview"), ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(44, 62, 80)
            pdf.multi_cell(0, 6, safe_text(research.get('overview', 'No overview available')))
            pdf.ln(5)

            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(102, 126, 234)
            pdf.cell(0, 8, safe_text("Top Attractions"), ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(44, 62, 80)

            attractions = research.get('top_attractions', [])
            if isinstance(attractions, dict):
                for i, (key, value) in enumerate(attractions.items(), 1):
                    pdf.cell(10, 6, safe_text(f"{i}."), ln=0)
                    pdf.multi_cell(0, 6, safe_text(f" {value}"))
            elif isinstance(attractions, list):
                for i, attraction in enumerate(attractions, 1):
                    pdf.cell(10, 6, safe_text(f"{i}."), ln=0)
                    if isinstance(attraction, dict):
                        for key, value in attraction.items():
                            pdf.multi_cell(0, 6, safe_text(f" {value}"))
                    else:
                        pdf.multi_cell(0, 6, safe_text(f" {attraction}"))
            pdf.ln(5)

            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(102, 126, 234)
            pdf.cell(0, 8, safe_text("Best Time to Visit"), ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.set_text_color(44, 62, 80)
            pdf.multi_cell(0, 6, safe_text(research.get('best_time_to_visit', 'No timing information available')))

        if plan.get('budget'):
            pdf.add_page()

            pdf.set_fill_color(118, 75, 162)
            pdf.rect(0, 0, 210, 30, 'F')
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 20, safe_text("Budget Breakdown"), ln=True, align='C')

            pdf.ln(15)
            budget = plan['budget']

            col_width = 95
            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(col_width, 10, safe_text("Total Budget:"), ln=0, border=1)
            pdf.set_font("Arial", '', 11)
            pdf.cell(col_width, 10, f"${budget.get('total_budget', 0):,.2f}", ln=True, border=1)

            pdf.set_font("Arial", 'B', 11)
            pdf.cell(col_width, 10, safe_text("Daily Average:"), ln=0, border=1)
            pdf.set_font("Arial", '', 11)
            pdf.cell(col_width, 10, f"${budget.get('daily_average', 0):,.2f}", ln=True, border=1)

            pdf.ln(10)

            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, safe_text("Budget Distribution"), ln=True)
            pdf.ln(5)

            categories = [
                ("Accommodation", budget.get('accommodation', {}).get('total', 0)),
                ("Food & Dining", budget.get('food_dining', {}).get('total', 0)),
                ("Transportation", budget.get('transportation', {}).get('total', 0)),
                ("Activities", budget.get('activities_entertainment', {}).get('total', 0)),
                ("Miscellaneous", budget.get('miscellaneous', {}).get('total', 0)),
            ]

            pdf.set_fill_color(240, 147, 251)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(120, 8, safe_text("Category"), border=1, ln=0, align='C', fill=True)
            pdf.cell(70, 8, safe_text("Amount"), border=1, ln=True, align='C', fill=True)

            pdf.set_text_color(44, 62, 80)
            pdf.set_font("Arial", '', 9)

            for category, amount in categories:
                pdf.cell(120, 7, safe_text(category), border=1, ln=0)
                pdf.cell(70, 7, f"${amount:,.2f}", border=1, ln=True, align='R')

        if plan.get('itinerary'):
            pdf.add_page()

            pdf.set_fill_color(245, 87, 108)
            pdf.rect(0, 0, 210, 30, 'F')
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 20, safe_text("Daily Itinerary"), ln=True, align='C')

            pdf.ln(15)
            pdf.set_text_color(44, 62, 80)

            for day in plan['itinerary']:
                pdf.set_fill_color(76, 175, 80)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 8, safe_text(f"Day {day.get('day', 'N/A')}: {day.get('theme', 'Exploring')}"), ln=True, fill=True, align='C')
                pdf.ln(5)

                pdf.set_text_color(44, 62, 80)
                pdf.set_font("Arial", 'B', 10)

                time_slots = [
                    ("Morning", day.get('morning', [])),
                    ("Afternoon", day.get('afternoon', [])),
                    ("Evening", day.get('evening', [])),
                ]

                for time_label, activities in time_slots:
                    if activities:
                        pdf.set_fill_color(240, 240, 240)
                        pdf.cell(0, 7, safe_text(time_label), ln=True, fill=True)
                        pdf.set_font("Arial", '', 8)
                        for activity in activities:
                            pdf.cell(5, 5, "", ln=0)
                            pdf.multi_cell(0, 5, safe_text(f"- {activity}"))
                        pdf.ln(2)

                if day.get('notes'):
                    pdf.set_fill_color(255, 243, 205)
                    pdf.set_font("Arial", 'I', 8)
                    pdf.multi_cell(0, 5, safe_text(f"Notes: {day['notes']}"), border=1, fill=True)

                pdf.ln(8)

                if pdf.get_y() > 250:
                    pdf.add_page()

        if plan.get('local_experiences'):
            pdf.add_page()

            pdf.set_fill_color(255, 167, 38)
            pdf.rect(0, 0, 210, 30, 'F')
            pdf.set_font("Arial", 'B', 16)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 20, safe_text("Local Experiences"), ln=True, align='C')

            pdf.ln(15)
            pdf.set_text_color(44, 62, 80)

            for i, experience in enumerate(plan['local_experiences'], 1):
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Arial", 'B', 11)
                pdf.set_text_color(102, 126, 234)
                pdf.cell(0, 8, safe_text(f"{i}. {experience.get('name', 'Unnamed Experience')}"), ln=True, fill=True)

                pdf.set_font("Arial", '', 8)
                pdf.set_text_color(44, 62, 80)

                details = [
                    f"Type: {experience.get('type', 'N/A')}",
                    f"Cost: {experience.get('cost', 'N/A')}",
                    f"Duration: {experience.get('duration', 'N/A')}",
                ]

                for detail in details:
                    pdf.cell(0, 5, safe_text(detail), ln=True)

                pdf.multi_cell(0, 5, safe_text(experience.get('description', 'No description available')))
                pdf.ln(3)

                if pdf.get_y() > 250:
                    pdf.add_page()

        pdf.add_page()

        pdf.set_fill_color(102, 126, 234)
        pdf.rect(0, 0, 210, 100, 'F')

        pdf.set_y(40)
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 15, safe_text("Happy Travels!"), ln=True, align='C')

        pdf.set_font("Arial", 'I', 12)
        pdf.cell(0, 10, safe_text("Your adventure awaits"), ln=True, align='C')

        pdf.ln(30)
        pdf.set_text_color(44, 62, 80)
        pdf.set_font("Arial", '', 9)
        pdf.cell(0, 8, safe_text("Generated by Travel Tripy - Your AI Travel Assistant"), ln=True, align='C')
        pdf.cell(0, 8, f"Created on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')

        pdf.ln(20)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 10, safe_text("Final Travel Tips:"), ln=True)
        pdf.set_font("Arial", '', 8)

        tips = [
            "Keep digital copies of important documents",
            "Learn basic phrases in the local language",
            "Check visa requirements well in advance",
            "Purchase comprehensive travel insurance",
            "Download offline maps before departure",
            "Inform your bank about travel dates",
            "Pack a portable charger for devices",
            "Respect local customs and traditions",
        ]

        for tip in tips:
            pdf.cell(0, 6, safe_text(f"- {tip}"), ln=True)

        # FIXED: fpdf2's `output(dest='S')` already returns `bytes`/
        # `bytearray` in current versions (unlike the classic pyfpdf, which
        # returned a `str`). Calling `.encode(...)` unconditionally on the
        # result crashes on fpdf2. Handle both cases explicitly.
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, (bytes, bytearray)):
            pdf_bytes = bytes(pdf_output)
        else:
            pdf_bytes = pdf_output.encode('latin-1', 'replace')

        st.download_button(
            label="📥 Download Professional PDF",
            data=pdf_bytes,
            file_name=f"Travel_Tripy_Plan_{travel_plan.destination.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.success("✅ Professional PDF Generated Successfully!")
        st.info(f"📄 Document contains {pdf.page_no()} pages of detailed travel information")

    except Exception as e:
        st.error(f"❌ PDF generation failed: {str(e)}")
        st.info("Creating simplified PDF version...")
        try:
            simple_pdf_bytes = create_simple_pdf(plan, travel_plan)
            st.download_button(
                label="📥 Download Simplified PDF",
                data=simple_pdf_bytes,
                file_name=f"Travel_Plan_{travel_plan.destination.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception:
            st.error("Could not generate PDF. Please try the text export instead.")


def create_simple_pdf(plan, travel_plan):
    """Simplified PDF fallback (no complex formatting)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "TRAVEL TRIPY - TRAVEL PLAN", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Travel Details:", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 8, _safe_pdf_text(f"Destination: {travel_plan.destination}"), ln=True)
    pdf.cell(0, 8, f"Duration: {travel_plan.duration_days} days", ln=True)
    pdf.cell(0, 8, f"Budget: ${travel_plan.budget:,.2f}", ln=True)
    pdf.cell(0, 8, _safe_pdf_text(f"Travel Style: {travel_plan.travel_style}"), ln=True)

    pdf.ln(10)

    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, (bytes, bytearray)):
        return bytes(pdf_output)
    return pdf_output.encode('latin-1', 'replace')


def export_travel_plan():
    """Export the complete travel plan as a downloadable text file."""
    if not st.session_state.get('full_plan'):
        return

    plan = st.session_state.full_plan
    travel_plan = st.session_state.travel_plan

    def format_list_items(items, default_text="N/A"):
        if not items:
            return default_text
        if isinstance(items, list):
            return chr(10).join(['• ' + str(item) for item in items])
        elif isinstance(items, dict):
            return chr(10).join(['• ' + str(value) for value in items.values()])
        else:
            return str(items)

    export_content = f"""
    🎉 TRAVEL TRIPY - LUXURY TRAVEL PLAN
    ====================================

    📍 DESTINATION: {travel_plan.destination}
    📅 TRIP DURATION: {travel_plan.duration_days} days
    💰 TOTAL BUDGET: ${travel_plan.budget:,.2f}
    🎯 TRAVEL STYLE: {travel_plan.travel_style.title()}
    ❤️ INTERESTS: {', '.join(travel_plan.interests)}
    🗓️ START DATE: {travel_plan.start_date}

    📋 GENERATED ON: {plan.get('created_at', 'N/A')}

    ====================================
    📊 DESTINATION RESEARCH
    ====================================

    🌟 Overview:
    {plan.get('research', {}).get('overview', 'N/A')}

    🌤️ Best Time to Visit:
    {plan.get('research', {}).get('best_time_to_visit', 'N/A')}

    🏛️ Top Attractions:
    {format_list_items(plan.get('research', {}).get('top_attractions', []))}

    🎭 Local Culture:
    {plan.get('research', {}).get('local_culture', 'N/A')}

    💡 Budget Tips:
    {format_list_items(plan.get('research', {}).get('budget_tips', []))}

    ====================================
    💰 BUDGET BREAKDOWN
    ====================================
    """

    budget_data = plan.get('budget', {})
    export_content += f"""
    Total Budget: ${budget_data.get('total_budget', 0):,.2f}
    Daily Average: ${budget_data.get('daily_average', 0):,.2f}
    """

    categories = ['accommodation', 'food_dining', 'transportation', 'activities_entertainment', 'miscellaneous']
    for category in categories:
        category_data = budget_data.get(category, {})
        if isinstance(category_data, dict):
            export_content += f"\n{category.title().replace('_', ' ')}: ${category_data.get('total', 0):,.2f}"
        else:
            export_content += f"\n{category.title().replace('_', ' ')}: ${category_data:,.2f}"

    export_content += """

    ====================================
    📅 DAILY ITINERARY
    ====================================

    """

    itinerary = plan.get('itinerary', [])
    for day in itinerary:
        export_content += f"""
    🗓️ DAY {day.get('day', 'N/A')}: {day.get('theme', 'Exploring')}
    {'=' * 50}

    🌅 MORNING:
    {format_list_items(day.get('morning', []))}

    ☀️ AFTERNOON:
    {format_list_items(day.get('afternoon', []))}

    🌙 EVENING:
    {format_list_items(day.get('evening', []))}

    💡 Notes: {day.get('notes', '')}

        """

    export_content += """
    ====================================
    🌟 LOCAL EXPERIENCES
    ====================================

    """

    experiences = plan.get('local_experiences', [])
    for i, experience in enumerate(experiences, 1):
        export_content += f"""
    {i}. {experience.get('name', 'Unnamed Experience')}
       Type: {experience.get('type', 'N/A')}
       Cost: {experience.get('cost', 'N/A')}
       Duration: {experience.get('duration', 'N/A')}

       Description: {experience.get('description', 'N/A')}

       Why Special: {experience.get('why_special', 'N/A')}

       Best Time: {experience.get('best_time_to_visit', 'N/A')}

       Tips:
       {format_list_items(experience.get('tips', []))}

        """

    export_content += """
    ====================================
    🎉 BONUS TIPS
    ====================================

    ✈️ Travel Smart:
    • Always keep digital copies of important documents
    • Learn a few basic phrases in the local language
    • Check visa requirements well in advance
    • Purchase travel insurance for peace of mind

    📱 Stay Connected:
    • Download offline maps before you go
    • Save emergency contact numbers locally
    • Inform your bank about your travel dates
    • Pack a portable charger for your devices

    🌍 Travel Responsibly:
    • Respect local customs and traditions
    • Support local businesses and artisans
    • Be mindful of your environmental impact
    • Leave places better than you found them

    ====================================
    🚀 Happy Travels from Travel Tripy!
    ====================================
    """

    st.download_button(
        label="📥 Download Travel Plan",
        data=export_content,
        file_name=f"Travel_Tripy_Plan_{travel_plan.destination.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        use_container_width=True,
    )


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 1rem;'>
            <h1 style='color: white; font-size: 2rem;'>🌍</h1>
            <h2 style='color: white;'>🗺️Travel Tripy 🛩️Let's Go!</h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("### 📑 Navigation")

        nav_options = {
            "🏠 Home": "home",
            "🔍 Research": "research",
            "💰 Budget": "budget",
            "📅 Itinerary": "itinerary",
            "🌟 Experiences": "experiences",
            "💾 Export": "export",
        }

        for nav_name, nav_id in nav_options.items():
            if st.button(nav_name, use_container_width=True, key=nav_id):
                st.session_state.current_section = nav_id
                st.rerun()

        setup_background_music()

        st.markdown("---")

        st.markdown("### 📤 Export")
        if st.button("💾 Export Plan", use_container_width=True, key="export_btn"):
            st.session_state.current_section = 'export'
            st.rerun()

        st.markdown("### Developer: Vrushabh Patil👨‍💻")
        st.markdown("[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/patilvrushabh/)")
        st.markdown("[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/vrushabh-09)")

        st.markdown("---")

        if st.session_state.get('travel_plan'):
            st.markdown("### 📊 Trip Summary")
            plan = st.session_state.travel_plan
            st.markdown(f"<p style='color: white;'><strong>📍 {plan.destination}</strong></p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: white;'>📅 {plan.duration_days} days</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: white;'>💰 ${plan.budget:,.0f}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: white;'>🎯 {plan.travel_style.title()}</p>", unsafe_allow_html=True)

            if st.session_state.get('full_plan'):
                st.markdown(f"<p style='color: white;'>🕐 {st.session_state.full_plan.get('created_at', 'N/A')}</p>", unsafe_allow_html=True)

            if st.button("🗑️ Start New Plan", use_container_width=True):
                for key in ['full_plan', 'research_data', 'budget_data', 'itinerary_data', 'local_experiences_data', 'travel_plan', 'plan_generated']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.current_section = 'home'
                st.rerun()

        st.markdown("""
        <div style='text-align: center; padding: 0.5rem; background: rgba(255,255,255,0.1); border-radius: 8px;'>
            <p style='color: white; font-size: 0.7rem; margin: 0;'>
                © 2025 Travel Tripy<br>
                <small>All Rights Reserved</small>
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_home_tab():
    destination, budget, duration, travel_style, interests, start_date = render_input_section()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Generate Luxury Travel Plan", use_container_width=True, type="primary"):
            if not destination.strip():
                st.error("❌ Please enter a destination")
                return

            if budget < 100:
                st.error("❌ Budget should be at least $100")
                return

            travel_plan = TravelPlan(
                destination=destination.strip(),
                budget=float(budget),
                duration_days=int(duration),
                travel_style=travel_style,
                interests=[x.strip() for x in interests.split(",") if x.strip()],
                start_date=start_date.strftime("%Y-%m-%d"),
            )

            with st.spinner("Creating your luxury travel experience..."):
                coordinator = TravelCoordinator()
                complete_plan = coordinator.create_complete_travel_plan(travel_plan)

                st.session_state.full_plan = complete_plan
                st.session_state.travel_plan = travel_plan
                st.session_state.research_data = complete_plan.get('research', {})
                st.session_state.budget_data = complete_plan.get('budget', {})
                st.session_state.itinerary_data = complete_plan.get('itinerary', [])
                st.session_state.local_experiences_data = complete_plan.get('local_experiences', [])
                st.session_state.plan_generated = True

            st.success("🎉 Luxury travel plan generated successfully! Navigate through the sections to explore your personalized itinerary.")
            st.balloons()

    if not st.session_state.plan_generated:
        st.markdown("---")

        st.markdown("""
        <div class="premium-features-section">
            <h2 class="premium-features-title">✨ Premium Features</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem;">
        """, unsafe_allow_html=True)

        features = [
            {"icon": "🔍", "title": "AI Research", "desc": "Comprehensive destination insights powered by AI"},
            {"icon": "💰", "title": "Smart Budgeting", "desc": "Intelligent budget allocation with visual analytics"},
            {"icon": "📅", "title": "Daily Planning", "desc": "Hour-by-hour itineraries with realistic timing"},
            {"icon": "🌟", "title": "Local Gems", "desc": "Hidden spots and authentic experiences beyond tourism"},
        ]

        for feature in features:
            st.markdown(f"""
            <div style='background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 15px;
            padding: 2rem; margin-bottom: 1.5rem; text-align: center; border: 1px solid rgba(255,255,255,0.2); transition: all 0.3s ease;'>
                <div style='font-size: 2.5rem; margin-bottom: 1rem;'>{feature['icon']}</div>
                <h4 style='color: #1a1a1a; margin-bottom: 0.5rem; font-weight: 600;'>{feature['title']}</h4>
                <p style='color: #2d2d2d; margin: 0; line-height: 1.5;'>{feature['desc']}</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)


def main():
    # FIXED: previously there were TWO `main()` definitions in this file —
    # a dead one at the very top (before `st` was even imported, referencing
    # a nonexistent `render_copyright()`), silently overwritten by this one.
    # The dead copy has been removed entirely.
    render_missing_keys_warning()

    load_css()
    init_session_state()

    render_sidebar()
    render_background_music()
    render_hero_section()

    section = st.session_state.current_section
    if section == 'home':
        render_home_tab()
    elif section == 'research':
        render_research_tab()
    elif section == 'budget':
        render_budget_tab()
    elif section == 'itinerary':
        render_itinerary_tab()
    elif section == 'experiences':
        render_local_experiences_tab()
    elif section == 'export':
        render_export_section()


if __name__ == "__main__":
    main()

# =============================================================================
# Copyright (c) 2025 Travel Tripy - Vrushabh Patil
# All Rights Reserved.
#
# This software is protected by copyright law and international treaties.
# Unauthorized copying, distribution, or modification of this software
# may result in severe civil and criminal penalties.
#
# For licensing inquiries: vrushabhpatil97711@gmail.com
# =============================================================================
