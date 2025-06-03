import csv
import boto3

from config import CSV_BUCKET_NAME


def save_to_csv(filename, data):
    """
    Function to write the data to a CSV file
    @param data: List with the data to write
    @param filename: Name of the file to write
    @return: None
    """

    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(
            ['fecha', 'categoria', 'titular', 'enlace']
        )
        writer.writerows(data)


def upload_file(file_name, bucket=CSV_BUCKET_NAME, s3_path=None):
    """
    Function to upload a file to an S3 bucket
    @param file_name: Name of the file to upload
    @param bucket: Name of the bucket
    @param s3_path: S3 path including partitions structure
    @return: None
    """

    # Si no se proporciona s3_path, usar el comportamiento anterior
    if s3_path is None:
        object_name = file_name.replace("/tmp/", "headlines/final/")
    else:
        object_name = s3_path

    # Upload the file
    s3_client = boto3.client('s3')
    s3_client.upload_file(file_name, bucket, object_name)
    print(f"✅ Archivo '{object_name}' subido correctamente al bucket '{bucket}'")
