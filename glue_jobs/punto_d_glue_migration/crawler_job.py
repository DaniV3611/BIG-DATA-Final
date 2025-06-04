#!/usr/bin/env python3
"""
AWS Glue Job: Catalog Crawler
Executes Glue crawler to update catalog partitions
Migrated from Lambda crawler functionality
"""

import sys
import boto3
import time
import json
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
    'DATABASE_NAME',
    'CRAWLER_NAME',
    'IAM_ROLE_ARN',
    'S3_TARGET_PATH'
])

job.init(args['JOB_NAME'], args)

# Configuration
S3_BUCKET = args.get('S3_BUCKET', 'your-bucket-name')
DATABASE_NAME = args.get('DATABASE_NAME', 'news_headlines_db')
CRAWLER_NAME = args.get('CRAWLER_NAME', 'news-headlines-crawler')
IAM_ROLE_ARN = args.get('IAM_ROLE_ARN', '')
S3_TARGET_PATH = args.get('S3_TARGET_PATH', f's3://{S3_BUCKET}/headlines/final/')

# Initialize AWS clients
glue_client = boto3.client('glue')

def check_glue_database_exists():
    """
    Check if Glue database exists, create if not
    """
    try:
        glue_client.get_database(Name=DATABASE_NAME)
        logger.info(f"Database {DATABASE_NAME} already exists")
        return True
    except glue_client.exceptions.EntityNotFoundException:
        logger.info(f"Database {DATABASE_NAME} doesn't exist, creating it")
        try:
            glue_client.create_database(
                DatabaseInput={
                    'Name': DATABASE_NAME,
                    'Description': 'Database for news headlines data'
                }
            )
            logger.info(f"Successfully created database {DATABASE_NAME}")
            return True
        except Exception as e:
            logger.error(f"Error creating database: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        return False

def ensure_crawler_exists():
    """
    Check if crawler exists, create it if it doesn't
    """
    try:
        glue_client.get_crawler(Name=CRAWLER_NAME)
        logger.info(f"Crawler {CRAWLER_NAME} already exists")
        return True
    except glue_client.exceptions.EntityNotFoundException:
        logger.info(f"Crawler {CRAWLER_NAME} doesn't exist, creating it")
        return create_crawler()
    except Exception as e:
        logger.error(f"Error checking crawler: {str(e)}")
        return False

def create_crawler():
    """
    Create a new Glue crawler
    """
    try:
        crawler_config = {
            'Name': CRAWLER_NAME,
            'Role': IAM_ROLE_ARN,
            'DatabaseName': DATABASE_NAME,
            'Description': 'Crawler for news headlines data partitioned by newspaper/year/month/day',
            'Targets': {
                'S3Targets': [
                    {
                        'Path': S3_TARGET_PATH,
                        'Exclusions': []
                    }
                ]
            },
            'SchemaChangePolicy': {
                'UpdateBehavior': 'UPDATE_IN_DATABASE',
                'DeleteBehavior': 'LOG'
            },
            'RecrawlPolicy': {
                'RecrawlBehavior': 'CRAWL_EVERYTHING'
            },
            'LineageConfiguration': {
                'CrawlerLineageSettings': 'ENABLE'
            },
            'Configuration': json.dumps({
                'Version': 1.0,
                'CrawlerOutput': {
                    'Partitions': {'AddOrUpdateBehavior': 'InheritFromTable'},
                    'Tables': {'AddOrUpdateBehavior': 'MergeNewColumns'}
                },
                'Grouping': {
                    'TableGroupingPolicy': 'CombineCompatibleSchemas'
                }
            })
        }
        glue_client.create_crawler(**crawler_config)
        logger.info(f"Successfully created crawler {CRAWLER_NAME}")
        return True
    except Exception as e:
        logger.error(f"Error creating crawler: {str(e)}")
        return False

def start_crawler():
    """
    Start the Glue crawler
    """
    try:
        # Check crawler state first
        crawler_info = glue_client.get_crawler(Name=CRAWLER_NAME)
        state = crawler_info['Crawler']['State']
        if state == 'RUNNING':
            logger.info(f"Crawler {CRAWLER_NAME} is already running")
            return True
        # Start the crawler
        glue_client.start_crawler(Name=CRAWLER_NAME)
        logger.info(f"Successfully started crawler {CRAWLER_NAME}")
        return True
    except glue_client.exceptions.CrawlerRunningException:
        logger.info(f"Crawler {CRAWLER_NAME} is already running")
        return True
    except Exception as e:
        logger.error(f"Error starting crawler: {str(e)}")
        return False

def wait_for_crawler_completion(max_wait_time=300):
    """
    Wait for crawler to complete
    @param max_wait_time: Maximum time to wait in seconds
    @return: Success boolean
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            crawler_info = glue_client.get_crawler(Name=CRAWLER_NAME)
            state = crawler_info['Crawler']['State']
            if state == 'READY':
                logger.info(f"Crawler {CRAWLER_NAME} completed successfully")
                # Log crawler metrics if available
                last_crawl = crawler_info['Crawler'].get('LastCrawl', {})
                if last_crawl:
                    tables_created = last_crawl.get('MetricsLog', {}).get('TablesCreated', 0)
                    tables_updated = last_crawl.get('MetricsLog', {}).get('TablesUpdated', 0)
                    tables_deleted = last_crawl.get('MetricsLog', {}).get('TablesDeleted', 0)
                    logger.info(
                        f"Crawler metrics - Created: {tables_created}, Updated: {tables_updated}, Deleted: {tables_deleted}"
                    )
                return True
            elif state in ['STOPPING', 'STOPPED']:
                logger.warning(f"Crawler {CRAWLER_NAME} stopped unexpectedly")
                return False
            logger.info(f"Crawler {CRAWLER_NAME} is {state}, waiting...")
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error checking crawler status: {str(e)}")
            return False
    logger.warning(f"Crawler {CRAWLER_NAME} did not complete within {max_wait_time} seconds")
    return False

def get_table_info():
    """
    Get information about tables in the database
    """
    try:
        response = glue_client.get_tables(DatabaseName=DATABASE_NAME)
        tables = response.get('TableList', [])
        logger.info(f"Found {len(tables)} tables in database {DATABASE_NAME}")
        for table in tables:
            table_name = table['Name']
            partition_keys = table.get('PartitionKeys', [])
            storage_descriptor = table.get('StorageDescriptor', {})
            location = storage_descriptor.get('Location', '')
            logger.info(f"Table: {table_name}")
            logger.info(f"  Location: {location}")
            logger.info(f"  Partition Keys: {[pk['Name'] for pk in partition_keys]}")
            # Get partition count
            try:
                partition_response = glue_client.get_partitions(
                    DatabaseName=DATABASE_NAME,
                    TableName=table_name
                )
                partition_count = len(partition_response.get('Partitions', []))
                logger.info(f"  Partitions: {partition_count}")
            except Exception as e:
                logger.warning(f"Could not get partition info for {table_name}: {str(e)}")
        return True
    except Exception as e:
        logger.error(f"Error getting table info: {str(e)}")
        return False

def main():
    """
    Main crawler execution logic
    """
    try:
        logger.info("Starting Glue crawler job")
        # Ensure database exists
        if not check_glue_database_exists():
            logger.error("Failed to ensure database exists")
            return
        # Ensure crawler exists
        if not ensure_crawler_exists():
            logger.error("Failed to ensure crawler exists")
            return
        # Start the crawler
        if not start_crawler():
            logger.error("Failed to start crawler")
            return
        # Wait for crawler completion
        success = wait_for_crawler_completion()
        if success:
            logger.info("✅ Crawler completed successfully")
            # Get updated table information
            get_table_info()
        else:
            logger.error("❌ Crawler did not complete successfully")
        logger.info("Glue crawler job completed")
    except Exception as e:
        logger.error(f"Error in main crawler logic: {str(e)}")
        raise e

if __name__ == "__main__":
    main()
    job.commit() 