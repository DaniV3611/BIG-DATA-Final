import json
import logging
import boto3
from botocore.exceptions import ClientError
from config import LOG_LEVEL, DATABASE_NAME, TABLE_NAME


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def create_response(status_code, body, headers=None):
    """Create a formatted Lambda response"""
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, default=str)
    }


def validate_s3_event(event):
    """Validate if event is a valid S3 event"""
    try:
        if 'Records' not in event:
            return False

        for record in event['Records']:
            if 's3' not in record or 'bucket' not in record['s3'] or 'object' not in record['s3']:
                return False

        return True
    except Exception:
        return False


def extract_partition_info_from_s3_key(s3_key):
    """
    Extract partition information from S3 key
    Expected format: headlines/final/periodico=xxx/year=xxx/month=xxx/day=xxx/file.csv
    """
    try:
        parts = s3_key.split('/')
        partition_info = {}

        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                partition_info[key] = value

        return partition_info
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not extract partition info from {s3_key}: {str(e)}")
        return {}


def check_glue_database_exists():
    """Check if Glue database exists, create if not"""
    glue_client = boto3.client('glue')
    logger = logging.getLogger(__name__)

    try:
        glue_client.get_database(Name=DATABASE_NAME)
        logger.info(f"Database {DATABASE_NAME} already exists")
        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityNotFoundException':
            logger.info(f"Database {DATABASE_NAME} doesn't exist, creating it")
            try:
                glue_client.create_database(
                    DatabaseInput={
                        'Name': DATABASE_NAME,
                        'Description': 'Database for news headlines data processing'
                    }
                )
                logger.info(f"Database {DATABASE_NAME} created successfully")
                return True
            except Exception as create_error:
                logger.error(f"Error creating database: {str(create_error)}")
                return False
        else:
            logger.error(f"Error checking database: {str(e)}")
            return False


def get_table_info():
    """Get information about the headlines table"""
    glue_client = boto3.client('glue')

    try:
        response = glue_client.get_table(
            DatabaseName=DATABASE_NAME,
            Name=TABLE_NAME
        )
        return response['Table']
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityNotFoundException':
            return None
        else:
            raise e


def list_table_partitions():
    """List all partitions for the headlines table"""
    glue_client = boto3.client('glue')

    try:
        response = glue_client.get_partitions(
            DatabaseName=DATABASE_NAME,
            TableName=TABLE_NAME
        )
        return response['Partitions']
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityNotFoundException':
            return []
        else:
            raise e


def format_partition_values(partition_info):
    """Format partition values for Glue operations"""
    return [
        partition_info.get('periodico', ''),
        str(partition_info.get('year', '')),
        str(partition_info.get('month', '')),
        str(partition_info.get('day', ''))
    ]


def validate_crawler_config(crawler_name, database_name, s3_path, iam_role):
    """Validate crawler configuration parameters"""
    errors = []

    if not crawler_name or not isinstance(crawler_name, str):
        errors.append("Crawler name must be a non-empty string")

    if not database_name or not isinstance(database_name, str):
        errors.append("Database name must be a non-empty string")

    if not s3_path or not s3_path.startswith('s3://'):
        errors.append("S3 path must be a valid S3 URI")

    if not iam_role or not iam_role.startswith('arn:aws:iam::'):
        errors.append("IAM role must be a valid ARN")

    return errors


def get_crawler_metrics(crawler_name):
    """Get metrics and status information for a crawler"""
    glue_client = boto3.client('glue')
    # cloudwatch = boto3.client('cloudwatch')

    try:
        # Get crawler information
        crawler_response = glue_client.get_crawler(Name=crawler_name)
        crawler = crawler_response['Crawler']

        # Get crawler runs
        runs_response = glue_client.get_crawler_metrics(CrawlerNameList=[crawler_name])

        metrics = {
            'crawler_name': crawler_name,
            'state': crawler['State'],
            'creation_time': crawler.get('CreationTime'),
            'last_updated': crawler.get('LastUpdated'),
            'version': crawler.get('Version', 0),
            'database_name': crawler.get('DatabaseName'),
            'table_prefix': crawler.get('TablePrefix', ''),
            'targets': crawler.get('Targets', {}),
            'runs': runs_response.get('CrawlerMetricsList', [])
        }

        return metrics

    except ClientError as e:
        logging.getLogger(__name__).error(f"Error getting crawler metrics: {str(e)}")
        return None


def cleanup_old_partitions(days_to_keep=30):
    """
    Cleanup old partitions (optional utility function)
    This could be used for data retention policies
    """
    from datetime import datetime, timedelta

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    logger = logging.getLogger(__name__)

    try:
        partitions = list_table_partitions()
        old_partitions = []

        for partition in partitions:
            values = partition['Values']
            if len(values) >= 4:  # periodico, year, month, day
                try:
                    year = int(values[1])
                    month = int(values[2])
                    day = int(values[3])
                    partition_date = datetime(year, month, day)

                    if partition_date < cutoff_date:
                        old_partitions.append(partition)
                except ValueError:
                    continue

        logger.info(f"Found {len(old_partitions)} partitions older than {days_to_keep} days")
        return old_partitions

    except Exception as e:
        logger.error(f"Error identifying old partitions: {str(e)}")
        return []
