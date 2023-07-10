"""
This module automates the process of updating a Google Sheet with student information to provide 
the new instructors to ops based on assignment completion status in Canvas.
Remove the load_dotenv lines 12 and 15 if using local variables, or pulling from the environment.
"""
import os
import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
import requests

load_dotenv()
# Replace with your own API key and domain, if needed. These are env. variables for AWS
CANVAS_API_KEY = os.environ.get("ctoken")
COURSEURL = os.environ.get("curl")
BLUEPRINT_COURSES = [6114, 6127]
SHEET_TAB_NAME = 'Cyber'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
PHASE_INSTRUCTOR_MAPPING = {
    # 'Phase 2 Complete': 'Instructor 2',
    'Phase 3 Complete': {
        'new_instructor': 'Eric Keith',
        'old_instructor': 'Ryan Shulman'
    },
    # 'Phase 4 Complete': 'Instructor 4',
    # 'Phase 5 Complete': 'Instructor 5'
}


def get_sheet_id_by_name(service, spreadsheet_id, sheet_name):
    """
    Get the sheet ID of a Google Sheet by its name.

    Args:
        service (googleapiclient.discovery.Resource): The Google Sheets API service instance.
        spreadsheet_id (str): The ID of the Google Sheet.
        sheet_name (str): The name of the sheet within the Google Sheet.

    Returns:
        int: The sheet ID of the specified sheet name, or None if the sheet is not found.
    """
    sheets_metadata = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id).execute()
    sheets = sheets_metadata.get('sheets', '')

    sheet_id = None
    for sheet in sheets:
        if sheet['properties']['title'] == sheet_name:
            sheet_id = sheet['properties']['sheetId']
            break

    if sheet_id is None:
        print(f"Error: Could not find a sheet with the name '{sheet_name}'")

    return sheet_id


def get_associated_courses(course_id):
    """
    Retrieves the associated courses for a given Blueprint course ID from the Canvas API.

    Parameters:
    course_id (int): The ID of the course for which to fetch associated courses.

    Returns:
    list: A list of associated courses as JSON objects.
    """
    url = f'{COURSEURL}/api/v1/courses/{course_id}/blueprint_templates/default/associated_courses'
    headers = {'Authorization': f'Bearer {CANVAS_API_KEY}'}
    # Add this line to retrieve the first 200 courses
    params = {'per_page': 200}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    return response.json()


def get_students_with_assignment(course_id, assignment_name, score, days):
    """
    Get a list of students who meet the specified assignment criteria in a given course.

    Args:
        course_id (int): The ID of the course to search for students.
        assignment_name (str): The name of the assignment to filter students by.
        score (int): The target score of the assignment to filter students by.
        days (int): The number of days in the past to consider when filtering 
        by assignment submission date.

    Returns:
        list: A list of dictionaries containing student information who 
        meet the specified criteria. Each dictionary includes 
        student id, name, sortable_name, email, sis_user_id, and assignment_name.
    """
    url = f'{COURSEURL}/api/v1/courses/{course_id}/users'
    params = {'enrollment_type[]': 'student', 'per_page': 100}
    headers = {'Authorization': f'Bearer {CANVAS_API_KEY}'}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    students = response.json()

    url = f'{COURSEURL}/api/v1/courses/{course_id}/assignments'
    # Add this line to retrieve the first 200 assignments
    params = {'per_page': 200}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    assignments = response.json()

    # Print all assignments to inspect the results
    # print(f"Course ID: {course_id}, All Assignments:")
    # for a in assignments:
    # print(f"  - {a['name']} (ID: {a['id']})")

    target_assignment = next(
        (a for a in assignments if a['name'] == assignment_name), None)

    if not target_assignment:
        # print(f"Course ID: {course_id}, '{assignment_name}' not found")
        return []

    target_assignment_id = target_assignment['id']
    # print(f"Course ID: {course_id}, Assign. ID for '{assignment_name}': {target_assignment_id}")

    since_date = (datetime.datetime.now() -
                  datetime.timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S')

    qualified_students = []
    for student in students:
        url = (
            f'{COURSEURL}/api/v1/courses/{course_id}/assignments/'
            f'{target_assignment_id}/submissions/{student["id"]}'
        )

        params = {'include': ['submission_history']}
        response = requests.get(url, headers=headers,
                                params=params, timeout=10)
        submission = response.json()

        if submission['score'] == score and submission['graded_at'] >= since_date:
            phase_name = assignment_name
            new_instructor_name = PHASE_INSTRUCTOR_MAPPING[phase_name].get(
                'new_instructor', 'Unknown Instructor')
            qualified_students.append({
                'id': student['id'],
                'name': student['name'],
                'sortable_name': student['sortable_name'],
                'email': student.get('email', 'No email'),
                'sis_user_id': student['sis_user_id'],
                'assignment_name': assignment_name,
                'new_instructor_name': new_instructor_name,
                'new_instructor_uuid_formula': (
                    f'=VLOOKUP("{new_instructor_name}", '
                    f'\'Instructor Roster\'!A:B, 2, FALSE)'
                )
            })
    return qualified_students


def append_to_google_sheet(data, creds):
    """
    Append non-duplicate student data to a specified Google Sheet, 
    based on student UUID matched with new instructor name.

    Args:
        data (list): A list of dictionaries containing student information to append.
        Each dictionary includes student id, name, sortable_name, email, sis_user_id, 
        and assignment_name.
        creds (google.oauth2.credentials.Credentials): The user's Google API credentials.

    Returns:
        None
    """

    service = build('sheets', 'v4', credentials=creds)
    spreadsheet_id = '1-SrzwExIqVDfrQRu1s-uruRJwatifFQQI6feZu6-das'
    sheet_id = get_sheet_id_by_name(service, spreadsheet_id, SHEET_TAB_NAME)

   # Step 1: Retrieve the existing data from the Google Sheet
    # Assuming 'sis_user_id' is in column C and 'new_instructor_name' is in column E
    range_name = f'{SHEET_TAB_NAME}!A2:F'
    # pylint: disable=maybe-no-member
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=range_name).execute()
    existing_data = result.get('values', [])

    # Step 2: Extract the 'sis_user_id' and 'new_instructor_name' column data
    existing_students = [
        {
            'sis_user_id': row[2],
            'new_instructor_name': row[4]
        } for row in existing_data if len(row) > 5

    ] if existing_data else []
    values = []

    # Step 3: Check for duplicates between the new data and the existing data
    for student in data:
        # print(student)
        # print(existing_students)
        # Check if the student is already in the sheet with the same new instructor name
        is_duplicate = any(
            existing_student['sis_user_id'] == student['sis_user_id']
            and existing_student['new_instructor_name'] == student['new_instructor_name']
            for existing_student in existing_students
        )
        print(is_duplicate)
        if not is_duplicate:
            # Get the instructor name based on the assignment name
            phase_name = student['assignment_name']
            instructor_names = PHASE_INSTRUCTOR_MAPPING.get(phase_name, {})
            new_instructor_name = instructor_names.get(
                'new_instructor', 'Unknown Instructor')
            old_instructor_name = instructor_names.get(
                'old_instructor', 'Unknown Instructor')
            new_instructor_uuid_formula = (
                f'=IFERROR(VLOOKUP("{new_instructor_name}",'
                f' \'Instructor Roster\'!A:B, 2, FALSE), "not found")'
            )
            old_instructor_uuid_formula = (
                f'==IFERROR(VLOOKUP("{old_instructor_name}", '
                f'\'Instructor Roster\'!A:B, 2, FALSE), "not found")'
            )
            row = [
                datetime.datetime.now().strftime('%Y-%m-%d'),  # Week of
                student['name'],  # Full name
                student['sis_user_id'],  # sis_user_id
                student['email'],  # Email address
                student['new_instructor_name'] #new instructor name
                ]

            values.append(row)

    if not values:
        print("No new data to add.")
        return

    body = {
        'requests': [
            {
                'insertRange': {
                    'range': {
                        'sheetId': sheet_id,  # set by variable at top of script
                        'startRowIndex': 1,
                        'endRowIndex': 1 + len(values)
                    },
                    'shiftDimension': 'ROWS'
                }
            },
            {
                'updateCells': {
                    'range': {
                        'sheetId': sheet_id,  # set by variable at top of script
                        'startRowIndex': 1,
                        'endRowIndex': 1 + len(values),
                        'startColumnIndex': 0,
                        # increase end column index by 1
                        'endColumnIndex': 1 + len(values[0]) + 1
                    },
                    'rows': [
                        {
                            'values': [
                                {'userEnteredValue': {'stringValue': str(cell)}} for cell in row
                            ] + [
                                {
                                    'userEnteredValue': {
                                        'formulaValue': (old_instructor_uuid_formula)
                                    }
                                },
                                {
                                    'userEnteredValue': {
                                        'formulaValue': (new_instructor_uuid_formula)
                                    }
                                }
                            ]
                        } for row in values
                    ],
                    'fields': 'userEnteredValue'
                }
            }
        ]
    }

    # print(values)
    # Step 4: Add only the non-duplicate data to the Google Sheet
    # pylint: disable=maybe-no-member
    result = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body).execute()

    updated_rows = len(values)
    print(f'{updated_rows} rows updated.')


def main():
    """
    Entry point for the script to retrieve and process student data from Canvas 
    and append it to a Google Sheet.

    This function:
        1. Authenticates the user with the Google API and refreshes the access token if necessary.
        2. Loops through blueprint courses and their associated courses.
        3. Retrieves students who completed a specific assignment with a specified score 
        within a given number of days.
        4. Updates the instructor name for each student based on the phase of the course.
        5. Appends the non-duplicate student data to the specified Google Sheet.

    Returns:
        None
    """

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w', encoding='utf-8') as token:
            token.write(creds.to_json())
    all_students = []
    for blueprint_course in BLUEPRINT_COURSES:
        # print(f"Processing blueprint course: {blueprint_course}")
        associated_courses = get_associated_courses(blueprint_course)
        for course in associated_courses:
            # print(f"Processing course ID: {course['id']}")
            for phase_name, instructor_mapping in PHASE_INSTRUCTOR_MAPPING.items():
                new_instructor_name = instructor_mapping['new_instructor']
                old_instructor_name = instructor_mapping['old_instructor']
                students = get_students_with_assignment(
                    course['id'], phase_name, 1, 7)
                for student in students:
                    student["new_instructor_name"] = new_instructor_name
                    student["old_instructor_name"] = old_instructor_name
                all_students.extend(students)

    append_to_google_sheet(all_students, creds)


if __name__ == '__main__':
    main()
