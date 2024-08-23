import time
import glob
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Automatically install chromedriver if not present
chromedriver_autoinstaller.install()

# Authenticate and initialize PyDrive2 for Google Drive
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# Function to log in
def login(driver, username, password):
    driver.get("https://my.voipfone.co.uk/#!/dashboard+auth")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'username'))).send_keys(username)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'password'))).send_keys(password)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]'))).click()

# Function to navigate and download the file
def download_call_records(driver):
    # Navigate directly to the 'Call Records' page
    driver.get("https://my.voipfone.co.uk/#!/services/call-records/view")
    # Wait for the page to load
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))

    # Scroll to the bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)  # Wait for any lazy-loaded elements to load

    # Wait for 'Download CSV' button to be clickable and click it
    download_csv_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[name="csv"]'))
    )
    driver.execute_script("arguments[0].click();", download_csv_button)
    # Adjust the timing below based on how long it typically takes to initiate the download
    time.sleep(10)  # Wait for the download to initiate

# Function to manage the downloaded file and upload it to Google Drive
def manage_and_upload_file():
    download_dir = r"C:\Users\Union Eleven\Downloads"
    list_of_files = glob.glob(download_dir + "\\*.csv")
    latest_file = max(list_of_files, key=os.path.getctime)

    # Rename the file
    today = datetime.now().strftime('%d-%m-%Y')
    new_filename = f"{today}.csv"
    new_filepath = os.path.join(download_dir, new_filename)
    os.rename(latest_file, new_filepath)

    # Upload the file to Google Drive
    file_drive = drive.CreateFile({'title': new_filename})
    file_drive.SetContentFile(new_filepath)
    file_drive.Upload()
    print(f"Uploaded {new_filename} to Google Drive")

# Load credentials from Streamlit secrets
username = st.secrets["voip_username"]
password = st.secrets["voip_password"]

# Set up the Selenium driver with Chrome options for automatic download
options = webdriver.ChromeOptions()
options.add_experimental_option("prefs", {
    "download.default_directory": r"C:\Users\Union Eleven\Downloads",
    "download.prompt_for_download": False,
})
options.add_argument("--headless")  # Runs Chrome in headless mode.
driver = webdriver.Chrome(options=options)

# Perform the automated process
try:
    login(driver, username, password)
    download_call_records(driver)
    manage_and_upload_file()
finally:
    # Close the browser
    driver.quit()
