import boto3
from utils import check_html_extension


def fetch_html_content(file: str, bucket_name: str):
    """
    Function to fetch the html content from the S3 bucket
    @param file: File name
    @param bucket_name: Bucket name
    @return: HTML content
    """

    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket=bucket_name, Key=file)
    html_content = response['Body'].read().decode('utf-8')

    return html_content


def get_html_code(file: str, bucket: str):
    """
    Function to get the HTML code from the S3 bucket
    @param file: File name
    @param bucket: Bucket name
    @return: HTML code or None if the file is not an HTML
    """

    if not check_html_extension(file):
        return None

    html_code = fetch_html_content(file, bucket)

    return html_code
