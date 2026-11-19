import os
import re
from pathlib import Path
import streamlit as st

from services.project_service import (
    create_project,
    get_active_projects,
    get_hidden_projects,
    hide_project,
    restore_project
)

from modules.project_zip_handler import extract_cpp_project_zip
from modules.project_detector import detect_cpp_project_structure
from modules.github_actions_runner import run_github_cpp_tests
from modules.external_github_runner import run_external_cpp_tests
from modules.code_comparator import compare_code
from modules.mcp_client import (
    analyze_code_impact_via_mcp,
    scan_cpp_project_via_mcp
)
from modules.dependency_visualizer import create_dependency_graph
from modules.llm_explainer import generate_impact_explanation
from modules.risk_analyzer import calculate_change_risk
from modules.test_case_generator import generate_cpp_test_suite

# --------------------------------------------------
# PROJECT PATH CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

@st.cache_data(show_spinner=False)
def get_project_scan(project_path):

    scan_response = scan_cpp_project_via_mcp(
        project_path
    )

    return scan_response["scan"]


def resolve_project_path(project_path):
    if not project_path:
        return None

    normalized_path = str(project_path).replace("\\", "/")

    # Convert old Windows paths into paths relative to the repository
    if "impactmap-ai/" in normalized_path:
        normalized_path = normalized_path.split(
            "impactmap-ai/", 1
        )[1]

    candidate_path = Path(normalized_path)

    if not candidate_path.is_absolute():
        candidate_path = BASE_DIR / candidate_path

    return str(candidate_path.resolve())

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="ImpactMap AI",
    page_icon="🔍",
    layout="wide"
)

# Saved Projects is closed by default and opens only when requested.
if "show_saved_projects" not in st.session_state:
    st.session_state.show_saved_projects = False


st.markdown("""
<style>
    :root {
        --im-bg: #0b1220;
        --im-panel: #111c2e;
        --im-panel-soft: #162338;
        --im-border: rgba(148, 163, 184, 0.18);
        --im-text: #e5edf8;
        --im-muted: #94a3b8;
        --im-blue: #60a5fa;
        --im-cyan: #22d3ee;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 12% 0%, rgba(37, 99, 235, 0.13), transparent 34%),
            linear-gradient(145deg, #0b1220 0%, #0e1727 55%, #101b2d 100%);
        color: var(--im-text);
    }

    .block-container {
        max-width: none !important;
        width: 100% !important;
        /* Keep the first app element below Streamlit's fixed Deploy toolbar. */
        padding-top: 4.1rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-bottom: 3rem;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #101a2b 0%, #0c1422 100%);
        border-right: 1px solid var(--im-border);
        min-width: 17rem;
        max-width: 17rem;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #cbd5e1;
    }

    h1, h2, h3 {
        color: #f1f5f9 !important;
        letter-spacing: -0.025em;
    }

    h1 { font-size: 2.15rem !important; font-weight: 780 !important; }
    h2 { font-size: 1.45rem !important; font-weight: 720 !important; }
    h3 { font-size: 1.12rem !important; font-weight: 680 !important; }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(23, 39, 62, .96), rgba(17, 29, 47, .96));
        border: 1px solid var(--im-border);
        border-radius: 13px;
        padding: 15px 17px;
        box-shadow: 0 8px 24px rgba(0,0,0,.12);
    }

    [data-testid="stMetricLabel"] {
        color: #a9bad0 !important;
        font-size: .82rem !important;
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 750 !important;
    }

    [data-testid="stTextArea"] textarea,
    [data-testid="stTextInput"] input {
        background: #0d1727 !important;
        color: #e2e8f0 !important;
        border: 1px solid #33445e !important;
        border-radius: 9px !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 13px;
        line-height: 1.55;
    }

    [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #111e31;
        border-color: #33445e;
        border-radius: 9px;
    }

    [data-testid="stForm"], [data-testid="stExpander"] {
        background: rgba(17, 28, 46, .68);
        border: 1px solid var(--im-border);
        border-radius: 12px;
    }

    [data-testid="stForm"] { padding: 20px; }

    .stButton > button,
    [data-testid="stFormSubmitButton"] button {
        border-radius: 9px;
        font-weight: 680;
        min-height: 42px;
        border: 1px solid rgba(96, 165, 250, .35);
        transition: all .18s ease;
    }

    .stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: linear-gradient(100deg, #2563eb, #0e7490);
        color: white;
        border: 0;
    }

    .stButton > button:hover {
        border-color: #60a5fa;
        transform: translateY(-1px);
        box-shadow: 0 5px 18px rgba(37, 99, 235, .18);
    }

    [data-testid="stCode"] {
        border: 1px solid var(--im-border);
        border-radius: 10px;
    }

    [data-testid="stAlert"] {
        border-radius: 10px;
    }

    [data-testid="stCaptionContainer"] {
        color: #94a3b8;
    }

    hr {
        border-color: rgba(148, 163, 184, .18);
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
    }


    /* Top workspace navigation */
    .im-navbar {
        position: relative;
        z-index: 5;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        flex-wrap: wrap;
        width: 100%;
        box-sizing: border-box;
        padding: 12px 20px;
        margin: 0 0 .85rem 0;
        border: 1px solid rgba(96,165,250,.24);
        border-radius: 10px;
        background: linear-gradient(100deg, rgba(13,25,43,.99), rgba(17,37,58,.98));
        box-shadow: 0 8px 24px rgba(0,0,0,.16);
    }
    .im-nav-brand {
        color: #f1f5f9 !important;
        font-weight: 800;
        letter-spacing: -.02em;
        white-space: nowrap;
        text-decoration: none !important;
    }
    .im-nav-links {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        flex-wrap: wrap;
    }
    .im-nav-links a {
        color: #cbd5e1 !important;
        text-decoration: none !important;
        font-size: .82rem;
        font-weight: 650;
        padding: 8px 11px;
        border-radius: 7px;
        transition: background .15s ease, color .15s ease;
    }
    .im-nav-links a:hover {
        color: #eff6ff !important;
        background: rgba(59,130,246,.2);
    }
    .im-nav-status {
        color: #86efac;
        border: 1px solid rgba(74,222,128,.25);
        background: rgba(22,163,74,.10);
        border-radius: 20px;
        padding: 5px 9px;
        font-size: .68rem;
        font-weight: 750;
        letter-spacing: .06em;
        white-space: nowrap;
    }
    @media (max-width: 760px) {
        .im-navbar { align-items: flex-start; }
        .im-nav-links { justify-content: flex-start; width: 100%; }
        .im-nav-links a { padding: 7px 8px; }
    }

    /* Compact section rhythm */
    [data-testid="stVerticalBlock"] > [data-testid="stMarkdownContainer"] h2 {
        padding-bottom: .35rem;
        border-bottom: 1px solid rgba(96, 165, 250, .18);
    }

    @media (max-width: 800px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        h1 { font-size: 1.7rem !important; }
    }
</style>
""", unsafe_allow_html=True)



# Top workspace navigation. The links scroll to the relevant sections;
# Saved Projects is a real Streamlit button (not HTML text).
st.markdown(
    """
    <nav class="im-navbar" aria-label="ImpactMap AI workspace navigation">
      <a class="im-nav-brand" href="#impactmap-overview">⌘ ImpactMap AI</a>
      <div class="im-nav-links">
        <a href="#project-registration">Register</a>
        <a href="#registered-projects">Projects</a>
        <a href="#code-impact-analysis">Code Analysis</a>
        <a href="#test-runs">Test Runs</a>
        <a href="#risk-analysis">Risk Analysis</a>
      </div>
      <span class="im-nav-status">● WORKSPACE</span>
    </nav>
    """,
    unsafe_allow_html=True
)

# Product identity and developer-oriented workspace header
st.markdown(
    """
    <div id="impactmap-overview" style="
        padding: 1.35rem 1.55rem;
        margin: .2rem 0 1.1rem 0;
        border: 1px solid rgba(96,165,250,.25);
        border-radius: 16px;
        background: linear-gradient(112deg, rgba(20,42,72,.96), rgba(15,32,52,.88) 58%, rgba(12,74,92,.42));
        box-shadow: 0 14px 35px rgba(0,0,0,.16);
    ">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span style="font-size:1.65rem;">⌘</span>
        <span style="font-size:1.65rem;font-weight:800;letter-spacing:-.04em;color:#f8fafc;">ImpactMap AI</span>
        <span style="font-size:.68rem;font-weight:700;letter-spacing:.12em;color:#93c5fd;border:1px solid rgba(147,197,253,.35);padding:5px 9px;border-radius:20px;">ENGINEERING INTELLIGENCE</span>
      </div>
      <div style="font-size:1.05rem;font-weight:650;color:#dbeafe;margin-top:.55rem;">
        Intelligent Code Change Impact Analyzer
      </div>
      <div style="font-size:.88rem;color:#a9bdd5;margin-top:.45rem;max-width:900px;line-height:1.55;">
        Trace code changes, discover dependencies, generate requirement-based tests,
        execute C++ validation remotely, and understand change risk.
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:1rem;">
        <span style="font-size:.72rem;color:#bfdbfe;background:rgba(37,99,235,.18);padding:5px 9px;border-radius:6px;">C++ ANALYSIS</span>
        <span style="font-size:.72rem;color:#a5f3fc;background:rgba(8,145,178,.16);padding:5px 9px;border-radius:6px;">MCP</span>
        <span style="font-size:.72rem;color:#c4b5fd;background:rgba(124,58,237,.16);padding:5px 9px;border-radius:6px;">RAG</span>
        <span style="font-size:.72rem;color:#86efac;background:rgba(22,163,74,.14);padding:5px 9px;border-radius:6px;">GITHUB ACTIONS</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Compact overview strip fills the top workspace area without changing app logic.
st.markdown(
    """
    <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:-.15rem 0 1.15rem 0;">
      <div style="padding:13px 15px;border:1px solid rgba(96,165,250,.22);border-radius:11px;background:linear-gradient(145deg,rgba(22,43,70,.88),rgba(17,29,47,.88));">
        <div style="font-size:.66rem;letter-spacing:.1em;font-weight:750;color:#93c5fd;">01 / WORKSPACE</div>
        <div style="font-size:.91rem;font-weight:700;color:#f1f5f9;margin-top:5px;">Project Discovery</div>
        <div style="font-size:.74rem;color:#9fb1c8;margin-top:3px;">Register · Upload · Scan</div>
      </div>
      <div style="padding:13px 15px;border:1px solid rgba(34,211,238,.2);border-radius:11px;background:linear-gradient(145deg,rgba(15,49,64,.82),rgba(17,29,47,.88));">
        <div style="font-size:.66rem;letter-spacing:.1em;font-weight:750;color:#67e8f9;">02 / INTELLIGENCE</div>
        <div style="font-size:.91rem;font-weight:700;color:#f1f5f9;margin-top:5px;">Code Impact</div>
        <div style="font-size:.74rem;color:#9fb1c8;margin-top:3px;">Compare · Trace · Map</div>
      </div>
      <div style="padding:13px 15px;border:1px solid rgba(167,139,250,.2);border-radius:11px;background:linear-gradient(145deg,rgba(43,34,72,.78),rgba(17,29,47,.88));">
        <div style="font-size:.66rem;letter-spacing:.1em;font-weight:750;color:#c4b5fd;">03 / VALIDATION</div>
        <div style="font-size:.91rem;font-weight:700;color:#f1f5f9;margin-top:5px;">Test Automation</div>
        <div style="font-size:.74rem;color:#9fb1c8;margin-top:3px;">Generate · Execute · Verify</div>
      </div>
      <div style="padding:13px 15px;border:1px solid rgba(74,222,128,.2);border-radius:11px;background:linear-gradient(145deg,rgba(22,54,48,.78),rgba(17,29,47,.88));">
        <div style="font-size:.66rem;letter-spacing:.1em;font-weight:750;color:#86efac;">04 / DECISION</div>
        <div style="font-size:.91rem;font-weight:700;color:#f1f5f9;margin-top:5px;">Risk Intelligence</div>
        <div style="font-size:.74rem;color:#9fb1c8;margin-top:3px;">Assess · Explain · Review</div>
      </div>
    </div>
    <style>
      @media (max-width: 900px) {
        div[style*="grid-template-columns:repeat(4"] { grid-template-columns:repeat(2,minmax(0,1fr)) !important; }
      }
      @media (max-width: 520px) {
        div[style*="grid-template-columns:repeat(4"] { grid-template-columns:1fr !important; }
      }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------

with st.sidebar:

    # BRANDING + WORKSPACE MODULES
    st.markdown(
        """
        <div style="padding:.5rem 0 1rem 0;">
          <div style="font-size:1.08rem;font-weight:800;color:#f1f5f9;">
            ⌘ ImpactMap AI
          </div>
          <div style="font-size:.7rem;letter-spacing:.12em;color:#7dd3fc;margin-top:3px;">
            DEVELOPER WORKSPACE
          </div>
        </div>

        <div style="border-top:1px solid rgba(148,163,184,.2);padding-top:1rem;">
          <div style="font-size:.7rem;font-weight:700;letter-spacing:.1em;color:#94a3b8;margin-bottom:.6rem;">
            WORKSPACE MODULES
          </div>

          <div style="padding:.48rem .6rem;border-radius:7px;background:rgba(37,99,235,.18);color:#bfdbfe;margin-bottom:5px;">
            ▣ &nbsp; Project Registration
          </div>

          <div style="padding:.48rem .6rem;color:#cbd5e1;margin-bottom:5px;">
            ⌕ &nbsp; Code Impact Analysis
          </div>

          <div style="padding:.48rem .6rem;color:#cbd5e1;margin-bottom:5px;">
            ⌁ &nbsp; Test Execution
          </div>

          <div style="padding:.48rem .6rem;color:#cbd5e1;margin-bottom:5px;">
            ◈ &nbsp; Risk & Dependencies
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # WORKSPACE MENU
    st.markdown("---")
    st.markdown("### WORKSPACE MENU")

    if st.button(
        "📁 Saved Projects",
        key="sidebar_saved_projects",
        use_container_width=True
    ):
        st.session_state.show_saved_projects = True
        st.rerun()

    if st.button(
        "🏠 Main Workspace",
        key="sidebar_main_workspace",
        use_container_width=True
    ):
        st.session_state.show_saved_projects = False
        st.rerun()

    # ANALYSIS PIPELINE
    st.markdown(
        """
        <div style="margin-top:1.3rem;padding:.8rem;border:1px solid rgba(96,165,250,.2);border-radius:9px;background:rgba(15,35,58,.65);">

          <div style="font-size:.68rem;color:#93c5fd;font-weight:700;letter-spacing:.08em;">
            ANALYSIS PIPELINE
          </div>

          <div style="font-size:.78rem;color:#cbd5e1;line-height:1.8;margin-top:.4rem;">
            01 &nbsp; Project discovery<br>
            02 &nbsp; Code comparison<br>
            03 &nbsp; Impact mapping<br>
            04 &nbsp; Test generation<br>
            05 &nbsp; Remote execution<br>
            06 &nbsp; Risk assessment
          </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    st.caption("ImpactMap AI · Developer build")

st.divider()

# --------------------------------------------------
# PROJECT REGISTRATION
# --------------------------------------------------

st.markdown('<div id="project-registration"></div>', unsafe_allow_html=True)
st.header("Register New Project")

st.subheader("Upload an External C++ Project")

uploaded_zip = st.file_uploader(
    "Upload C++ Project ZIP (optional)",
    type=["zip"],
    help="Upload a ZIP file containing your C++ project. Maximum size: 100 MB."
)

st.caption(
    "You can upload a ZIP file or enter an existing project folder path below."
)

with st.form("project_form"):

    project_name = st.text_input("Project Name")

    project_description = st.text_area(
        "Project Description"
    )

    project_path = st.text_input(
        "Project Folder Path",
        help="Required only when you are not uploading a ZIP file."
    )

    programming_language = st.selectbox(
        "Programming Language",
        ["C++", "Python", "Java", "JavaScript", "Other"]
    )

    submitted = st.form_submit_button("Register Project")

    if submitted:

        if not project_name.strip():

            st.error("Please enter a project name.")

        elif uploaded_zip is None and not project_path.strip():

            st.error(
                "Please upload a ZIP file or enter the project folder path."
            )

        elif uploaded_zip is not None and programming_language != "C++":

            st.error(
                "ZIP upload currently supports C++ projects only. "
                "Please select C++."
            )

        else:

            try:

                if uploaded_zip is not None:

                    with st.spinner("Extracting C++ project ZIP..."):

                        extraction_result = extract_cpp_project_zip(
                            uploaded_zip,
                            BASE_DIR / "uploaded_projects"
                        )

                    project_path_to_save = extraction_result["project_path"]

                else:

                    project_path_to_save = project_path.strip()

                project_id = create_project(
                    project_name.strip(),
                    project_description,
                    project_path_to_save,
                    programming_language
                )

                st.success(
                    f"Project registered successfully! ID: {project_id}"
                )

                if uploaded_zip is not None:

                    st.success("External C++ ZIP project extracted successfully.")

                    st.write(
                        "Extracted files:",
                        extraction_result["file_count"]
                    )

                    st.write(
                        "C++ files discovered:",
                        extraction_result["cpp_file_count"]
                    )

                    st.write("Discovered C++ files:")

                    for cpp_file in extraction_result["cpp_files"]:
                        st.write(f"- {cpp_file}")

                st.info(
                    "Your project is now registered. "
                    "You can select it in Code Impact Analysis."
                )

            except Exception as error:

                st.error(
                    f"Error registering project: {error}"
                )


# --------------------------------------------------
# REGISTERED PROJECTS
# --------------------------------------------------


# --------------------------------------------------
# REGISTERED PROJECTS
# --------------------------------------------------

st.markdown(
    '<div id="registered-projects"></div>',
    unsafe_allow_html=True
)

st.header("Registered Projects")

try:
    projects = get_active_projects()

    if projects:
        st.write(f"Total Active Projects: {len(projects)}")

        for project in projects:

            col_project, col_hide = st.columns([0.90, 0.10])

            with col_project:
                with st.expander(project["project_name"]):

                    st.write(
                        "**Description:**",
                        project["project_description"] or "N/A"
                    )

                    st.write(
                        "**Programming Language:**",
                        project["programming_language"] or "N/A"
                    )

                    st.write(
                        "**Project Path:**",
                        project["project_path"] or "N/A"
                    )

                    st.write("**Project ID:**", project["id"])

            with col_hide:
                if st.button(
                    "×",
                    key=f"hide_project_{project['id']}",
                    help="Hide this project from the main list"
                ):
                    hide_project(project["id"])
                    st.toast(
                        f"{project['project_name']} moved to Saved Projects"
                    )
                    st.rerun()

    else:
        st.info("No active projects available.")

except Exception as error:
    st.error(f"Unable to load active projects: {error}")
    projects = []



# --------------------------------------------------
# SAVED PROJECTS
# --------------------------------------------------

if st.session_state.show_saved_projects:

    st.divider()
    st.header("📁 Saved Projects")

    st.write(
        "Projects hidden from the main workspace are available here."
    )

    if st.button("← Back to Main Workspace", key="back_to_workspace"):
        st.session_state.show_saved_projects = False
        st.rerun()

    hidden_projects = get_hidden_projects()

    st.write(f"**Total Saved Projects: {len(hidden_projects)}**")

    if hidden_projects:

        for project in hidden_projects:

            with st.container(border=True):

                col1, col2 = st.columns([4, 1])

                with col1:
                    st.subheader(project["project_name"])

                    st.caption(
                        project.get("project_description", "")
                    )

                    st.write(
                        "Language:",
                        project.get("programming_language", "Not specified")
                    )

                    st.caption(
                        "Project Path: "
                        + str(project.get("project_path", "Not available"))
                    )

                with col2:
                    if st.button(
                        "Restore",
                        key=f"restore_project_{project['id']}",
                        use_container_width=True
                    ):
                        restore_project(project["id"])

                        st.success(
                            f"{project['project_name']} restored successfully!"
                        )

                        st.rerun()

    else:
        st.info(
            "No hidden projects found. "
            "Click × beside a project in the main workspace to save it here."
        )


st.divider()


# --------------------------------------------------
# CODE IMPACT ANALYSIS
# --------------------------------------------------

st.markdown('<div id="code-impact-analysis"></div>', unsafe_allow_html=True)
st.header("🔬 Code Impact Analysis")

st.write(
    "Select a registered C++ project, enter the function "
    "you want to modify, and compare the original and proposed code."
)

cpp_projects = [
    project for project in projects
    if (project["programming_language"] or "").strip().lower() == "c++"
    and project["project_path"]
]


if cpp_projects:

    selected_project = st.selectbox(
        "Select C++ Project",
        cpp_projects,
        format_func=lambda project: project["project_name"]
    )


    selected_source_file = None
    changed_function = ""
    detected_project_root = None

    project_path_for_scan = resolve_project_path(
        selected_project["project_path"]
    )

    if not project_path_for_scan or not os.path.isdir(
        project_path_for_scan
    ):

        st.error(
            "The selected project folder does not exist. "
            "Please check the registered project path."
        )

    else:

        st.subheader("Project Source Discovery")

        if st.button("🔄 Refresh Project Scan"):

            get_project_scan.clear()

        try:

            # STEP 1: AUTOMATIC PROJECT STRUCTURE DETECTION

            with st.spinner("Detecting project structure..."):
                project_structure = detect_cpp_project_structure(
                    project_path_for_scan
                )

            detected_project_root = os.path.realpath(
                project_structure["project_root"]
            )

            if not os.path.isdir(detected_project_root):
                raise FileNotFoundError(
                    "The detected C++ project root does not exist: "
                    f"{detected_project_root}"
                )

            st.success("Project structure detected successfully!")
            st.write(
                "**Detected Project Root:**",
                detected_project_root               
            )

            metric1, metric2, metric3, metric4 = st.columns(4)
            metric1.metric("Total Files", project_structure["total_files"])
            metric2.metric("Source Files", len(project_structure["source_files"]))
            metric3.metric("Header Files", len(project_structure["header_files"]))
            metric4.metric("Test Files", len(project_structure["test_files"]))

            st.write(
                "**Build System:**",
                ", ".join(project_structure["build_systems"])
            )
            st.write(
                "**Entry Points:**",
                ", ".join(project_structure["entry_points"])
                if project_structure["entry_points"] else "Not detected"
            )

            with st.expander("View Complete Detected Project Structure"):

                st.markdown("**Source Files**")
                st.code(
                "\n".join(project_structure["source_files"])
                or "None detected"
                )

                st.markdown("**Header Files**")
                st.code(
                    "\n".join(project_structure["header_files"])
                    or "None detected"
                )

                st.markdown("**Test Files**")
                st.code(
                    "\n".join(project_structure["test_files"])
                    or "None detected"
                )

                st.markdown("**Source Directories**")
                st.code(
                    "\n".join(project_structure["source_directories"])
                    or "None detected"
                )

                st.markdown("**Include Directories**")
                st.code(
                    "\n".join(project_structure["include_directories"])
                    or "None detected"
                )

                st.markdown("**Test Directories**")
                st.code(
                    "\n".join(project_structure["test_directories"])
                    or "None detected"
                )

                st.markdown("**Build Configuration Files**")
                st.code(
                    "\n".join(project_structure["build_files"])
                    or "None detected"
                )

            # STEP 2: EXISTING MCP PROJECT SCANNING
            with st.spinner(
                "Scanning project files and discovering functions..."
            ):

                project_scan = get_project_scan(
                    detected_project_root
                )

            source_files = sorted({
                file.replace("\\", "/")
                for file in project_scan.get("files", [])
                if file.lower().endswith(
                    (".cpp", ".cc", ".cxx")
                )
            })

            if not source_files:

                st.warning(
                    "No C++ source files were found in this project."
                )

            else:

                selected_source_file = st.selectbox(
                    "Select Source File",
                    source_files,
                    key=f"selected_source_file_{selected_project['id']}"
                )

                normalized_selected_file = (
                    selected_source_file.replace("\\", "/").lower()
                )

                class_names = {
                    item["name"]
                    for item in project_scan.get("classes", [])
                }

                available_functions = sorted({
                    item["name"]
                    for item in project_scan.get("functions", [])
                    if (
                        item["file"].replace("\\", "/").lower()
                        == normalized_selected_file
                        and item["name"] not in class_names
                    )
                })

                if available_functions:

                    changed_function = st.selectbox(
                        "Select Function to Modify",
                        available_functions,
                        key=(
                            f"selected_changed_function_{selected_project['id']}_"
                            f"{normalized_selected_file}"
                        )
                    )

                else:

                    st.warning(
                        "No function definitions were detected "
                        "in the selected source file."
                    )
                    
        except Exception as error:
                st.error(f"Project scanning failed: {error}")
                st.exception(error)


    # --------------------------------------------------
    # ORIGINAL AND MODIFIED CODE INPUT
    # --------------------------------------------------

    st.subheader("🔄 Proposed Code Change")

    col1, col2 = st.columns(2)

    with col1:

        original_code = st.text_area(
            "📝 Original Code",
            placeholder="Paste existing C++ function here...",
            height=220,
            key=(
                f"original_code_{selected_project['id']}_"
                f"{selected_source_file}_{changed_function}"
            )
        )

    with col2:

        modified_code = st.text_area(
            "✨ Modified Code",
            placeholder="Paste proposed C++ function here...",
            height=220,
            key=(
                f"modified_code_{selected_project['id']}_"
                f"{selected_source_file}_{changed_function}"
            )
        )

    business_requirements = st.text_area(
        "📋 Business Requirements for Generated Tests",
        placeholder=(
            "Example: HRA = 20%, DA = 10%. Total salary = "
            "basic salary + HRA + DA + bonus."
        ),
        height=90,
        help=(
            "For the first version, enter explicit HRA and DA percentages. "
            "Expected results are generated from these requirements, not guessed."
        )
    )

    # --------------------------------------------------
    # --------------------------------------------------
    # UNIFIED ANALYSIS BUTTON
    # --------------------------------------------------

    if st.button("🚀 Analyze Code Impact", type="primary"):

        project_path = detected_project_root

        if not project_path or not os.path.isdir(project_path):

            st.error(
                "The selected project folder does not exist. "
                "Please check the registered project path."
            )

        elif not selected_source_file:

            st.warning("Please select a C++ source file.")

        elif not changed_function:

            st.warning("Please select a function.")

        elif not original_code.strip():

            st.warning("Please enter the original code.")

        elif not modified_code.strip():

            st.warning("Please enter the modified code.")

        else:

            try:

                # --------------------------------------------------
                # STEP 1: CODE COMPARISON
                # --------------------------------------------------

                with st.spinner("Comparing original and modified code..."):

                    comparison = compare_code(
                        original_code,
                        modified_code
                    )

                    generated_test_suite = generate_cpp_test_suite(
                        original_code=original_code,
                        modified_code=modified_code,
                        function_name=changed_function.strip(),
                        requirements=business_requirements,
                        project_path=project_path
                    )

                st.success("Code comparison completed!")

                st.divider()

                st.subheader("📊 Code Comparison Summary")

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Added Lines",
                    comparison["added_count"]
                )

                col2.metric(
                    "Removed Lines",
                    comparison["removed_count"]
                )

                col3.metric(
                    "Total Changed Lines",
                    comparison["added_count"]
                    + comparison["removed_count"]
                )

                st.info(comparison["change_summary"])

                # --------------------------------------------------
                # FUNCTION SIGNATURE ANALYSIS
                # --------------------------------------------------

                st.subheader("🔧 Function Signature Analysis")

                if comparison["signature_changed"]:

                    st.warning("Function signature changes detected.")

                else:

                    st.success("No function signature changes detected.")

                # --------------------------------------------------
                # RETURN STATEMENT ANALYSIS
                # --------------------------------------------------

                st.subheader("↩️ Return Statement Analysis")

                if comparison["return_changed"]:

                    st.warning("Return statement changes detected.")

                else:

                    st.success("No return statement changes detected.")

                # --------------------------------------------------
                # ADDED LINES
                # --------------------------------------------------

                with st.expander("🟢 Added Lines"):

                    if comparison["added_lines"]:

                        st.code(
                            "\n".join(comparison["added_lines"]),
                            language="cpp"
                        )

                    else:

                        st.info("No added lines.")

                # --------------------------------------------------
                # REMOVED LINES
                # --------------------------------------------------

                with st.expander("🔴 Removed Lines"):

                    if comparison["removed_lines"]:

                        st.code(
                            "\n".join(comparison["removed_lines"]),
                            language="cpp"
                        )

                    else:

                        st.info("No removed lines.")

                # --------------------------------------------------
                # DETAILED CODE DIFFERENCE
                # --------------------------------------------------

                with st.expander("📋 Detailed Code Difference"):

                    if comparison["unified_diff"]:

                        st.code(
                            "\n".join(comparison["unified_diff"]),
                            language="diff"
                        )

                    else:

                        st.info("No differences found.")

                # --------------------------------------------------
                # AUTOMATIC TEST CASE GENERATION
                # --------------------------------------------------

                st.subheader("🧪 Automatic Test Case Generation")

                if generated_test_suite["supported"]:

                    st.success(
                        f"Generated {len(generated_test_suite['test_cases'])} "
                        "requirement-based C++ test cases."
                    )

                    # Display salary rules only for salary-based generators.
                    if (
                        "hra_percentage" in generated_test_suite
                        and "da_percentage" in generated_test_suite
                    ):
                        st.write(
                            "**Parsed business rules:** "
                            f"HRA = {generated_test_suite['hra_percentage']:g}%, "
                            f"DA = {generated_test_suite['da_percentage']:g}%"
                        )

                    with st.expander("Preview Generated C++ Tests"):
                        st.code(
                            generated_test_suite["code"],
                            language="cpp"
                        )

                    st.write("**Generated test scenarios:**")

                    for case in generated_test_suite["test_cases"]:

                        if "employee_id" in case:
                            st.write(
                                f"- {case['name']}: employee ID "
                                f"{case['employee_id']}, expected result "
                                f"{case['expected']}"
                            )

                        elif (
                            "basic_salary" in case
                            and "bonus" in case
                        ):
                            st.write(
                                f"- {case['name']}: basic salary "
                                f"{case['basic_salary']:g}, bonus "
                                f"{case['bonus']:g}, expected result "
                                f"{case['expected']:g}"
                            )

                        else:
                            st.write(
                                f"- {case['name']}: expected result "
                                f"{case.get('expected', 'N/A')}"
                            )

                    if generated_test_suite.get("baseline_comparisons"):

                        st.write("**Original behavior reference:**")

                        for item in generated_test_suite["baseline_comparisons"]:

                            status = (
                                "behavior differs from the new requirement"
                                if item["behavior_differs"]
                                else "matches the new requirement"
                            )

                            st.write(
                                f"- {item['name']}: original reference "
                                f"{item['original_reference']:g}; new expected "
                                f"{item['requirement_expected']:g} ({status})"
                            )

                    st.caption(
                        "Generated tests are based on the supplied business "
                        "requirements and the detected C++ function."
                    )

                else:

                    st.warning(
                        generated_test_suite.get(
                            "reason",
                            "Test generation is not supported for this function."
                        )
                    )

                # --------------------------------------------------
                # STEP 2: MCP CODE IMPACT ANALYSIS
                # --------------------------------------------------

                with st.spinner(
                    "Connecting to MCP Server and analyzing dependencies..."
                ):

                    mcp_response = analyze_code_impact_via_mcp(
                        project_path,
                        changed_function.strip(),
                        source_file=selected_source_file
                    )

                    result = mcp_response["analysis"]

                st.success("MCP code impact analysis completed!")

                # --------------------------------------------------
                # STEP 3: GITHUB ACTIONS C++ TEST EXECUTION
                # --------------------------------------------------

                st.divider()

                st.markdown('<div id="test-runs"></div>', unsafe_allow_html=True)
                st.subheader("🧪 GitHub Actions C++ Test Execution")

                st.info(
                    "The proposed code will be compiled and tested "
                    "on a GitHub-hosted Linux runner. "
                    "No local Windows executable will be launched."
                )

                test_result = {
                    "status": "ERROR",
                    "message": "C++ test configuration could not be prepared.",
                    "run_url": None
                }

                try:

                    # --------------------------------------------------
                    # PROJECT AND REPOSITORY PATHS
                    # --------------------------------------------------

                    project_root = os.path.realpath(project_path)

                    repository_root = os.path.realpath(
                        os.path.dirname(os.path.abspath(__file__))
                    )

                    def is_inside_directory(path, directory):

                        try:

                            return (
                                os.path.normcase(
                                    os.path.commonpath([path, directory])
                                )
                                == os.path.normcase(directory)
                            )

                        except ValueError:

                            return False

                    # External ZIP projects are stored inside uploaded_projects,
                    # which itself is located inside the repository.
                    uploaded_projects_root = os.path.realpath(
                        os.path.join(repository_root, "uploaded_projects")
                    )

                    is_uploaded_project = is_inside_directory(
                        project_root,
                        uploaded_projects_root
                    )

                    # External ZIP projects must always use the external GitHub runner.
                    if is_uploaded_project or not is_inside_directory(
                        project_root,
                        repository_root
                    ):

                        def resolve_external_file(file_path):
                            if not file_path:
                                return None
                            raw = str(file_path).strip()
                            candidate = (
                                os.path.realpath(raw)
                                if os.path.isabs(raw)
                                else os.path.realpath(os.path.join(project_root, raw))
                            )
                            if (
                                is_inside_directory(candidate, project_root)
                                and os.path.isfile(candidate)
                            ):
                                return candidate
                            return None

                        external_source = resolve_external_file(selected_source_file)
                        if not external_source or not external_source.lower().endswith((".cpp", ".cc", ".cxx")):
                            raise ValueError("Selected source file could not be resolved inside the external project.")

                        external_tests = []
                        for item in result.get("test_files", []) or []:
                            candidate = resolve_external_file(item)
                            if candidate and candidate.lower().endswith((".cpp", ".cc", ".cxx")):
                                external_tests.append(candidate)
                        external_tests = list(dict.fromkeys(external_tests))

                        external_include = next(
                            (
                                directory for directory in (
                                    os.path.join(project_root, "include"),
                                    os.path.join(project_root, "inc"),
                                    project_root
                                )
                                if os.path.isdir(directory)
                            ),
                            project_root
                        )

                        st.write("**Selected Project:**", selected_project["project_name"])
                        st.write("**External Source File:**", os.path.relpath(external_source, project_root).replace("\\", "/"))
                        st.write("**Existing Test Files:**", len(external_tests))


                        # Preserve the rest of the selected source file when the editor
                        # contains only the changed function rather than the complete file.

                        source_text = Path(external_source).read_text(encoding="utf-8")

                        original_fragment = (original_code or "").strip()
                        modified_fragment = (modified_code or "").strip()

                        # Case 1: No actual code change.
                        # Use the existing source file and continue running generated tests.
                        if original_fragment == modified_fragment:
                            external_proposed_code = source_text

                        # Case 2: Original function exists exactly in the source file.
                        elif original_fragment and original_fragment in source_text:
                            external_proposed_code = source_text.replace(
                                original_fragment,
                                modified_code,
                                1
                            )

                        # Case 3: User supplied a complete source file.
                        elif modified_fragment.startswith(("#include", "//", "/*")):
                            external_proposed_code = modified_code

                        # Case 4: Cannot safely identify the function to replace.
                        else:
                            raise ValueError(
                                "Could not safely locate the original function code "
                                "inside the selected source file. "
                                "Please verify the selected source file and original function."
                            )


                        with st.spinner("Uploading external project and running GitHub Actions tests..."):
                            test_result = run_external_cpp_tests(
                                project_root=project_root,
                                proposed_code=external_proposed_code,
                                source_file=external_source,
                                test_files=external_tests,
                                include_dir=external_include,
                                project_name=selected_project["project_name"],
                                generated_test_code=(
                                    generated_test_suite["code"]
                                    if generated_test_suite["supported"]
                                    else ""
                                )
                            )

                    else:
                        # --------------------------------------------------
                        # RESOLVE MCP FILE PATHS
                        # --------------------------------------------------

                        def resolve_project_file(file_path):

                            if not file_path:
                                return None

                            file_path = str(file_path).strip()

                            if not file_path:
                                return None

                            if os.path.isabs(file_path):

                                candidates = [
                                    os.path.realpath(file_path)
                                ]

                            else:

                                candidates = [
                                    os.path.realpath(
                                        os.path.join(project_root, file_path)
                                    ),
                                    os.path.realpath(
                                        os.path.join(repository_root, file_path)
                                    )
                                ]

                            for candidate in candidates:

                                if (
                                    is_inside_directory(
                                        candidate,
                                        project_root
                                    )
                                    and os.path.isfile(candidate)
                                ):

                                    return candidate

                            return None

                        # --------------------------------------------------
                        # USE THE USER-SELECTED SOURCE FILE
                        # --------------------------------------------------

                        source_file = resolve_project_file(
                            selected_source_file
                        )

                        if (
                            not source_file
                            or not source_file.lower().endswith(
                                (".cpp", ".cc", ".cxx")
                            )
                        ):

                            raise ValueError(
                                "The selected C++ source file could not "
                                "be resolved inside the project."
                            )

                        if not source_file:

                            raise ValueError(
                                "No valid C++ source definition file was found. "
                                "Please check MCP definition_files."
                            )

                        # --------------------------------------------------
                        # FIND RELATED TEST FILES
                        # --------------------------------------------------

                        resolved_test_files = []

                        related_test_files = result.get(
                            "test_files",
                            []
                        )

                        if isinstance(related_test_files, str):

                            related_test_files = [
                                related_test_files
                            ]

                        for test_file in related_test_files:

                            candidate = resolve_project_file(test_file)

                            if (
                                candidate
                                and candidate.lower().endswith(
                                    (".cpp", ".cc", ".cxx")
                                )
                            ):

                                resolved_test_files.append(candidate)

                        # Remove duplicate test paths.
                        resolved_test_files = list(
                            dict.fromkeys(resolved_test_files)
                        )

                        if not resolved_test_files:

                            raise ValueError(
                                "No valid C++ test files were found. "
                                "Please check MCP test_files."
                            )

                        # --------------------------------------------------
                        # FIND INCLUDE DIRECTORY
                        # --------------------------------------------------

                        detected_include_dirs = (
                            project_structure.get("include_directories", [])
                        )

                        possible_include_dirs = []

                        for include_path in detected_include_dirs:
                            include_path = str(include_path).strip()

                            if not include_path:
                                continue

                            if os.path.isabs(include_path):
                                candidate_include_dir = os.path.realpath(
                                    include_path
                                )
                            else:
                                candidate_include_dir = os.path.realpath(
                                    os.path.join(project_root, include_path)
                                )

                            if (
                                is_inside_directory(
                                    candidate_include_dir,
                                    project_root
                                )
                                and os.path.isdir(candidate_include_dir)
                            ):
                                possible_include_dirs.append(
                                    candidate_include_dir
                                )

                        possible_include_dirs.extend([
                            os.path.join(project_root, "include"),
                            os.path.join(project_root, "inc"),
                            project_root
                        ])

                        # Keep only unique, existing directories inside the project.
                        possible_include_dirs = list(dict.fromkeys(
                            os.path.realpath(directory)
                            for directory in possible_include_dirs
                            if (
                                os.path.isdir(directory)
                                and is_inside_directory(
                                    os.path.realpath(directory),
                                    project_root
                                )
                            )
                        ))

                        include_dir = (
                            possible_include_dirs[0]
                            if possible_include_dirs
                            else None
                        )

                        if not include_dir:

                            raise ValueError(
                                "No valid C++ include directory was found."
                            )

                        # CONVERT TO GITHUB REPOSITORY-RELATIVE PATHS
                        # --------------------------------------------------

                        github_source_file = os.path.relpath(
                            source_file,
                            repository_root
                        ).replace("\\", "/")

                        github_test_files = [
                            os.path.relpath(
                                path,
                                repository_root
                            ).replace("\\", "/")
                            for path in resolved_test_files
                        ]

                        github_include_dir = os.path.relpath(
                            include_dir,
                            repository_root
                        ).replace("\\", "/")

                        # --------------------------------------------------
                        # DISPLAY TEST CONFIGURATION
                        # --------------------------------------------------

                        st.write(
                            "**Selected Project:**",
                            selected_project["project_name"]
                        )

                        st.write(
                            "**Changed Function:**",
                            changed_function
                        )

                        st.write(
                            "**Source File:**",
                            github_source_file
                        )

                        st.write(
                            "**Include Directory:**",
                            github_include_dir
                        )

                        st.write("**Related Test Files:**")

                        for test_file in github_test_files:

                            st.write("📄", test_file)

                        # --------------------------------------------------
                        # SUBMIT TO GITHUB ACTIONS
                        # --------------------------------------------------

                        with st.spinner(
                            "Submitting proposed code to GitHub Actions..."
                        ):

                            test_result = run_github_cpp_tests(
                                proposed_code=modified_code,
                                source_file=github_source_file,
                                test_files=github_test_files,
                                include_dir=github_include_dir,
                                project_name=selected_project["project_name"],
                                generated_test_code=(
                                    generated_test_suite["code"]
                                    if generated_test_suite["supported"]
                                    else ""
                                )
                            )

                except Exception as error:

                    test_result = {
                        "status": "ERROR",
                        "message": str(error),
                        "run_url": None
                    }

                # --------------------------------------------------
                # DISPLAY TEST RESULT
                # --------------------------------------------------

                test_status = test_result.get(
                    "status",
                    "ERROR"
                )

                if test_status == "PASSED":

                    st.success(
                        "✅ Proposed C++ code passed GitHub Actions tests!"
                    )

                elif test_status == "FAILED":

                    st.error(
                        "❌ Proposed C++ code failed GitHub Actions tests."
                    )

                elif test_status == "TIMEOUT":

                    st.warning(
                        "⚠️ GitHub Actions execution timed out. "
                        "Check the workflow run."
                    )

                else:

                    st.error(
                        f"GitHub Actions execution status: {test_status}"
                    )

                st.write(
                    "**Remote Test Status:**",
                    test_status
                )

                st.write(
                    "**Details:**",
                    test_result.get(
                        "message",
                        "No details available."
                    )
                )

                if test_result.get("run_url"):

                    st.markdown(
                        f"[🔗 View GitHub Actions Run]"
                        f"({test_result['run_url']})"
                    )

                st.caption(
                    "C++ source and related test files are selected "
                    "dynamically using MCP analysis."
                )

                st.divider()

                # --------------------------------------------------
                # STEP 4: CHANGE RISK ANALYSIS
                # --------------------------------------------------

                # Get individual test suite statuses from GitHub Actions
                existing_test_status = test_result.get(
                    "existing_test_status",
                    test_status
                )

                generated_test_status = test_result.get(
                    "generated_test_status",
                    (
                        "NOT_GENERATED"
                        if not generated_test_suite["supported"]
                        else "UNKNOWN"
                    )
                )

                # Fallback when individual status is unavailable
                if existing_test_status == "UNKNOWN":
                    existing_test_status = test_status

                risk_result = calculate_change_risk(
                    result,
                    comparison,
                    existing_test_status,
                    generated_test_status=generated_test_status,
                    generated_test_count=len(
                        generated_test_suite["test_cases"]
                    )
                )


                # --------------------------------------------------
                # RISK AND TEST METRICS
                # --------------------------------------------------

                col1, col2, col3, col4 = st.columns(4)

                col1.metric(
                    "Risk Score",
                    risk_result["risk_score"]
                )

                col2.metric(
                    "Impacted Files",
                    risk_result["impacted_file_count"]
                )

                col3.metric(
                    "Related Test Files",
                    risk_result["test_file_count"]
                )

                col4.metric(
                    "Test Risk Points",
                    risk_result["test_risk_points"]
                )

                st.write(
                    "**Automated Test Status:**",
                    risk_result["test_status"]
                )

                if risk_result["generated_test_count"] > 0:
                    st.write(
                        "**Generated Test Cases:**",
                        risk_result["generated_test_count"]
                    )
                    st.write(
                        "**Generated Test Execution:**",
                        risk_result["generated_test_status"]
                    )

                st.markdown('<div id="risk-analysis"></div>', unsafe_allow_html=True)

                # --------------------------------------------------
                # RISK LEVEL
                # --------------------------------------------------

                risk_level = risk_result["risk_level"]

                if risk_level == "LOW":

                    st.success("🟢 LOW RISK")

                elif risk_level == "MEDIUM":

                    st.warning("🟡 MEDIUM RISK")

                else:

                    st.error("🔴 HIGH RISK")

                # --------------------------------------------------
                # RISK ANALYSIS REASONS
                # --------------------------------------------------

                st.write("**Risk Analysis Reasons:**")

                for reason in risk_result["reasons"]:

                    st.write("•", reason)

                # --------------------------------------------------
                # RECOMMENDATION
                # --------------------------------------------------

                st.info(
                    "**Recommendation:** "
                    + risk_result["recommendation"]
                )

                st.caption(
                    "Risk is a heuristic estimate based on dependency "
                    "exposure, definition detection, identified test "
                    "files, code changes, existing tests and generated "
                    "requirement-based test results. It does not guarantee "
                    "code safety."
                )

                st.divider()

                # --------------------------------------------------
                # STEP 5: MCP INTEGRATION DETAILS
                # --------------------------------------------------

                with st.expander("🔌 MCP Integration Details"):

                    st.write("**MCP Server:** ImpactMap AI")

                    st.write(
                        "**Executed Tool:** analyze_code_impact"
                    )

                    st.write("**Available MCP Tools:**")

                    for tool in mcp_response["available_tools"]:

                        st.write("✅", tool)

                # --------------------------------------------------
                # STEP 6: IMPACT SUMMARY
                # --------------------------------------------------

                st.subheader("📊 Impact Summary")

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Definition Files",
                    len(result["definition_files"])
                )

                col2.metric(
                    "Impacted Files",
                    len(result["impacted_files"])
                )

                col3.metric(
                    "Related Tests",
                    len(result["test_files"])
                )

                # --------------------------------------------------
                # DEFINITION FILES
                # --------------------------------------------------

                st.subheader("📁 Definition Files")

                if result["definition_files"]:

                    for file in result["definition_files"]:

                        st.write("📄", file)

                else:

                    st.info("No function definition found.")

                # --------------------------------------------------
                # IMPACTED FILES
                # --------------------------------------------------

                st.subheader("🎯 Impacted Files")

                if result["impacted_files"]:

                    for file in result["impacted_files"]:

                        st.write("📄", file)

                else:

                    st.info("No dependent files detected.")

                # --------------------------------------------------
                # RELATED TEST FILES
                # --------------------------------------------------

                st.subheader("🧪 Related Test Files")

                if result["test_files"]:

                    for file in result["test_files"]:

                        st.write("📄", file)

                else:

                    st.info("No related test files detected.")

                # --------------------------------------------------
                # STEP 7: DEPENDENCY GRAPH
                # --------------------------------------------------

                st.subheader("🕸️ Dependency Graph")

                figure = create_dependency_graph(
                    result["dependencies"]
                )

                if figure:

                    st.plotly_chart(
                        figure,
                        use_container_width=True
                    )

                else:

                    st.info("No dependency relationships found.")

                # --------------------------------------------------
                # STEP 8: RAG SEARCH
                # --------------------------------------------------

                st.subheader("📚 Related Code (RAG Search)")

                if result["related_code"]:

                    for item in result["related_code"]:

                        with st.expander(
                            f'{item["file"]} | Similarity: {item["score"]}'
                        ):

                            st.write(
                                "Starting Line:",
                                item["start_line"]
                            )

                            st.code(
                                item["text"],
                                language="cpp"
                            )

                else:

                    st.info("No related code found.")

                # --------------------------------------------------
                # STEP 9: IMPACT EXPLANATION
                # --------------------------------------------------

                st.divider()

                st.subheader("🤖 Impact Explanation")

                st.caption(
                    "Meta Llama 3.2 3B | Local AI Impact Analysis"
                )

                with st.spinner("Generating impact explanation..."):

                    explanation = generate_impact_explanation(result)

                st.markdown(explanation)

                # --------------------------------------------------
                # FINAL RESULT
                # --------------------------------------------------

                st.divider()

                st.success(
                    "🎉 Complete Code Change Analysis Finished!"
                )

            except Exception as error:
                    st.error(f"Impact analysis failed: {error}")
                    st.exception(error)
else:

    st.info(
        "Please register a C++ project with a valid folder path "
        "to use Code Impact Analysis."
    )
