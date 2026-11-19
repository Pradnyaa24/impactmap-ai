
from config.database import get_connection


def create_project(
    project_name,
    project_description,
    project_path,
    programming_language
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            query = """
                INSERT INTO projects (
                    project_name,
                    project_description,
                    project_path,
                    programming_language
                )
                VALUES (%s, %s, %s, %s)
            """

            cursor.execute(
                query,
                (
                    project_name,
                    project_description,
                    project_path,
                    programming_language
                )
            )

            project_id = cursor.lastrowid

        connection.commit()
        return project_id

    finally:
        connection.close()


# Get only visible projects for the main workspace
def get_active_projects():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT *
                FROM projects
                WHERE is_hidden = 0
                ORDER BY id DESC
            """)

            return cursor.fetchall()

    finally:
        connection.close()


# Get only hidden projects for the Saved Projects section
def get_hidden_projects():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT *
                FROM projects
                WHERE is_hidden = 1
                ORDER BY id DESC
            """)

            return cursor.fetchall()

    finally:
        connection.close()


# Get all projects, including hidden projects
# Kept for compatibility with existing code
def get_all_projects():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM projects ORDER BY id DESC"
            )

            return cursor.fetchall()

    finally:
        connection.close()


# Hide a project without deleting its database record
def hide_project(project_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE projects
                SET is_hidden = 1
                WHERE id = %s
            """, (project_id,))

        connection.commit()
        return True

    finally:
        connection.close()


# Restore a hidden project
def restore_project(project_id):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE projects
                SET is_hidden = 0
                WHERE id = %s
            """, (project_id,))

        connection.commit()
        return True

    finally:
        connection.close()


def update_project_path(project_id, project_path):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            query = """
                UPDATE projects
                SET project_path = %s
                WHERE id = %s
            """

            cursor.execute(query, (project_path, project_id))

        connection.commit()

    finally:
        connection.close()
