from bs4 import BeautifulSoup
import re


def detect_newspaper_type(file_name):
    """
    Detecta el tipo de periódico basado en el nombre del archivo
    @param file_name: Nombre del archivo
    @return: String indicando el tipo de periódico
    """
    if 'eltiempo' in file_name.lower():
        return 'eltiempo'
    elif 'elespectador' in file_name.lower():
        return 'elespectador'
    else:
        return 'unknown'


def extract_news_from_eltiempo(soup):
    """
    Extrae noticias de El Tiempo
    @param soup: BeautifulSoup object del HTML
    @return: Lista de noticias con [categoría, titular, enlace]
    """
    news_data = []
    
    # Buscar artículos con la clase c-articulo
    articles = soup.find_all("article", class_=re.compile(r"c-articulo"))
    
    for article in articles:
        try:
            # Extraer titular
            title_element = article.find("h2", class_="c-articulo__titulo") or \
                          article.find("h3", class_="c-articulo__titulo")
            
            if title_element:
                title_link = title_element.find("a", class_="c-articulo__titulo__txt")
                if title_link:
                    titular = title_link.get_text(strip=True)
                    enlace = title_link.get('href', '')
                    
                    # Si el enlace es relativo, añadir el dominio
                    if enlace and not enlace.startswith('http'):
                        enlace = 'https://www.eltiempo.com' + enlace
                    
                    # Extraer categoría de los data attributes
                    categoria = article.get('data-category', 'Sin categoría')
                    seccion = article.get('data-seccion', '')
                    subseccion = article.get('data-subseccion', '')
                    
                    # Construir categoría completa
                    if seccion and subseccion:
                        categoria = f"{seccion}/{subseccion}"
                    elif seccion:
                        categoria = seccion
                    
                    if titular and enlace:
                        news_data.append([categoria, titular, enlace])
                        
        except Exception as e:
            continue
    
    return news_data


def extract_news_from_elespectador(soup):
    """
    Extrae noticias de El Espectador
    @param soup: BeautifulSoup object del HTML
    @return: Lista de noticias con [categoría, titular, enlace]
    """
    news_data = []
    
    # Buscar elementos Card que contienen las noticias
    cards = soup.find_all("div", class_=lambda x: x and "Card" in x)
    
    for card in cards:
        try:
            # Buscar el enlace principal de la noticia
            title_link = card.find("a", href=True)
            
            if title_link:
                href = title_link.get('href', '')
                
                # Solo procesar enlaces que son de noticias de El Espectador
                if href and ('elespectador.com' in href and 
                           ('/' in href.replace('https://www.elespectador.com', '')) and
                           not any(skip in href for skip in ['play', 'autores', 'terminos', 'newsletter'])):
                    
                    # Buscar el título en h2 dentro del card
                    title_element = card.find("h2", class_=lambda x: x and "Card-Title" in x)
                    if title_element:
                        title_link_element = title_element.find("a")
                        if title_link_element:
                            titular = title_link_element.get_text(strip=True)
                        else:
                            titular = title_element.get_text(strip=True)
                    else:
                        # Si no hay h2, buscar en el enlace principal
                        titular = title_link.get_text(strip=True)
                    
                    # Filtrar títulos muy cortos
                    if len(titular) < 10:
                        continue
                    
                    enlace = href
                    
                    # Buscar la categoría en el Card-Section
                    section_element = card.find("h4", class_=lambda x: x and "Card-Section" in x)
                    if section_element:
                        section_link = section_element.find("a")
                        if section_link:
                            categoria = section_link.get_text(strip=True)
                        else:
                            categoria = section_element.get_text(strip=True)
                    else:
                        # Extraer categoría de la URL como fallback
                        url_path = href.replace('https://www.elespectador.com/', '')
                        url_parts = url_path.strip('/').split('/')
                        if len(url_parts) >= 1 and url_parts[0]:
                            categoria = url_parts[0].replace('-', ' ').title()
                        else:
                            categoria = 'Sin categoría'
                    
                    if titular and enlace and len(titular) > 10:
                        news_data.append([categoria, titular, enlace])
                        
        except Exception as e:
            continue
    
    # También buscar enlaces directos en títulos y headings
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        try:
            link = heading.find('a', href=True)
            if link:
                href = link.get('href', '')
                titular = link.get_text(strip=True)
                
                # Solo procesar enlaces que son de noticias de El Espectador
                if (href and len(titular) > 10 and 
                    'elespectador.com' in href and
                    not any(skip in href for skip in ['play', 'autores', 'terminos', 'newsletter'])):
                    
                    enlace = href
                    
                    # Extraer categoría de la URL
                    url_path = href.replace('https://www.elespectador.com/', '')
                    url_parts = url_path.strip('/').split('/')
                    if len(url_parts) >= 1 and url_parts[0]:
                        categoria = url_parts[0].replace('-', ' ').title()
                    else:
                        categoria = 'Sin categoría'
                    
                    news_data.append([categoria, titular, enlace])
                    
        except Exception as e:
            continue
    
    # Eliminar duplicados basados en el enlace
    seen_urls = set()
    unique_news = []
    
    for news in news_data:
        if news[2] not in seen_urls:
            seen_urls.add(news[2])
            unique_news.append(news)
    
    return unique_news


def extract_and_parse_info(html_content, curr_date, file_name=None):
    """
    Function to extract and parse the information from the HTML content
    @param html_content: HTML content of the news website
    @param curr_date: Current date
    @param file_name: Name of the file to detect newspaper type
    @return: List with the information of the news
    """
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    news_data = []
    
    # Detectar tipo de periódico
    if file_name:
        newspaper_type = detect_newspaper_type(file_name)
    else:
        # Intentar detectar por el contenido del HTML
        if 'eltiempo.com' in html_content.lower():
            newspaper_type = 'eltiempo'
        elif 'elespectador.com' in html_content.lower():
            newspaper_type = 'elespectador'
        else:
            newspaper_type = 'unknown'
    
    # Extraer noticias según el tipo de periódico
    if newspaper_type == 'eltiempo':
        extracted_news = extract_news_from_eltiempo(soup)
    elif newspaper_type == 'elespectador':
        extracted_news = extract_news_from_elespectador(soup)
    else:
        # Intentar ambos métodos si no se puede detectar
        extracted_news = extract_news_from_eltiempo(soup)
        if not extracted_news:
            extracted_news = extract_news_from_elespectador(soup)
    
    # Añadir fecha a cada noticia
    for news in extracted_news:
        news_data.append([curr_date] + news)
    
    return news_data
