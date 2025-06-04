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

    print(f"🔍 Processing file: {file_name}")
    print(f"🪣 From bucket: {bucket_name}")

    html_content = get_html_code(file_name, bucket_name)

    if not html_content:
        raise NotFoundException("El archivo no es un HTML")

    curr_date = date.today().strftime("%Y-%m-%d")
    year = date.today().strftime("%Y")
    month = date.today().strftime("%m")
    day = date.today().strftime("%d")

    create_directory("/tmp")

    # Extraer el nombre del archivo correctamente - manejar tanto paths con carpetas como sin carpetas
    if "/" in file_name:
        file_name_split = file_name.split("/")[-1].replace(".html", "")
    else:
        file_name_split = file_name.replace(".html", "")

    print(f"📰 File name for processing: {file_name_split}")

    data = extract_and_parse_info(html_content, curr_date, file_name_split)

    # Detectar el periódico
    newspaper_type = detect_newspaper_type(file_name_split)

    print(f"🔍 Newspaper type detected: {newspaper_type}")
    print(f"📊 Number of news extracted: {len(data)}")

    if len(data) == 0:
        print("⚠️ Warning: No news data extracted!")
        # Intentar ver si hay contenido en el HTML
        print(f"📄 HTML content length: {len(html_content)}")
        if 'elespectador' in file_name_split.lower():
            print("🔍 This is El Espectador - checking HTML structure...")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            links = soup.find_all("a", href=True)
            print(f"🔗 Total links found: {len(links)}")

    # Crear nombre del archivo con estructura de particiones
    csv_file_name = f'/tmp/{file_name_split}.csv'

    # Crear la ruta de S3 con particiones según el README
    s3_path = f"headlines/final/periodico={newspaper_type}/year={year}/month={month}/day={day}/{file_name_split}.csv"

    print(f"💾 Saving to: {s3_path}")

    save_to_csv(csv_file_name, data)

    upload_file(csv_file_name, s3_path=s3_path)
