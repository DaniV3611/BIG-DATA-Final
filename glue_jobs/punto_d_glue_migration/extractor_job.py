#!/usr/bin/env python3
"""
AWS Glue Job: Web Extractor
Extracts daily news from Colombian newspapers and saves to S3
Migrated from Lambda extractor functionality
"""

import sys
import requests
import boto3
from datetime import date
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
    'S3_PREFIX'
])

job.init(args['JOB_NAME'], args)

# Configuration
S3_BUCKET = args.get('S3_BUCKET', 'your-bucket-name')
S3_PREFIX = args.get('S3_PREFIX', 'headlines/raw')

# Initialize S3 client
s3_client = boto3.client('s3')


def download_webpage(url, timeout=30):
    """
    Download webpage content
    @param url: URL to download
    @param timeout: Request timeout
    @return: HTML content or None
    """
    try:
        headers = {
            'User-Agent': """
            Mozilla/5.0 
            (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36
            """
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Error downloading {url}: {str(e)}")
        return None


def upload_to_s3(content, s3_key):
    """
    Upload content to S3
    @param content: Content to upload
    @param s3_key: S3 key path
    @return: Success boolean
    """
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=content.encode('utf-8'),
            ContentType='text/html'
        )
        logger.info(f"Successfully uploaded to s3://{S3_BUCKET}/{s3_key}")
        return True
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        return False


def main():
    """
    Main extraction logic
    """
    try:
        # Get current date
        curr_date = date.today().strftime("%Y-%m-%d")

        # Define newspapers and their URLs
        newspapers = {
            'eltiempo': 'https://www.eltiempo.com/',
            'elespectador': 'https://www.elespectador.com/'
        }

        logger.info(f"Starting web extraction for date: {curr_date}")

        for newspaper, url in newspapers.items():
            logger.info(f"Downloading {newspaper} from {url}")
            
            # Download webpage
            content = download_webpage(url)
    
            if content:
                # Create S3 key with the required structure
                s3_key = f"{S3_PREFIX}/{newspaper}-{curr_date}.html"

                # Upload to S3
                success = upload_to_s3(content, s3_key)

                if success:
                    logger.info(f"✅ Successfully processed {newspaper}")
                else:
                    logger.error(f"❌ Failed to upload {newspaper}")
            else:
                logger.error(f"❌ Failed to download content from {newspaper}")

        logger.info("Web extraction job completed")

    except Exception as e:
        logger.error(f"Error in main extraction logic: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
    job.commit()
