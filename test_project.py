
from services.project_service import (
    create_project,
    get_all_projects
)

project_id = create_project(
    project_name="ImpactMap AI Demo",
    project_description="AI-based code change impact analysis system",
    project_path="sample_projects",
    programming_language="Python"
)

print("Project registered successfully!")
print("Project ID:", project_id)

projects = get_all_projects()

print("\nRegistered Projects:")

for project in projects:
    print(project)
