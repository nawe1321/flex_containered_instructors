import os
import requests
from dotenv import load_dotenv

load_dotenv()


CANVAS_API_KEY = os.environ.get("ctoken")
COURSEURL = os.environ.get("curl")


def get_orphaned_courses():
    orphaned_courses = []
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
                orphaned_courses.append(course)
        else:
            response.raise_for_status()
    return orphaned_courses


def main():
    orphaned_courses = get_orphaned_courses()
    for course in orphaned_courses:
        print(f"Name: {course['name']}, ID: {course['id']}")


if __name__ == '__main__':
    main()
