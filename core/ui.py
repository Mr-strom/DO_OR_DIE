import streamlit as st

def inject_theme():
    """Injects high-density styling: Inter font, orange accents, compact spacing."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
            
            html, body, [class*="css"] {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                color: #0F172A;
            }
            
            /* Remove excess header whitespace */
            .block-container {
                padding-top: 1.5rem !important;
                padding-bottom: 2rem !important;
                max-width: 96% !important;
            }
            
            /* Primary button styling */
            div.stButton > button:first-child {
                background-color: #F97316;
                color: #FFFFFF;
                font-weight: 600;
                border: 1px solid #EA580C;
                border-radius: 6px;
                padding: 0.4rem 1rem;
                transition: all 0.15s ease-in-out;
            }
            div.stButton > button:first-child:hover {
                background-color: #EA580C;
                border-color: #C2410C;
                color: #FFFFFF;
                box-shadow: 0 4px 12px rgba(249, 115, 22, 0.25);
            }
            
            /* Custom Cards */
            .dense-card {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 1rem 1.25rem;
                margin-bottom: 0.75rem;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            }
            .dense-card:hover {
                border-color: #CBD5E1;
            }
            
            /* Metric Boxes */
            .metric-box {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-left: 4px solid #F97316;
                border-radius: 6px;
                padding: 0.75rem 1rem;
            }
            .metric-title {
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #64748B;
            }
            .metric-value {
                font-size: 1.4rem;
                font-weight: 700;
                color: #0F172A;
                margin-top: 0.2rem;
            }
            
            /* Badges */
            .badge-role {
                display: inline-block;
                padding: 0.2rem 0.6rem;
                font-size: 0.75rem;
                font-weight: 700;
                border-radius: 9999px;
                text-transform: uppercase;
            }
            .badge-sponsor { background-color: #FEF3C7; color: #B45309; }
            .badge-mentor  { background-color: #E0E7FF; color: #4338CA; }
            .badge-student { background-color: #FFEDD5; color: #C2410C; }
            
            /* Ledger Hashes */
            .hash-tag {
                font-family: 'JetBrains Mono', monospace;
                background-color: #F1F5F9;
                color: #475569;
                padding: 0.15rem 0.4rem;
                border-radius: 4px;
                font-size: 0.75rem;
                border: 1px solid #E2E8F0;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_metric_card(label: str, value: str, subtext: str = ""):
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-title">{label}</div>
            <div class="metric-value">{value}</div>
            <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 0.2rem;">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_role_badge(role: str):
    role_cls = {
        "Sponsor": "badge-sponsor",
        "Mentor": "badge-mentor",
        "Student": "badge-student"
    }.get(role, "badge-student")
    
    st.markdown(
        f'<span class="badge-role {role_cls}">{role} View</span>', 
        unsafe_allow_html=True
    )

def notify_ledger_action(action: str, current_hash: str):
    short_hash = current_hash[:8] if current_hash else "--------"
    st.toast(f"🔒 {action} [Ledger: {short_hash}]", icon="⚡")
