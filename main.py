import pandas as pd
import os
from datetime import datetime
import re
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Authenticate and initialize PyDrive2
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # This will open a browser window for Google sign-in
drive = GoogleDrive(gauth)


# Function to find the most recent CSV file in Google Drive
def find_most_recent_csv_in_drive():
    # List all files in Google Drive
    file_list = drive.ListFile({'q': "mimeType='text/csv' and trashed=false"}).GetList()

    # Filter files matching the date pattern (assuming dates are in the filename)
    date_pattern = re.compile(r'\d{2}-\d{2}-\d{4}\.csv')
    csv_files = [f for f in file_list if date_pattern.search(f['title'])]

    if not csv_files:
        return None

    # Find the most recent file by comparing dates in the filename
    latest_file = max(csv_files,
                      key=lambda x: datetime.strptime(date_pattern.search(x['title']).group(), '%d-%m-%Y.csv'))
    return latest_file


# Function to download a file from Google Drive
def download_from_drive(file, local_file_path):
    file.GetContentFile(local_file_path)
    print(f"Downloaded {file['title']} to {local_file_path}")


# Function to upload a file to Google Drive
def upload_to_drive(local_file_path, drive_file_name):
    file = drive.CreateFile({'title': drive_file_name})
    file.SetContentFile(local_file_path)
    file.Upload()
    print(f"Uploaded {drive_file_name} to Google Drive")


# Mapping of extensions to staff names
extension_to_name = {
    '*200': 'Chloe',
    '*201': 'Nicola',
    '*202': 'Jess',
    '*203': 'Debbie',
    '*204': 'Emma',
    '*205': 'Frankie',
    '*206': 'Sharon',
    '*207': 'Becky',
    '*208': 'Reece',
    '*209': 'Lewis',
    '*210': 'Olivia',
    '*211': 'Kim',
    '*212': 'Mike',
    '*213': 'Chris',
    '*214': 'Leah',
    '*215': 'Steve',
    '*228': 'Charlee',
    '*229': 'Ellie',
    '*230': 'Michelle',
    '*231': 'Abbie',
    '*232': 'Bethany',
}


# Function to map extension to staff name
def map_extension_to_staff_name(extension, day_of_week):
    return extension_to_name.get(extension, 'Unknown')


# Get the current day, week, and month
now = datetime.now()
current_day = now.date()
current_week = now.isocalendar()[1]
current_month = now.month
current_year = now.year

# Print the current system date for debugging
print(f"System Date: {current_day}")

# Find the most recent CSV file in Google Drive
current_csv_file = find_most_recent_csv_in_drive()
if current_csv_file:
    local_csv_path = os.path.join('assets', current_csv_file['title'])

    # Download the file locally to process it
    download_from_drive(current_csv_file, local_csv_path)

    # Load the CSV into a DataFrame
    df = pd.read_csv(local_csv_path)

    # Convert 'Date & Time' to datetime
    df['Date & Time'] = pd.to_datetime(df['Date & Time'], format='%d/%m/%Y %H:%M', errors='coerce')

    # Create 'Day of Week' column
    df['Day of Week'] = df['Date & Time'].dt.dayofweek

    # Extract the extension part and replace 'To' column with names based on extensions
    df['Extracted Extension'] = df['To'].str.extract(r'(\*\d+)$')[0]
    df['Name'] = df.apply(lambda row: map_extension_to_staff_name(row['Extracted Extension'], row['Day of Week']),
                          axis=1)

    # Filter for answered calls that have a recognized extension
    answered_calls = df[df['Name'] != 'Unknown'].copy()

    # Create date-related columns
    answered_calls['Date'] = answered_calls['Date & Time'].dt.date
    answered_calls['Week'] = answered_calls['Date & Time'].dt.isocalendar().week
    answered_calls['Month'] = answered_calls['Date & Time'].dt.month
    answered_calls['Year'] = answered_calls['Date & Time'].dt.year

    # Filter data for current period
    daily_summary = answered_calls[answered_calls['Date'] == current_day].groupby('Name').size().reset_index(
        name='Calls').sort_values(by='Calls', ascending=False)
    weekly_summary = answered_calls[
        (answered_calls['Week'] == current_week) & (answered_calls['Year'] == current_year)].groupby(
        'Name').size().reset_index(name='Calls').sort_values(by='Calls', ascending=False)
    monthly_summary = answered_calls[answered_calls['Month'] == current_month].groupby('Name').size().reset_index(
        name='Calls').sort_values(by='Calls', ascending=False)

    # Calculate average calls
    daily_summary['Average Calls'] = daily_summary['Calls'].mean()
    weekly_summary['Average Calls'] = weekly_summary['Calls'].mean()
    monthly_summary['Average Calls'] = monthly_summary['Calls'].mean()

    # Calculate total calls
    daily_summary['Total Calls'] = daily_summary['Calls'].sum()
    weekly_summary['Total Calls'] = weekly_summary['Calls'].sum()
    monthly_summary['Total Calls'] = monthly_summary['Calls'].sum()

    # List of all staff names
    all_staff_names = [
        'Chloe', 'Nicola', 'Jess', 'Emma', 'Frankie', 'Sharon', 'Becky', 'Reece',
        'Lewis', 'Olivia', 'Kim', 'Mike', 'Chris', 'Leah',
        'Steve', 'Charlee', 'Michelle', 'Abbie', 'Ellie', 'Bethany', 'Debbie'
    ]

    # Create a DataFrame for all staff names with zero calls
    all_staff_df = pd.DataFrame(all_staff_names, columns=['Name'])
    all_staff_df['Calls'] = 0

    # Merge your summary data with the all_staff_df
    daily_summary = pd.merge(all_staff_df, daily_summary, on='Name', how='outer').fillna(0)
    weekly_summary = pd.merge(all_staff_df, weekly_summary, on='Name', how='outer').fillna(0)
    monthly_summary = pd.merge(all_staff_df, monthly_summary, on='Name', how='outer').fillna(0)

    # Save summaries to CSV in the local directory and upload to Google Drive
    summaries = {
        'daily_summary.csv': daily_summary,
        'weekly_summary.csv': weekly_summary,
        'monthly_summary.csv': monthly_summary,
    }

    for summary_file, summary_df in summaries.items():
        summary_path = os.path.join('assets', summary_file)
        summary_df.to_csv(summary_path, index=False)

        # Upload the summary file to Google Drive
        upload_to_drive(summary_path, summary_file)

    # Calculate hourly stats for the current day
    answered_calls_today = answered_calls[answered_calls['Date'] == current_day].copy()
    answered_calls_today['Hour'] = answered_calls_today['Date & Time'].dt.hour

    # Create a DataFrame for all possible hours in the day (0-23)
    hours = pd.DataFrame({'Hour': range(24)})

    # Group by 'Hour' and 'Name' to count calls per hour for each staff
    hourly_calls_today = answered_calls_today.groupby(['Hour', 'Name']).size().reset_index(name='Calls')

    # Merge with all hours to ensure every hour is represented
    hourly_summary_today = pd.merge(hours, hourly_calls_today, on='Hour', how='left').fillna(0)
    hourly_summary_today['Total Calls'] = hourly_summary_today.groupby('Hour')['Calls'].transform('sum')

    # Save hourly summary for today to CSV and upload it to Google Drive
    hourly_summary_file = os.path.join('assets', f'hourly_summary_{current_day}.csv')
    hourly_summary_today.to_csv(hourly_summary_file, index=False)
    upload_to_drive(hourly_summary_file, f'hourly_summary_{current_day}.csv')

    # Print hourly summary for debugging
    print(f"Hourly Summary for {current_day}:")
    print(hourly_summary_today)

    # Print last updated time
    last_updated = now.strftime('%Y-%m-%d %H:%M:%S')
    print(f"Data processed from the file: {current_csv_file['title']}")
    print(f"Last updated on: {last_updated}")

else:
    print("No CSV files found in Google Drive.")
