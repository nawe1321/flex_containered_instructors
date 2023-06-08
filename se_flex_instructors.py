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
BLUEPRINT_COURSES = [3299, 4182, 6667, 5935, 6130, 6343, 3309]
SHEET_TAB_NAME = 'SE'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
PHASE_INSTRUCTOR_MAPPING = {
    '[Flex] Student Survey for Phase 1': {
        # determined in array in main() 'new_instructor': 'Nancy Noyes'
    },
    '[Flex] Student Survey for Phase 2': {
        'new_instructor': 'Nancy Noyes' if 3299 in BLUEPRINT_COURSES 
        else 'Aastha Saxena' if 5935 in BLUEPRINT_COURSES
        else 'unknown instructor'
    },
    '[Flex] Student Survey for Phase 3': {
        'new_instructor': 'Enoch Griffith' if 6130 in BLUEPRINT_COURSES 
        else 'Benjamin Aschenbrenner' if 4182 in BLUEPRINT_COURSES
        else 'unknown instructor'
    },
    '[Flex] Student Survey for Phase 4': {
        # determined in array in main() 'new_instructor': 'Instructor 5'
    }
}
COURSE_INSTRUCTOR_MAPPING = {
    6191: 'Madeline Stark',
    5145: 'Nancy Noyes',
    5153: 'Nancy Noyes',
    5146: 'Benjamin Aschenbrenner',
    5154: 'Benjamin Aschenbrenner',
    5162: 'Benjamin Aschenbrenner'
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


def get_courses_without_blueprint():
    """
    Retrieves a list of course IDs that are not associated with a 
    Blueprint course from the Canvas API.

    Returns:
        list: A list of course IDs that are not associated with a Blueprint course.
    """
    url = f'{COURSEURL}/api/v1/accounts/667/courses'
    headers = {'Authorization': f'Bearer {CANVAS_API_KEY}'}
    params = {
        'with_enrollments': True,
        'enrollment_type[]': 'Student',
        'published': True,
        'completed': False,
        'blueprint_associated': False,
        'per_page': 100
    }
    course_ids = []
    for phase in range(2, 6):
        search_term = f'Phase {phase}'
        params['search_term'] = search_term
        response = requests.get(url, headers=headers,
                                params=params, timeout=10)
        if response.status_code == 200:
            results = response.json()
            for result in results:
                course_ids.append(result['id'])
        else:
            response.raise_for_status()
    return course_ids


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
    params = {'enrollment_type[]': 'student'}
    headers = {'Authorization': f'Bearer {CANVAS_API_KEY}'}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    students = response.json()

    url = (
        f'{COURSEURL}/api/v1/courses/{course_id}/'
        f'assignments?search_term=%5BFlex%5D%20Student%20Survey%20for%20Phase'
    )
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
                'email': student['email'],
                'sis_user_id': student['sis_user_id'],
                'assignment_name': assignment_name,
                'new_instructor_name': new_instructor_name
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

    # Step 2: Extract the 'sis_user_id', 'new_instructor_name', and 'assignment_name' column data
    existing_students = [
        {
            'sis_user_id': row[2],
            'assignment_name': row[5]
        } for row in existing_data if len(row) > 5

    ] if existing_data else []
    values = []

    # Define current_row before the loop
    current_row = len(existing_data) + 2

    # Step 3: Check for duplicates between the new data and the existing data
    for student in data:
        print(f'Student: {student}')
        print(f'Existing: {existing_students}')
        # Check if the student is already in the sheet with the same new instructor name
        is_duplicate = any(
            existing_student['sis_user_id'] == student['sis_user_id']
            and existing_student['assignment_name'] == student['assignment_name']
            for existing_student in existing_students
        )
        print(is_duplicate)
        if not is_duplicate:
            row = [
                datetime.datetime.now().strftime('%Y-%m-%d'),  # Week of
                student['name'],  # Full name
                student['sis_user_id'],  # sis_user_id
                student['email'],  # Email address
                student['new_instructor_name'],  # new instructor name
                student['assignment_name'],  # Which phase completed
                {"userEnteredValue": {
                    "formulaValue": (
                        f'=IFERROR(VLOOKUP("{student["new_instructor_name"]}",'
                        f' \'Instructor Roster\'!A:B, 2, FALSE), "not found")'
                    )
                }}
            ]

            values.append(row)
            current_row += 1  # only add the increment for the vlookup when appending a row

    if not values:
        print("No new data to add.")
        return

    values_for_update = [{'values': [{'userEnteredValue': {'stringValue': str(
        cell)}} if not isinstance(cell, dict) else cell for cell in row]} for row in values]

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
                        # increase end column index by 1 for the Ops Complete Data Validation
                        'endColumnIndex': 1 + len(values[0]) + 1
                    },
                    'rows': values_for_update,
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


def get_counters():
    """
    Fetch the counters from 'counters.txt' file.

    This function reads the 'counters.txt' file line by line and returns the
    values as integers. If the file does not exist or contains less than 2 lines,
    the function returns 0, 0.

    Returns:
        phase_2_counter (int): Counter for phase 2.
        phase_5_counter (int): Counter for phase 5.
    """
    if not os.path.exists('counters.txt'):
        return 0, 0

    with open('counters.txt', 'r', encoding='utf-8') as file:
        counters = file.readlines()

    if len(counters) < 2:
        return 0, 0

    phase_2_counter = int(counters[0].strip())
    phase_5_counter = int(counters[1].strip())

    return phase_2_counter, phase_5_counter



def save_counters(phase_2_counter, phase_5_counter):
    """
    Save the counters to 'counters.txt' file.

    This function takes two arguments, phase_2_counter and phase_5_counter,
    converts them to strings, and writes them to 'counters.txt' file, one
    on each line.

    Args:
        phase_2_counter (int): The counter for phase 2 to be saved.
        phase_5_counter (int): The counter for phase 5 to be saved.

    Returns:
        None
    """
    with open('counters.txt', 'w', encoding='utf-8') as file:
        file.write(str(phase_2_counter) + '\n')
        file.write(str(phase_5_counter) + '\n')

def main():
    """
    Entry point for the script to retrieve and process student data from Canvas 
    and append it to a Google Sheet.

    This function:
        1. Authenticates the user with the Google API and refreshes the access token if necessary.
        2. Loops through blueprint courses and their associated courses, 
        as well as courses that don't have an associated blueprint.
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
    phase_2_instructors = ['Madeline Stark', 'Demetrio Lima']
    phase_5_instructors = ['Ryan Parrish', 'Dustin Anderson', 'Madeline Stark', 'Demetrio Lima',
                           'Nancy Noyes', 'Aastha Saxena', 'Enoch Griffith',
                            'Benjamin Aschenbrenner']
    phase_2_counter, phase_5_counter = get_counters()
    for blueprint_course in BLUEPRINT_COURSES:
        # print(f"Processing blueprint course: {blueprint_course}")
        associated_courses = get_associated_courses(blueprint_course)
        for course in associated_courses:
            # print(f"Processing course ID: {course['id']}")
            for phase_name, instructor_mapping in PHASE_INSTRUCTOR_MAPPING.items():
                students = get_students_with_assignment(
                    course['id'], phase_name, 1, 30)
                for student in students:
                    if phase_name == '[Flex] Student Survey for Phase 1':
                        # Use mod 2 counter for Phase 2 to alternate between instructors
                        new_instructor_name = phase_2_instructors[phase_2_counter % len(
                            phase_2_instructors)]
                        phase_2_counter += 1
                    elif phase_name == '[Flex] Student Survey for Phase 4':
                        new_instructor_name = phase_5_instructors[phase_5_counter % len(
                            phase_5_instructors)]
                        phase_5_counter += 1
                    else:
                        new_instructor_name = instructor_mapping['new_instructor']
                    student["new_instructor_name"] = new_instructor_name
                    all_students.extend([student])

    # Process courses without blueprint
    course_ids = get_courses_without_blueprint()
    for course_id in course_ids:
        print(f"Processing course ID: {course_id}")
        new_instructor_name = COURSE_INSTRUCTOR_MAPPING.get(course_id, 'Unknown Instructor')
        for phase_name, _ in PHASE_INSTRUCTOR_MAPPING.items():
            students = get_students_with_assignment(
                course_id, phase_name, 1, 30)
            for student in students:
                student["new_instructor_name"] = new_instructor_name
            all_students.extend(students)
    append_to_google_sheet(all_students, creds)
    save_counters(phase_2_counter, phase_5_counter)


if __name__ == '__main__':
    main()
