# DKB-transaction-analysis

A tool that queries and analyses your past DKB transactions via a reverse engineered DKB API.

# Install

Run `poetry shell` to create a virtual environment, then run `poetry install`.
If you want to install the requirements, via a `requirements.txt` file, you can
run `poetry export -f requirements.txt --output requirements.txt` to export a `requirements.txt` file.

# Run

Create a `.env` file and add your `DKB_USERNAME=***` and `DKB_PASSWORD=***`
Activate the Google Sheets API and download the corresponding Google Sheets API `credentials.json` file and put into the
root dir.

Run `python main.py`.

The script will attempt to log in into your DKB account which has to be approved via two-factor-authentication.
All present transactions will be downloaded, categorised and uploaded into a Google Sheet.

The final result can be found in your Google Drive home. 
