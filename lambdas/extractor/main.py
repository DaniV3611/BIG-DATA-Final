from datetime import date

from pages import download_and_save_pages, upload_pages_to_s3
from utils import create_directory, delete_directory


def main():

    # Get the current date
    curr_date = date.today().strftime("%Y-%m-%d")

    dir_path = f"/tmp/periodico-{curr_date}"

    create_directory(dir_path)

    # Download and save the pages
    pages_names = download_and_save_pages(dir_path, curr_date)

    upload_pages_to_s3(pages_names)

    delete_directory(dir_path)
