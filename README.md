# Canvas Progress Tracker

This script retrieves information about Flex students' progress in Canvas courses, including their new instructor, and appends the data to a Google Sheet. The script uses the Canvas API to fetch course and student data, and the Google Sheets API to update the spreadsheet.

## Prerequisites

- Python 3.x installed on your system
- A Google Cloud project with Sheets API enabled
- Access to Canvas instance with API token

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

## Contributing

- Fork the repository
- Create a new branch for your changes
- Open a pull request with a description of your changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting

- Ensure you have the correct Canvas API token and URL in your `.env` file.
- Check that your Google Cloud project has the Sheets API enabled and that the `credentials.json` file is in the same directory as the script.
- If the script doesn't run or fails with an error, ensure that you have installed all required packages using `pip3 install -r requirements.txt`.
- If the data is not being appended to the Google Sheet, double-check that the `SHEET_TAB_NAME` variable is set to the correct tab name in your Google Sheet.
- If you encounter a "ModuleNotFoundError" error, make sure you have installed the required packages and that your Python environment is set up correctly.
- If you receive a "TypeError" or "ValueError" related to date and time formatting, ensure that the date and time values in the script and the Google Sheet are in the expected format.

For further assistance, please open an issue on the GitHub repository, and provide a detailed description of the problem you are experiencing. This will help us identify the issue and provide support to resolve it.
