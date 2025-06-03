from datetime import date
from html_extracter import get_html_code
from utils import NotFoundException, create_directory
from parser import extract_and_parse_info, detect_newspaper_type
from files import save_to_csv, upload_file


def main(record):
    """
    Main function to run the program
    @param record: Record with the information of the file
    @return: None
    """

    file_name = record["s3"]["object"]["key"]
    bucket_name = record['s3']['bucket']['name']

    html_content = get_html_code(file_name, bucket_name)

    if not html_content:
        raise NotFoundException("El archivo no es un HTML")

    curr_date = date.today().strftime("%Y-%m-%d")
    year = date.today().strftime("%Y")
    month = date.today().strftime("%m")
    day = date.today().strftime("%d")

    create_directory(f"/tmp")

    # Extraer el nombre del archivo sin la ruta primero
    file_name_split = str(file_name.split("/")[1]).replace(".html", "")

    data = extract_and_parse_info(html_content, curr_date, file_name_split)
    
    # Detectar el periódico
    newspaper_type = detect_newspaper_type(file_name_split)
    
    print(f"🔍 Newspaper type: {newspaper_type}")
    
    # Crear nombre del archivo con estructura de particiones
    csv_file_name = f'/tmp/{file_name_split}.csv'
    
    # Crear la ruta de S3 con particiones según el README
    s3_path = f"headlines/final/periodico={newspaper_type}/year={year}/month={month}/day={day}/{file_name_split}.csv"

    save_to_csv(csv_file_name, data)

    upload_file(csv_file_name, s3_path=s3_path)
