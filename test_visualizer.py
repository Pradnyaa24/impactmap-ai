import streamlit as st

from modules.cpp_analyzer import analyze_cpp_project
from modules.dependency_analyzer import build_dependency_map
from modules.dependency_visualizer import create_dependency_graph


project_path = "sample_projects/EmployeeManagementSystem"

results = analyze_cpp_project(project_path)

dependencies = build_dependency_map(results)

st.title("ImpactMap AI - Dependency Visualization")

st.write("Total Dependencies:", len(dependencies))

figure = create_dependency_graph(dependencies)

if figure:
    st.plotly_chart(figure, use_container_width=True)
else:
    st.info("No dependencies found.")