import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


# Authentication using service account
def authenticate():
    gauth = GoogleAuth()
    scope = ['https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gdrive_service_account"], scope
    )
    gauth.credentials = credentials
    return gauth


gauth = authenticate()

# Set page configuration
st.set_page_config(page_title='SFS Call Stats', page_icon=':telephone_receiver:', layout='wide')

# Custom CSS for the layout
st.markdown("""
    <style>
    .carousel-container {
        overflow-x: auto;
        white-space: nowrap;
        padding: 20px 0;
    }
    .carousel-item {
        display: inline-block;
        background-color: #f9f9f9;
        margin: 0 10px;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        min-width: 300px;
    }
    .carousel-item img {
        max-width: 100%;
        max-height: 150px;
        object-fit: cover;
        border-radius: 5px;
    }
    .carousel-link {
        text-decoration: none;
        color: #007bff;
    }
    .article-item {
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        background-color: #f9f9f9;
    }
    .article-item h3 {
        color: #333333;
    }
    .article-item p {
        color: #666666;
    }
    .highlighted {
        background-color: #ffd1d1;
    }
    .dataframe-container {
        width: 100% !important;
        overflow-x: auto;
    }
    .dataframe-container table {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and logo
st.markdown("<h1 style='text-align: center; color: black;'>SFS Dashboard</h1>", unsafe_allow_html=True)
logo = 'assets/sfs_logo_clean-red.png'
st.image(logo, width=300)

# Function to download a file from Google Drive
def download_file_from_drive(file_name):
    file_list = drive.ListFile({'q': f"title='{file_name}' and trashed=false"}).GetList()
    if file_list:
        file = file_list[0]  # Get the first matching file
        file.GetContentFile(f'assets/{file_name}')
        return pd.read_csv(f'assets/{file_name}')
    else:
        st.error(f"File '{file_name}' not found on Google Drive.")
        return None

# Load and process data
hourly_filename = f'hourly_summary_{datetime.now().date()}.csv'
hourly_data = download_file_from_drive(hourly_filename)

if hourly_data is not None:
    # List of all unique staff members
    all_staff_names = hourly_data['Name'].unique()

    # Create a DataFrame for all staff members
    all_staff = pd.DataFrame({'Name': all_staff_names})

    # List of staff to include if their calls are higher than 0
    staff_to_include = ['Lewis', 'Mike', 'Reece', 'Olivia', 'Steve']

    # Filter by time
    hourly_data = hourly_data[(hourly_data['Hour'] >= 9) & (hourly_data['Hour'] <= 17)]

    # Ensure Name is a string and fill with 'None' for missing entries
    hourly_data['Name'] = hourly_data['Name'].astype(str).fillna('None')

    # Generate a complete set of hours and staff with zeros for missing data
    complete_hours = pd.DataFrame({'Hour': range(9, 18)})
    all_staff_per_hour = pd.merge(complete_hours, all_staff, how='cross')

    # Ensure that both 'Name' columns are strings
    all_staff_per_hour['Name'] = all_staff_per_hour['Name'].astype(str)
    hourly_data['Name'] = hourly_data['Name'].astype(str)

    hourly_summary = pd.merge(all_staff_per_hour, hourly_data, on=['Hour', 'Name'], how='left').fillna({'Calls': 0})

    # Remove decimal places from hourly calls data
    hourly_summary['Calls'] = hourly_summary['Calls'].astype(int)

    # Exclude future hours and hide rows where Name is '0'
    current_hour = datetime.now().hour
    hourly_summary = hourly_summary[(hourly_summary['Hour'] <= current_hour) & (hourly_summary['Name'] != '0')]

    # Exclude rows for Lewis, Reece, Mike, Steve, Olivia if their Calls are 0
    hourly_summary = hourly_summary[~((hourly_summary['Name'].isin(staff_to_include)) & (hourly_summary['Calls'] == 0))]

    # Determine busy hours based on total calls > 20
    hourly_summary_grouped = hourly_summary.groupby('Hour').sum().reset_index()
    hourly_summary_grouped = complete_hours.merge(hourly_summary_grouped, on='Hour', how='left').fillna(0)
    hourly_summary_grouped['isBusy'] = hourly_summary_grouped['Calls'] > 19

    # Altair bar chart for hourly calls
    bars = alt.Chart(hourly_summary_grouped).mark_bar().encode(
        x=alt.X('Hour:O', title='Hour of Day'),
        y=alt.Y('Calls:Q', title='Total Calls'),
        color=alt.condition(
            alt.datum.isBusy,
            alt.value('red'),  # True condition
            alt.value('steelblue')  # False condition
        )
    )

    st.markdown("## Total Calls by Hour")
    st.altair_chart(bars, use_container_width=True)

    # Display a text box for busy hours
    busy_hours_text = ', '.join(
        hourly_summary_grouped[hourly_summary_grouped['isBusy']]['Hour'].astype(int).astype(str))
    if busy_hours_text:
        st.markdown(f"### Busy Hours: {busy_hours_text}. Remember phones! 💪")

    # Displaying hourly call details in tables
    st.markdown("## Hourly Call Details")
    cols = st.columns(9)
    for i, hour in enumerate(range(9, 18)):
        hour_data = hourly_summary[hourly_summary['Hour'] == hour].copy()
        hour_data.sort_values('Calls', ascending=False, inplace=True)
        with cols[i]:
            # Add a container for custom CSS styling
            with st.container():
                st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
                st.table(hour_data[['Name', 'Calls']].reset_index(drop=True))
                st.markdown('</div>', unsafe_allow_html=True)

# Function to load and display daily, weekly, and monthly summaries with performance logic
def load_summary_data(file_name, calls_column):
    data = download_file_from_drive(file_name)
    if data is not None:
        data = data[(~data['Name'].isin(['Mike', 'Steve', 'Lewis', 'Reece', 'Olivia'])) | (data[calls_column] > 0)]
        data = data[data['Name'] != '0']  # Exclude rows where Name is '0'
        avg_calls = data[calls_column].mean()
        data['Performance Recognition'] = data[calls_column].apply(
            lambda x: '🤩' if x > avg_calls * 2 else ('👍' if x >= avg_calls else '')
        )
        data.sort_values(by=calls_column, ascending=False, inplace=True)
        return data
    return pd.DataFrame()  # Return an empty DataFrame if the file isn't found

# Displaying the summaries
col1, col2, col3 = st.columns(3)
summaries = {
    "Daily Calls": load_summary_data('daily_summary.csv', 'Calls_y'),
    "Weekly Calls": load_summary_data('weekly_summary.csv', 'Calls_y'),
    "Monthly Calls": load_summary_data('monthly_summary.csv', 'Calls_y')
}
for col, (title, data) in zip([col1, col2, col3], summaries.items()):
    with col:
        st.subheader(title)
        st.table(data[['Name', 'Calls_y', 'Performance Recognition']].reset_index(drop=True))
