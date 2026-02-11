import streamlit as st

def apply_custom_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Outfit:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        color: #1E1E1E;
    }

    /* Glassmorphism Card Effect */
    .stCard {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        margin-bottom: 20px;
    }

    /* Premium Button Style */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 10px 24px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(118, 75, 162, 0.4);
        color: white;
    }

    /* Metric Card Styling */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem;
        font-weight: 700;
        color: #764ba2;
    }
    
    /* Navigation styling */
    .sidebar .sidebar-content {
        background-image: linear-gradient(#2e7bcf,#2e7bcf);
        color: white;
    }

    /* Dark Mode support adjustments if needed */
    @media (prefers-color-scheme: dark) {
        .stCard {
            background: rgba(30, 30, 30, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
        }
        h1, h2, h3 { color: #F5F5F5; }
    }
    </style>
    """, unsafe_allow_html=True)

def render_metric_card(label, value, color="#764ba2", icon="📦"):
    st.markdown(f"""
    <div class="stCard">
        <h4 style="margin:0; color: #666; font-size: 0.9rem;">{label}</h4>
        <div style="display:flex; align-items: baseline; gap: 10px;">
            <span style="font-size: 2rem; font-weight: 700; color: {color};">{value}</span>
            <span style="font-size: 1.2rem;">{icon}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
