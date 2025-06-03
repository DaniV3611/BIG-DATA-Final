import os
from config import HTML_EXTENSION


def check_html_extension(file):
    """
    Function to check if the file has the HTML extension.

    :param file: Name of the file
    :return: True if the file has the HTML extension, False otherwise
    """
    return HTML_EXTENSION.match(file)


def create_directory(directory):
    """
    Function to create a directory.

    :param directory: Name of the directory
    :return: None
    """
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


class NotFoundException(Exception):
    """Custom Exception for Not Found Errors in requests."""

    def __init__(self, message):
        super().__init__(message)
