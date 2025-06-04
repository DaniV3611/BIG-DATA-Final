#!/usr/bin/env python3
"""
AWS Glue Job: RDS MySQL Crawler
Creates and runs a Glue crawler to map RDS MySQL tables to Glue Data Catalog
Part of point e) implementation
"""

import sys
import boto3
import time
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
    'IAM_ROLE_ARN',
    'RDS_ENDPOINT',
    'RDS_DATABASE',
    'RDS_USERNAME',
    'RDS_PASSWORD',
    'TARGET_DATABASE',
    'CRAWLER_NAME'
])

job.init(args['JOB_NAME'], args)

# Configuration
IAM_ROLE_ARN = args.get('IAM_ROLE_ARN')
RDS_ENDPOINT = args.get('RDS_ENDPOINT', 'news2.cevqoilkonik.us-east-1.rds.amazonaws.com')
RDS_DATABASE = args.get('RDS_DATABASE', 'news')
RDS_USERNAME = args.get('RDS_USERNAME', 'admin')
RDS_PASSWORD = args.get('RDS_PASSWORD', '123456789')
TARGET_DATABASE = args.get('TARGET_DATABASE', 'news_rds_db')
CRAWLER_NAME = args.get('CRAWLER_NAME', 'news-rds-crawler')

# Initialize Glue client
glue_client = boto3.client('glue')


def create_rds_connection():
    """
    Verify that the Glue connection for RDS MySQL exists
    @return: Connection name or None
    """
    try:
        connection_name = "news-rds-connection"
        
        # Check if connection exists (should be created by deployment)
        try:
            glue_client.get_connection(Name=connection_name)
            logger.info("✅ Connection {} exists and is ready to use".format(connection_name))
            return connection_name
        except glue_client.exceptions.EntityNotFoundException:
            logger.error(f"❌ Connection {connection_name} does not exist!")
            logger.error("This connection should be created during deployment.")
            logger.error("Please run the deployment script to create all required resources.")
            return None
  
    except Exception as e:
        logger.error(f"❌ Error checking RDS connection: {str(e)}")
        return None


def create_target_database():
    """
    Create target database in Glue Data Catalog for RDS tables
    @return: Success boolean
    """
    try:
        # Check if database already exists
        try:
            glue_client.get_database(Name=TARGET_DATABASE)
            logger.info(f"✅ Database {TARGET_DATABASE} already exists")
            return True
        except glue_client.exceptions.EntityNotFoundException:
            logger.info(f"Database {TARGET_DATABASE} does not exist, creating...")

        # Create database
        database_input = {
            'Name': TARGET_DATABASE,
            'Description': 'Database for news RDS MySQL tables mapped to Glue catalog'
        }

        glue_client.create_database(DatabaseInput=database_input)
        logger.info(f"✅ Successfully created database: {TARGET_DATABASE}")

        return True

    except Exception as e:
        logger.error(f"❌ Error creating database: {str(e)}")
        return False


def create_rds_crawler(connection_name):
    """
    Create a Glue crawler for RDS MySQL
    @param connection_name: Name of the Glue connection
    @return: Success boolean
    """
    try:
        # Check if crawler already exists
        try:
            glue_client.get_crawler(Name=CRAWLER_NAME)
            logger.info(f"✅ Crawler {CRAWLER_NAME} already exists")
            return True
        except glue_client.exceptions.EntityNotFoundException:
            logger.info(f"Crawler {CRAWLER_NAME} does not exist, creating...")

        # Crawler configuration
        crawler_config = {
            'Name': CRAWLER_NAME,
            'Role': IAM_ROLE_ARN,
            'DatabaseName': TARGET_DATABASE,
            'Description': 'Crawler for news RDS MySQL tables',
            'Targets': {
                'JdbcTargets': [
                    {
                        'ConnectionName': connection_name,
                        'Path': f"{RDS_DATABASE}/%"  # Crawl all tables in the database
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
            }
        }

        # Create the crawler
        glue_client.create_crawler(**crawler_config)
        logger.info(f"✅ Successfully created crawler: {CRAWLER_NAME}")

        return True

    except Exception as e:
        logger.error(f"❌ Error creating crawler: {str(e)}")
        return False


def run_crawler():
    """
    Run the RDS crawler
    @return: Success boolean
    """
    try:
        logger.info(f"🚀 Starting crawler: {CRAWLER_NAME}")

        # Start the crawler
        glue_client.start_crawler(Name=CRAWLER_NAME)

        # Wait for crawler to complete
        max_wait_time = 600  # 10 minutes
        wait_interval = 30   # 30 seconds
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            # Get crawler status
            response = glue_client.get_crawler(Name=CRAWLER_NAME)
            state = response['Crawler']['State']

            logger.info(f"Crawler state: {state} (elapsed: {elapsed_time}s)")

            if state == 'READY':
                # Get crawler metrics
                last_crawl = response['Crawler'].get('LastCrawl', {})
                if last_crawl:
                    logger.info("✅ Crawler completed successfully")
                    logger.info(f"Tables created/updated: {last_crawl.get('TablesCreated', 0)}")
                    logger.info(f"Tables updated: {last_crawl.get('TablesUpdated', 0)}")
                    logger.info(f"Tables deleted: {last_crawl.get('TablesDeleted', 0)}")

                    if last_crawl.get('Status') == 'SUCCEEDED':
                        return True
                    else:
                        logger.error(f"❌ Crawler failed: {last_crawl.get('ErrorMessage', 'Unknown error')}")
                        return False
                else:
                    logger.warning("⚠️ No crawl history found")
                    return False

            elif state == 'RUNNING':
                # Continue waiting
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                continue

            else:
                logger.error(f"❌ Unexpected crawler state: {state}")
                return False

        logger.error(f"❌ Crawler timed out after {max_wait_time} seconds")
        return False

    except Exception as e:
        logger.error(f"❌ Error running crawler: {str(e)}")
        return False


def verify_catalog_tables():
    """
    Verify that tables were created in the Glue catalog
    @return: Success boolean
    """
    try:
        logger.info(f"🔍 Verifying tables in database: {TARGET_DATABASE}")
        
        # Get tables in the database
        response = glue_client.get_tables(DatabaseName=TARGET_DATABASE)
        tables = response.get('TableList', [])
        
        if not tables:
            logger.warning("⚠️ No tables found in target database")
            return False

        logger.info(f"✅ Found {len(tables)} tables in catalog:")

        for table in tables:
            table_name = table['Name']
            column_count = len(table.get('StorageDescriptor', {}).get('Columns', []))

            logger.info(f"  📋 Table: {table_name} ({column_count} columns)")

            # Show column details for main table
            if table_name == 'noticias':
                columns = table.get('StorageDescriptor', {}).get('Columns', [])
                logger.info(f"    Columns in {table_name}:")
                for col in columns:
                    logger.info(f"      - {col['Name']}: {col['Type']}")

        return True

    except Exception as e:
        logger.error(f"❌ Error verifying catalog tables: {str(e)}")
        return False


def main():
    """
    Main processing logic
    """
    try:
        logger.info("🚀 Starting RDS MySQL Crawler Job")
        logger.info(f"RDS Endpoint: {RDS_ENDPOINT}")
        logger.info(f"Database: {RDS_DATABASE}")
        logger.info(f"Target Catalog Database: {TARGET_DATABASE}")
        logger.info(f"Crawler Name: {CRAWLER_NAME}")

        # Step 1: Create target database in Glue catalog
        logger.info("📊 Creating target database in Glue catalog...")
        if not create_target_database():
            logger.error("❌ Failed to create target database")
            return

        # Step 2: Create RDS connection
        logger.info("🔗 Creating RDS connection...")
        connection_name = create_rds_connection()
        if not connection_name:
            logger.error("❌ Failed to create RDS connection")
            return

        # Step 3: Create RDS crawler
        logger.info("🕷️ Creating RDS crawler...")
        if not create_rds_crawler(connection_name):
            logger.error("❌ Failed to create crawler")
            return

        # Step 4: Run the crawler
        logger.info("▶️ Running RDS crawler...")
        if not run_crawler():
            logger.error("❌ Crawler execution failed")
            return

        # Step 5: Verify catalog tables
        logger.info("✅ Verifying catalog tables...")
        if not verify_catalog_tables():
            logger.error("❌ Table verification failed")
            return

        logger.info("✅ RDS MySQL Crawler Job completed successfully")
        logger.info("🎉 RDS tables are now available in Glue Data Catalog")
        logger.info(f"📋 You can now query tables in database: {TARGET_DATABASE}")

    except Exception as e:
        logger.error(f"❌ Error in main processing logic: {str(e)}")
        raise e


if __name__ == "__main__":
    main()
    job.commit()
