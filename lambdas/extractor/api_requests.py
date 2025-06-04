import requests

from config import API_HEADERS
from utils import NotFoundException


def fetch_page(page_url: str):
    """
    Function that downloads a page from a given URL
    @param page_url: URL of the page to download
    @return: Request response (HTML code)
    """

    response = requests.get(
        page_url, headers=API_HEADERS
    )

    if response.status_code == 404:
        raise NotFoundException("❌ Error 404: Página no encontrada")

    if response.status_code != 200:
        raise Exception(f"❌ Error al descargar la página {page_url}: {response.status_code}")

    return response.text
