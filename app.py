
import os
import streamlit as st

from services.project_service import (
    create_project,
    get_all_projects
)

from modules.cpp_test_runner import run_cpp_tests
from modules.code_comparator import compare_code
from modules.mcp_client import analyze_code_impact_via_mcp
from modules.dependency_visualizer import create_dependency_graph
from modules.llm_explainer import generate_impact_explanation
from modules.risk_analyzer import calculate_change_risk


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="ImpactMap AI",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 ImpactMap AI")
st.subheader("Intelligent Code Change Impact Analyzer")

st.write(
    "Register your software projects and analyze "
    "the impact of future code changes."
)

st.divider()


# --------------------------------------------------
# PROJECT REGISTRATION
# --------------------------------------------------

st.header("Register New Project")

with st.form("project_form"):

    project_name = st.text_input("Project Name")

    project_description = st.text_area(
        "Project Description"
    )

    project_path = st.text_input(
        "Project Folder Path"
    )

    programming_language = st.selectbox(
        "Programming Language",
        ["C++", "Python", "Java", "JavaScript", "Other"]
    )

    submitted = st.form_submit_button("Register Project")

    if submitted:

        if not project_name.strip():

            st.error("Please enter a project name.")

        elif not project_path.strip():

            st.error("Please enter the project folder path.")

        else:

            try:

                project_id = create_project(
                    project_name,
                    project_description,
                    project_path,
                    programming_language
                )

                st.success(
                    f"Project registered successfully! ID: {project_id}"
                )

            except Exception as error:

                st.error(f"Registration failed: {error}")


st.divider()


# --------------------------------------------------
# REGISTERED PROJECTS
# --------------------------------------------------

st.header("Registered Projects")

try:

    projects = get_all_projects()

    if projects:

        st.write(f"Total Projects: {len(projects)}")

        for project in projects:

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

    else:

        st.info("No projects registered yet.")

except Exception as error:

    st.error(f"Unable to load projects: {error}")
    projects = []


st.divider()


# --------------------------------------------------
# CODE IMPACT ANALYSIS
# --------------------------------------------------

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

    changed_function = st.text_input(
        "Function to Modify",
        placeholder="Example: calculateSalary"
    )


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
            key="original_code"
        )

    with col2:

        modified_code = st.text_area(
            "✨ Modified Code",
            placeholder="Paste proposed C++ function here...",
            height=220,
            key="modified_code"
        )


    # --------------------------------------------------
    # UNIFIED ANALYSIS BUTTON
    # --------------------------------------------------

    if st.button("🚀 Analyze Code Impact", type="primary"):

        project_path = selected_project["project_path"]

        if not os.path.isdir(project_path):

            st.error("The selected project folder does not exist.")

        elif not changed_function.strip():

            st.warning("Please enter a function name.")

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


                st.divider()


                # --------------------------------------------------
                # STEP 2: MCP CODE IMPACT ANALYSIS
                # --------------------------------------------------

                with st.spinner(
                    "Connecting to MCP Server and analyzing dependencies..."
                ):

                    mcp_response = analyze_code_impact_via_mcp(
                        project_path,
                        changed_function.strip()
                    )

                    result = mcp_response["analysis"]

                st.success("MCP code impact analysis completed!")


                # --------------------------------------------------
                # STEP 3: AUTOMATED C++ TEST EXECUTION
                # --------------------------------------------------

                st.divider()

                st.subheader("🧪 Automated C++ Test Execution")

                with st.spinner("Compiling and running C++ tests..."):

                    test_result = run_cpp_tests(project_path)

                test_status = test_result["status"]

                if test_status == "PASSED":

                    st.success(
                        "✅ C++ tests compiled and executed successfully!"
                    )

                elif test_status == "FAILED":

                    st.error(
                        "❌ C++ tests executed but one or more tests failed."
                    )

                elif test_status == "COMPILE_FAILED":

                    st.error("❌ C++ compilation failed.")

                elif test_status == "EXECUTION_BLOCKED":

                    st.warning(
                        "⚠️ Windows Application Control blocked "
                        "C++ test execution."
                    )

                elif test_status == "TIMEOUT":

                    st.warning(
                        "⚠️ C++ test execution timed out."
                    )

                else:

                    st.error(
                        f"C++ test runner error: {test_result.get('message', 'Unknown error')}"
                    )

                st.write("**Test Status:**", test_status)

                st.write(
                    "**Details:**",
                    test_result.get("message", "No details available.")
                )

                if test_result.get("compile_errors"):

                    with st.expander("Compilation Errors"):

                        st.code(
                            test_result["compile_errors"],
                            language="text"
                        )

                if test_result.get("test_output"):

                    with st.expander("Test Output"):

                        st.code(
                            test_result["test_output"],
                            language="text"
                        )

                if test_result.get("test_errors"):

                    with st.expander("Test Execution Errors"):

                        st.code(
                            test_result["test_errors"],
                            language="text"
                        )

                if test_status == "EXECUTION_BLOCKED":

                    st.info(
                        "The test executable could not be launched due "
                        "to Windows security restrictions. The test "
                        "has not been marked as passed."
                    )

                st.divider()


                # --------------------------------------------------
                # STEP 4: CHANGE RISK ANALYSIS
                # --------------------------------------------------

                risk_result = calculate_change_risk(
                    result,
                    comparison,
                    test_status
                )

                st.subheader("📝 Code Change Risk Details")


                # --------------------------------------------------
                # CODE CHANGE METRICS
                # --------------------------------------------------

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Added Lines",
                    risk_result["added_line_count"]
                )

                col2.metric(
                    "Removed Lines",
                    risk_result["removed_line_count"]
                )

                col3.metric(
                    "Total Changed Lines",
                    risk_result["added_line_count"]
                    + risk_result["removed_line_count"]
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
                    "files, code changes and test execution status. "
                    "It does not guarantee code safety."
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
                    "Rule-based Mock LLM Engine | No API credits required"
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


else:

    st.info(
        "Please register a C++ project with a valid folder path "
        "to use Code Impact Analysis."
    )
