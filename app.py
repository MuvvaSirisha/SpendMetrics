# ─────────────────────────────────────────────────────────────────────────────
# app.py — SpendSense Application Entry Point
#
# PURPOSE:
#   This is the FIRST file Streamlit runs: `streamlit run app.py`
#   It is responsible for:
#     1. Page configuration (title, icon, layout)
#     2. Applying a consistent visual theme with custom CSS
#     3. Building the sidebar navigation
#     4. Routing to the correct page module based on the user's selection
#
# FLOW:
#   User opens browser → Streamlit runs app.py → sidebar renders →
#   user clicks a page → the matching page module is imported and rendered.
#
# INTERVIEW TIP:
#   "app.py is the shell of the application. It sets up the layout and
#    navigation. Each page lives in its own file under pages/, which keeps
#    the code organized and easy to maintain."
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
from utils.config import APP_NAME, APP_ICON, APP_VERSION, THEME

# ── Page Configuration ─────────────────────────────────────────────────────────
# Must be the FIRST Streamlit call in the script.
# layout="wide" uses the full browser width — better for dashboards.
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Custom CSS (Visual Theme) ──────────────────────────────────────────────────
# We inject a small amount of CSS to override Streamlit's default colors
# and apply our navy/white/green theme consistently across all pages.
def apply_custom_css():
    """Inject custom CSS to apply the SpendSense color theme."""
    st.markdown(
        f"""
        <style>
        /* ── Global Background ── */
        .stApp {{
            background-color: {THEME['background']};
        }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background-color: {THEME['primary']};
        }}
        [data-testid="stSidebar"] * {{
            color: white !important;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            color: white !important;
            font-size: 15px;
            padding: 6px 0;
        }}

        /* ── Metric Cards ── */
        [data-testid="metric-container"] {{
            background-color: {THEME['card']};
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        /* ── Section Headers ── */
        h1, h2, h3 {{
            color: {THEME['primary']};
        }}

        /* ── Positive numbers (income, surplus) ── */
        .positive {{
            color: {THEME['secondary']};
            font-weight: bold;
        }}

        /* ── Negative numbers (expenses, deficit) ── */
        .negative {{
            color: {THEME['danger']};
            font-weight: bold;
        }}

        /* ── Alert / Warning banners ── */
        .alert-warning {{
            background-color: #FFF3CD;
            border-left: 4px solid {THEME['warning']};
            padding: 12px 16px;
            border-radius: 4px;
            margin: 8px 0;
        }}
        .alert-danger {{
            background-color: #FADBD8;
            border-left: 4px solid {THEME['danger']};
            padding: 12px 16px;
            border-radius: 4px;
            margin: 8px 0;
        }}
        .alert-success {{
            background-color: #D5F5E3;
            border-left: 4px solid {THEME['secondary']};
            padding: 12px 16px;
            border-radius: 4px;
            margin: 8px 0;
        }}

        /* ── Hide Streamlit default footer ── */
        footer {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Navigation Definition ──────────────────────────────────────────────────────
# Each entry is: (display_label, emoji_icon, module_path)
# We import the page module dynamically when the user selects it.
PAGES = [
    ("Dashboard",           "📊", "views.dashboard"),
    ("Transactions",        "💳", "views.transactions"),
    ("Insights & Budgets",  "🎯", "views.budgets"),
    ("Settings",            "⚙️",  "views.settings"),
]


def render_sidebar() -> str:
    """
    Render the sidebar header and navigation menu.
    Returns the name of the page the user has selected.
    """
    with st.sidebar:
        # ── App Logo / Title ─────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="text-align:center; padding: 20px 0 10px 0;">
                <div style="font-size:48px;">{APP_ICON}</div>
                <div style="font-size:22px; font-weight:700; color:white; margin-top:4px;">
                    {APP_NAME}
                </div>
                <div style="font-size:12px; color:rgba(255,255,255,0.6); margin-top:2px;">
                    Personal Finance Analytics
                </div>
            </div>
            <hr style="border-color:rgba(255,255,255,0.2); margin: 8px 0 16px 0;">
            """,
            unsafe_allow_html=True,
        )

        # ── Navigation Radio Buttons ─────────────────────────────────────────
        st.markdown(
            "<div style='color:rgba(255,255,255,0.7); font-size:11px; "
            "font-weight:600; letter-spacing:1px; margin-bottom:8px;'>"
            "NAVIGATION</div>",
            unsafe_allow_html=True,
        )

        page_labels = [f"{icon}  {label}" for label, icon, _ in PAGES]
        selected_label = st.radio(
            label="Navigation",        # Required by Streamlit; hidden with CSS
            options=page_labels,
            label_visibility="collapsed",
            key="nav_selection",
        )

        # ── Footer ───────────────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="position:fixed; bottom:20px; left:0; width:250px;
                        text-align:center; color:rgba(255,255,255,0.4);
                        font-size:11px;">
                {APP_NAME} v{APP_VERSION}<br>
                Built with Streamlit 🚀
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Extract the plain page name (strip icon prefix)
    # e.g. "📊  Dashboard" → "Dashboard"
    selected_page_name = selected_label.split("  ", 1)[1]
    return selected_page_name


def load_page(page_name: str):
    """
    Dynamically import and run the selected page module.

    HOW IT WORKS:
        Each file under pages/ (e.g. pages/dashboard.py) defines a function
        called `render()`. We import the module and call render().
        This keeps app.py clean — it only handles routing, not content.
    """
    import importlib

    # Find the module path for the selected page name
    module_path = None
    for label, _, path in PAGES:
        if label == page_name:
            module_path = path
            break

    if module_path is None:
        st.error(f"Page '{page_name}' not found. This is a bug — please report it.")
        return

    try:
        module = importlib.import_module(module_path)
        module.render()
    except ImportError as e:
        # This page hasn't been built yet — show a friendly "coming soon" state
        st.info(
            f"🚧 **{page_name}** is being built.\n\n"
            f"This page will be available in the next development step.\n\n"
            f"_Technical detail: {e}_"
        )
    except Exception as e:
        st.error(f"⚠️ An error occurred while loading **{page_name}**: {e}")
        st.exception(e)  # Shows the full traceback for debugging


# ── Main Entry Point ───────────────────────────────────────────────────────────
def main():
    """Main function — called every time Streamlit reruns the script."""
    apply_custom_css()
    selected_page = render_sidebar()
    load_page(selected_page)


if __name__ == "__main__":
    main()
