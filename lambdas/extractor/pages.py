import boto3
from config import HTML_BUCKET_NAME
from api_requests import fetch_page


def download_pages(dir_path: str, curr_date: str):
    """
    Function that downloads a number of pages from the Mitula URL
    @param dir_path: Directory path
    @return: List of HTML pages
    """

    pages = []

    pages.append({
        "file_name": f"{dir_path}/eltiempo-{curr_date}.html",
        "content": fetch_page("https://www.eltiempo.com/")
    })

    pages.append({
        "file_name": f"{dir_path}/elespectador-{curr_date}.html",
        "content": fetch_page("https://www.elespectador.com/")
    })

    return pages


def download_and_save_pages(dir_path: str, curr_date: str):
    """
    Function that downloads and pages HTML
    @param dir_path: Directory path
    @return: List of file names
    """

    pages = download_pages(dir_path, curr_date)

    for page in pages:
        with open(page["file_name"], "w") as file:
            file.write(page["content"])

    return [page["file_name"] for page in pages]


def upload_page(file_name: str):
    """
    Function that uploads a page to the S3 bucket
    @param file_name: File name
    @return: None
    """

    object_name = file_name.replace("/tmp/", "headlines/raw/")

    s3_client = boto3.client('s3')

    s3_client.upload_file(file_name, HTML_BUCKET_NAME, object_name)

    print(f"✅ Archivo '{object_name}' subido correctamente al bucket '{HTML_BUCKET_NAME}'")


def upload_pages_to_s3(files_names: list[str]):
    """
    Function that uploads a list of pages to the S3 bucket
    @param files_names: List of file names
    @return: None
    """

    [upload_page(file_name) for file_name in files_names]
