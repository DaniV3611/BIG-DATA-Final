#!/usr/bin/env python3
"""
AWS Glue Job: HTML Processor
Processes HTML files from S3 using BeautifulSoup and saves structured data as CSV
Migrated from Lambda processor functionality
"""

import sys
import boto3
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup
import re
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'S3_BUCKET',
    'S3_INPUT_PREFIX',
    'S3_OUTPUT_PREFIX'
])

job.init(args['JOB_NAME'], args)

# Configuration
S3_BUCKET = args.get('S3_BUCKET', 'your-bucket-name')
S3_INPUT_PREFIX = args.get('S3_INPUT_PREFIX', 'headlines/raw')
S3_OUTPUT_PREFIX = args.get('S3_OUTPUT_PREFIX', 'headlines/final')

# Initialize S3 client
s3_client = boto3.client('s3')

def get_html_from_s3(s3_key):
    """
    Download HTML content from S3
    @param s3_key: S3 key path
    @return: HTML content or None
    """
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        return content
    except Exception as e:
        logger.error(f"Error reading from S3: {str(e)}")
        return None

def detect_newspaper_type(filename):
    """
    Detect newspaper type from filename
    @param filename: File name
    @return: Newspaper type
    """
    filename_lower = filename.lower()
    if 'eltiempo' in filename_lower:
        return 'eltiempo'
    elif 'elespectador' in filename_lower:
        return 'elespectador'
    else:
        return 'unknown'

def extract_eltiempo_news(soup, curr_date):
    """
    Extract news from El Tiempo HTML
    @param soup: BeautifulSoup object
    @param curr_date: Current date
    @return: List of news dictionaries
    """
    news_list = []
    
    try:
        # Find news articles in El Tiempo
        articles = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'.*article.*|.*news.*|.*story.*'))
        
        for article in articles:
            try:
                # Extract title
                title_elem = (article.find('h1') or 
                            article.find('h2') or 
                            article.find('h3') or
                            article.find('a', class_=re.compile(r'.*title.*|.*headline.*')))
                
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                # Extract link
                link_elem = article.find('a', href=True)
                link = link_elem['href'] if link_elem else ''
                
                # Make link absolute if relative
                if link and link.startswith('/'):
                    link = 'https://www.eltiempo.com' + link
                
                # Extract category (if available)
                category_elem = article.find(class_=re.compile(r'.*category.*|.*section.*'))
                category = category_elem.get_text(strip=True) if category_elem else 'General'
                
                if title and len(title) > 10:  # Filter out empty or very short titles
                    news_list.append({
                        'fecha': curr_date,
                        'categoria': category,
                        'titular': title,
                        'enlace': link,
                        'periodico': 'eltiempo'
                    })
                    
            except Exception as e:
                logger.warning(f"Error processing article: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error extracting El Tiempo news: {str(e)}")
    
    return news_list

def extract_elespectador_news(soup, curr_date):
    """
    Extract news from El Espectador HTML
    @param soup: BeautifulSoup object
    @param curr_date: Current date
    @return: List of news dictionaries
    """
    news_list = []
    
    try:
        # Find news articles in El Espectador
        articles = (soup.find_all('article') or 
                   soup.find_all('div', class_=re.compile(r'.*article.*|.*news.*|.*story.*')) or
                   soup.find_all('a', href=True))
        
        seen_titles = set()  # To avoid duplicates
        
        for article in articles:
            try:
                # Extract title and link
                if article.name == 'a':
                    title = article.get_text(strip=True)
                    link = article['href']
                else:
                    title_elem = (article.find('h1') or 
                                article.find('h2') or 
                                article.find('h3') or
                                article.find('a'))
                    
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    link_elem = article.find('a', href=True)
                    link = link_elem['href'] if link_elem else ''
                
                # Make link absolute if relative
                if link and link.startswith('/'):
                    link = 'https://www.elespectador.com' + link
                
                # Extract category
                category_elem = article.find(class_=re.compile(r'.*category.*|.*section.*'))
                category = category_elem.get_text(strip=True) if category_elem else 'General'
                
                # Filter valid news
                if (title and 
                    len(title) > 10 and 
                    title not in seen_titles and
                    not title.lower().startswith(('buscar', 'seguir', 'compartir'))):
                    
                    seen_titles.add(title)
                    news_list.append({
                        'fecha': curr_date,
                        'categoria': category,
                        'titular': title,
                        'enlace': link,
                        'periodico': 'elespectador'
                    })
                    
            except Exception as e:
                logger.warning(f"Error processing article: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error extracting El Espectador news: {str(e)}")
    
    return news_list

def extract_and_parse_info(html_content, curr_date, filename):
    """
    Extract and parse information from HTML content
    @param html_content: HTML content
    @param curr_date: Current date
    @param filename: Source filename
    @return: List of news dictionaries
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Detect newspaper type
        newspaper_type = detect_newspaper_type(filename)
        
        if newspaper_type == 'eltiempo':
            return extract_eltiempo_news(soup, curr_date)
        elif newspaper_type == 'elespectador':
            return extract_elespectador_news(soup, curr_date)
        else:
            logger.warning(f"Unknown newspaper type for {filename}")
            return []
            
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        return []

def save_to_s3_csv(data, s3_key):
    """
    Save data to S3 as CSV
    @param data: List of dictionaries
    @param s3_key: S3 key path
    @return: Success boolean
    """
    try:
        if not data:
            logger.warning("No data to save")
            return False
            
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Convert DataFrame to CSV string
        csv_buffer = df.to_csv(index=False)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=csv_buffer.encode('utf-8'),
            ContentType='text/csv'
        )
        
        logger.info(f"Successfully saved CSV to s3://{S3_BUCKET}/{s3_key}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving CSV to S3: {str(e)}")
        return False

def main():
    """
    Main processing logic
    """
    try:
        # Get current date for partitioning
        curr_date = date.today().strftime("%Y-%m-%d")
        year = date.today().strftime("%Y")
        month = date.today().strftime("%m")
        day = date.today().strftime("%d")
        
        logger.info(f"Starting HTML processing for date: {curr_date}")
        
        # List HTML files in S3 input prefix
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_INPUT_PREFIX
        )
        
        if 'Contents' not in response:
            logger.info("No files found in input prefix")
            return
        
        # Process each HTML file
        for obj in response['Contents']:
            s3_key = obj['Key']
            
            # Skip if not HTML file
            if not s3_key.endswith('.html'):
                continue
                
            logger.info(f"Processing file: {s3_key}")
            
            # Get HTML content
            html_content = get_html_from_s3(s3_key)
            
            if not html_content:
                logger.error(f"Failed to get HTML content for {s3_key}")
                continue
            
            # Extract filename for processing
            filename = s3_key.split('/')[-1].replace('.html', '')
            
            # Extract news data
            news_data = extract_and_parse_info(html_content, curr_date, filename)
            
            if not news_data:
                logger.warning(f"No news data extracted from {filename}")
                continue
            
            # Detect newspaper type for partitioning
            newspaper_type = detect_newspaper_type(filename)
            
            # Create output S3 key with partitions
            output_s3_key = f"{S3_OUTPUT_PREFIX}/periodico={newspaper_type}/year={year}/month={month}/day={day}/{filename}.csv"
            
            # Save to S3
            success = save_to_s3_csv(news_data, output_s3_key)
            
            if success:
                logger.info(f"✅ Successfully processed {filename} ({len(news_data)} articles)")
            else:
                logger.error(f"❌ Failed to save processed data for {filename}")
        
        logger.info("HTML processing job completed")
        
    except Exception as e:
        logger.error(f"Error in main processing logic: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
    job.commit() 