#!/usr/bin/env python3

from parser import extract_and_parse_info, detect_newspaper_type
from datetime import date
import os


def test_parser():
    """
    Test function to verify the parser works with both newspapers
    """
    curr_date = date.today().strftime("%Y-%m-%d")

    # Test El Tiempo
    if os.path.exists('eltiempo-2025-06-03.html'):
        print("🔍 Testing El Tiempo...")
        with open('eltiempo-2025-06-03.html', 'r', encoding='utf-8') as f:
            html_content = f.read()

        news_data = extract_and_parse_info(html_content, curr_date, 'eltiempo-2025-06-03')
        newspaper_type = detect_newspaper_type('eltiempo-2025-06-03')

        print(f"📰 Newspaper type: {newspaper_type}")
        print(f"📊 Number of news extracted: {len(news_data)}")

        if news_data:
            print("📝 First 3 news items:")
            for i, news in enumerate(news_data[:3]):
                print(f"   {i+1}. [{news[1]}] {news[2][:50]}... - {news[3][:50]}...")

        print()

    # Test El Espectador
    if os.path.exists('elespectador-2025-06-03.html'):
        print("🔍 Testing El Espectador...")
        with open('elespectador-2025-06-03.html', 'r', encoding='utf-8') as f:
            html_content = f.read()

        news_data = extract_and_parse_info(html_content, curr_date, 'elespectador-2025-06-03')
        newspaper_type = detect_newspaper_type('elespectador-2025-06-03')

        print(f"📰 Newspaper type: {newspaper_type}")
        print(f"📊 Number of news extracted: {len(news_data)}")

        if news_data:
            print("📝 First 3 news items:")
            for i, news in enumerate(news_data[:3]):
                print(f"   {i+1}. [{news[1]}] {news[2][:50]}... - {news[3][:50]}...")
        else:
            print("⚠️ No news extracted! Let's debug...")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            cards = soup.find_all("div", class_=lambda x: x and "Card" in x)
            print(f"🔍 Found {len(cards)} Card elements")

            links = soup.find_all("a", href=True)
            espectador_links = [link for link in links if link.get('href') and 'elespectador.com' in link.get('href')]
            print(f"🔗 Found {len(espectador_links)} elespectador.com links")


if __name__ == "__main__":
    test_parser()
