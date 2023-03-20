# Canvas Progress Tracker

This script retrieves information about Flex students' progress in Canvas courses, including their new isntructor, and appends the data to a Google Sheet. The script uses the Canvas API to fetch course and student data, and the Google Sheets API to update the spreadsheet.

## Usage

1. Set up your environment variables in a `.env` file. You need to provide the following:

ctoken=YOUR_CANVAS_API_TOKEN
curl=YOUR_CANVAS_URL


Replace `YOUR_CANVAS_API_TOKEN` with your Canvas API token, and `YOUR_CANVAS_URL` with your Canvas instance URL (e.g., `https://learning.flatironschool.com:443`).

2. Configure the following variables in the script according to your needs:

SHEET_TAB_NAME: Set this variable to the name of the tab in your Google Sheet where the data will be appended.
BLUEPRINT_COURSES: Set this array to include the IDs of the blueprint courses you want to process.
PHASE_INSTRUCTOR_MAPPING: Set this dictionary to map the assignment names to their corresponding instructors. 

3. Install the required packages using the requirements.txt file:

pip3 install -r requirements.txt

4. Follow the [Python Quickstart Guide for Google Sheets API](https://developers.google.com/sheets/api/quickstart/python) to set up a Google Cloud project and download your `credentials.json` file.

5. Run the script:

The script will create a `token.json` file for Google Sheets API authentication.
