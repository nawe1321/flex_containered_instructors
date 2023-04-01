import os
import requests
from dotenv import load_dotenv

load_dotenv()


CANVAS_API_KEY = os.environ.get("ctoken")
COURSEURL = os.environ.get("curl")


def get_courses_without_blueprint():
    courses_without_blueprint = []
    for phase in range(2, 6):
        search_term = f'Phase {phase}'
        url = f'{COURSEURL}/api/v1/accounts/667/courses?with_enrollments=true&published=true&completed=false&blueprint_associated=false&search_term={search_term}&per_page=100'
        headers = {'Authorization': f'Bearer {CANVAS_API_KEY}'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            results = response.json()
            for result in results:
                course = {
                    'name': result['name'],
                    'id': result['id']
                }
                courses_without_blueprint.append(course)
        else:
            response.raise_for_status()
    return courses_without_blueprint


def main():
    courses_without_blueprint = get_courses_without_blueprint()
    for course in courses_without_blueprint:
        print(f"Name: {course['name']}, ID: {course['id']}")


if __name__ == '__main__':
    main()
