import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import logging
import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# Automatically install chromedriver if not present
chromedriver_autoinstaller.install()

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.info("Script started")

# Google Drive authentication
def authenticate():
    scope = ["https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gdrive_service_account"], scope
    )
    gauth = GoogleAuth()
    gauth.credentials = credentials
    drive = GoogleDrive(gauth)
    return drive

# Set up Google Drive authentication
drive = authenticate()

# Set up the Selenium driver with Chrome options for automatic download
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Runs Chrome in headless mode.
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(options=options)

# Function to log in
def login():
    username = st.secrets["voip_username"]
    password = st.secrets["voip_password"]

    driver.get("https://my.voipfone.co.uk/#!/dashboard+auth")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'username'))).send_keys(username)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'password'))).send_keys(password)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click()


# Function to navigate and download the file directly to memory
def download_call_records():
    # Navigate directly to the 'Call Records' page
    driver.get("https://my.voipfone.co.uk/#!/services/call-records/view")
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))

    # Scroll to the bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)  # Wait for any lazy-loaded elements to load

    # Wait for 'Download CSV' button to be clickable and click it
    download_csv_button = WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="csv"]'))
    )
    driver.execute_script("arguments[0].click();", download_csv_button)
    time.sleep(10)  # Wait for the download to complete

    # Capture the CSV file content from the download (this assumes it’s in the response body)
    file_content = driver.page_source
    return BytesIO(file_content.encode('utf-8'))

# Function to upload the file to Google Drive
# Function to upload the file to Google Drive
def upload_to_drive(file_content):
    today = datetime.now().strftime('%d-%m-%Y')
    new_filename = f"{today}.csv"

    logging.info(f"Uploading {new_filename} to Google Drive")
    file_drive = drive.CreateFile({'title': new_filename})

    # Use SetContentString to handle the in-memory content
    file_drive.SetContentString(file_content.getvalue().decode('utf-8'))  # Assuming it's a CSV string

    file_drive.Upload()
    logging.info(f"Uploaded {new_filename} to Google Drive")


# Perform the steps
login()
file_content = download_call_records()
upload_to_drive(file_content)

# Close the browser
driver.quit()
