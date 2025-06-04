import json
import boto3
import logging
from botocore.exceptions import ClientError
from config import CRAWLER_NAME, DATABASE_NAME, S3_TARGET_PATH, IAM_ROLE_ARN
from utils import setup_logging, create_response, check_glue_database_exists

# Setup logging
logger = setup_logging()

# Initialize AWS clients
glue_client = boto3.client('glue')

def lambda_handler(event, context):
    """
    Lambda function to execute Glue crawler for updating partitions
    This function is triggered when new data arrives in S3
    """
    try:
        logger.info("Starting Glue crawler execution")
        
        # Extract S3 event information if triggered by S3
        if 'Records' in event:
            process_s3_event(event)
        
        # Ensure database exists
        check_glue_database_exists()
        
        # Recreate table with correct schema
        recreate_table_with_correct_schema()
        
        # Check if crawler exists, create if not
        ensure_crawler_exists()
        
        # Start the crawler
        crawler_run_id = start_crawler()
        
        # Wait for crawler completion (optional - can be async)
        wait_for_crawler_completion()
        
        response_data = {
            'crawler_name': CRAWLER_NAME,
            'status': 'success',
            'message': 'Crawler executed successfully and partitions updated',
            'run_id': crawler_run_id
        }
        
        logger.info(f"Crawler execution completed successfully: {response_data}")
        return create_response(200, response_data)
        
    except Exception as e:
        logger.error(f"Error executing crawler: {str(e)}")
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })

def process_s3_event(event):
    """Process S3 event to understand what triggered the crawler"""
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        logger.info(f"Processing S3 event for object: s3://{bucket}/{key}")

def ensure_crawler_exists():
    """Check if crawler exists, create it if it doesn't"""
    try:
        # Check if crawler exists
        glue_client.get_crawler(Name=CRAWLER_NAME)
        logger.info(f"Crawler {CRAWLER_NAME} already exists")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityNotFoundException':
            logger.info(f"Crawler {CRAWLER_NAME} doesn't exist, creating it")
            create_crawler()
        else:
            raise e

def create_crawler():
    """Create a new Glue crawler"""
    crawler_config = {
        'Name': CRAWLER_NAME,
        'Role': IAM_ROLE_ARN,
        'DatabaseName': DATABASE_NAME,
        'Description': 'Crawler for news headlines data partitioned by periodico/year/month/day',
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
            },
            'projection.enabled': 'false'
        })
    }
    
    response = glue_client.create_crawler(**crawler_config)
    logger.info(f"Crawler {CRAWLER_NAME} created successfully")
    return response

def start_crawler():
    """Start the Glue crawler"""
    try:
        # Check crawler state first
        crawler_info = glue_client.get_crawler(Name=CRAWLER_NAME)
        state = crawler_info['Crawler']['State']
        
        if state == 'RUNNING':
            logger.info(f"Crawler {CRAWLER_NAME} is already running")
            return None
            
        # Start the crawler
        response = glue_client.start_crawler(Name=CRAWLER_NAME)
        logger.info(f"Started crawler {CRAWLER_NAME}")
        return response.get('ResponseMetadata', {}).get('RequestId')
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'CrawlerRunningException':
            logger.info(f"Crawler {CRAWLER_NAME} is already running")
            return None
        else:
            raise e

def wait_for_crawler_completion(max_wait_time=300):
    """
    Wait for crawler to complete (optional)
    In production, you might want to make this async or use Step Functions
    """
    import time
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        crawler_info = glue_client.get_crawler(Name=CRAWLER_NAME)
        state = crawler_info['Crawler']['State']
        
        if state == 'READY':
            logger.info(f"Crawler {CRAWLER_NAME} completed successfully")
            return True
        elif state in ['STOPPING', 'STOPPED']:
            logger.warning(f"Crawler {CRAWLER_NAME} stopped unexpectedly")
            return False
            
        logger.info(f"Crawler {CRAWLER_NAME} is {state}, waiting...")
        time.sleep(10)
    
    logger.warning(f"Crawler {CRAWLER_NAME} did not complete within {max_wait_time} seconds")
    return False

def get_crawler_status():
    """Get current crawler status"""
    try:
        response = glue_client.get_crawler(Name=CRAWLER_NAME)
        return {
            'name': CRAWLER_NAME,
            'state': response['Crawler']['State'],
            'last_crawl': response['Crawler'].get('LastCrawl', {}),
            'creation_time': response['Crawler']['CreationTime'].isoformat() if 'CreationTime' in response['Crawler'] else None
        }
    except ClientError:
        return {'name': CRAWLER_NAME, 'state': 'NOT_FOUND'}

# Handler for manual testing
def test_handler(event, context):
    """Test handler for manual invocation"""
    test_event = {
        'test': True,
        'manual_trigger': True
    }
    return lambda_handler(test_event, context)

def recreate_table_with_correct_schema():
    """Recreate table with correct schema by dropping and creating it again"""
    try:
        logger.info("Attempting to recreate table with correct schema")
        
        # Try to delete existing table
        try:
            glue_client.delete_table(
                DatabaseName=DATABASE_NAME,
                Name='headlines'
            )
            logger.info("Existing table deleted")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.info("Table doesn't exist, creating new one")
            else:
                logger.warning(f"Could not delete existing table: {str(e)}")
        
        # Create table with correct schema
        table_input = {
            'Name': 'headlines',
            'Description': 'News headlines from Colombian newspapers',
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'fecha', 'Type': 'string', 'Comment': 'Publication date'},
                    {'Name': 'categoria', 'Type': 'string', 'Comment': 'News category'},
                    {'Name': 'titular', 'Type': 'string', 'Comment': 'News headline'},
                    {'Name': 'enlace', 'Type': 'string', 'Comment': 'News link'}
                ],
                'Location': S3_TARGET_PATH,
                'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                'SerdeInfo': {
                    'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
                    'Parameters': {
                        'field.delim': ',',
                        'skip.header.line.count': '1'
                    }
                }
            },
            'PartitionKeys': [
                {'Name': 'periodico', 'Type': 'string', 'Comment': 'Newspaper name'},
                {'Name': 'year', 'Type': 'string', 'Comment': 'Year'},
                {'Name': 'month', 'Type': 'string', 'Comment': 'Month'},
                {'Name': 'day', 'Type': 'string', 'Comment': 'Day'}
            ],
            'TableType': 'EXTERNAL_TABLE',
            'Parameters': {
                'projection.enabled': 'true',
                'projection.periodico.type': 'enum',
                'projection.periodico.values': 'eltiempo,elespectador',
                'projection.year.type': 'integer',
                'projection.year.range': '2020,2030',
                'projection.month.type': 'integer',
                'projection.month.range': '1,12',
                'projection.day.type': 'integer',
                'projection.day.range': '1,31',
                'storage.location.template': f'{S3_TARGET_PATH}/periodico=${{periodico}}/year=${{year}}/month=${{month}}/day=${{day}}',
                'classification': 'csv',
                'delimiter': ',',
                'skip.header.line.count': '1',
                'compressionType': 'none',
                'typeOfData': 'file'
            }
        }
        
        glue_client.create_table(
            DatabaseName=DATABASE_NAME,
            TableInput=table_input
        )
        
        logger.info("Table recreated successfully with correct schema")
        return True
        
    except Exception as e:
        logger.error(f"Error recreating table: {str(e)}")
        return False 