
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
