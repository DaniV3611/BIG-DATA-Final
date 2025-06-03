import os


def create_directory(directory):
    """
    Function that creates a directory
    @param directory: Directory path
    @return: None
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def delete_directory(directory):
    """
    Function that deletes a directory
    @param directory: Directory path
    @return: None
    """

    if os.path.exists(directory):
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                delete_directory(file_path)
        os.rmdir(directory)


class NotFoundException(Exception):
    """Custom Exception for Not Found Errors in requests."""

    def __init__(self, message):
        super().__init__(message)
