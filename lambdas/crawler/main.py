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
        
        # Clean incorrect tables from previous runs
        clean_incorrect_tables()
        
        # Recreate table with correct schema
        recreate_table_with_correct_schema()
        
        # Diagnose initial state
        diagnose_table_state()
        
        # Check if crawler exists, create if not
        ensure_crawler_exists()
        
        # Start the crawler
        crawler_run_id = start_crawler()
        
        # Wait for crawler completion (optional - can be async)
        wait_for_crawler_completion()
        
        # Repair partitions to ensure they are visible in Athena
        repair_partitions()
        
        # Diagnose final state
        diagnose_table_state()
        
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
        crawler_info = glue_client.get_crawler(Name=CRAWLER_NAME)
        logger.info(f"Crawler {CRAWLER_NAME} already exists, deleting to recreate with new config")
        
        # Delete existing crawler to recreate with correct configuration
        glue_client.delete_crawler(Name=CRAWLER_NAME)
        logger.info(f"Deleted existing crawler {CRAWLER_NAME}")
        
        # Create new crawler with correct configuration
        create_crawler()
        
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
                'TableGroupingPolicy': 'CombineCompatibleSchemas',
                'TableLevelConfiguration': 4  # Reconocer 4 niveles de partición: periodico/year/month/day
            }
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

def clean_incorrect_tables():
    """Delete incorrect tables created by previous crawler runs"""
    incorrect_table_patterns = [
        'periodico_elespectador',
        'periodico_eltiempo', 
        'run_mysql_node1748997651070_1_part_r_00000',
        'run_mysql_node1748997651070_1_part_r_00001'
    ]
    
    for table_name in incorrect_table_patterns:
        try:
            glue_client.delete_table(
                DatabaseName=DATABASE_NAME,
                Name=table_name
            )
            logger.info(f"Deleted incorrect table: {table_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.info(f"Table {table_name} doesn't exist, skipping")
            else:
                logger.warning(f"Could not delete table {table_name}: {str(e)}")

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

def diagnose_table_state():
    """Diagnose current table state and partitions"""
    try:
        logger.info("=== TABLE DIAGNOSTICS ===")
        
        # Check if table exists
        try:
            table_info = glue_client.get_table(
                DatabaseName=DATABASE_NAME,
                Name='headlines'
            )
            logger.info("✅ Table 'headlines' exists")
            logger.info(f"Table location: {table_info['Table']['StorageDescriptor']['Location']}")
            logger.info(f"Partition keys: {[pk['Name'] for pk in table_info['Table']['PartitionKeys']]}")
        except ClientError:
            logger.error("❌ Table 'headlines' does not exist")
            return
        
        # Check partitions
        try:
            partitions_response = glue_client.get_partitions(
                DatabaseName=DATABASE_NAME,
                TableName='headlines'
            )
            partitions = partitions_response['Partitions']
            logger.info(f"✅ Found {len(partitions)} partitions in Glue catalog")
            
            for i, partition in enumerate(partitions[:5]):  # Show first 5 partitions
                values = partition['Values']
                location = partition['StorageDescriptor']['Location']
                logger.info(f"  Partition {i+1}: periodico={values[0]}, year={values[1]}, month={values[2]}, day={values[3]} -> {location}")
                
        except ClientError as e:
            logger.warning(f"Could not get partitions: {str(e)}")
        
        # Check S3 structure
        try:
            s3_client = boto3.client('s3')
            
            # Parse S3 path correctly
            if S3_TARGET_PATH.startswith('s3://'):
                s3_path_parts = S3_TARGET_PATH[5:].split('/', 1)
                bucket_name = s3_path_parts[0]
                prefix = s3_path_parts[1] if len(s3_path_parts) > 1 else ''
            else:
                raise ValueError(f"Invalid S3 path format: {S3_TARGET_PATH}")
            
            logger.info(f"Checking S3 structure in s3://{bucket_name}/{prefix}")
            
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=10
            )
            
            if 'Contents' in response:
                logger.info(f"✅ Found {len(response['Contents'])} objects in S3")
                for obj in response['Contents'][:5]:
                    logger.info(f"  S3 object: {obj['Key']}")
            else:
                logger.error("❌ No objects found in S3")
                
        except Exception as e:
            logger.error(f"Error checking S3: {str(e)}")
        
        logger.info("=== END DIAGNOSTICS ===")
        
    except Exception as e:
        logger.error(f"Error in diagnostics: {str(e)}")

def repair_partitions():
    """Repair partitions using MSCK REPAIR TABLE equivalent"""
    try:
        logger.info("Starting partition repair process")
        
        # Get all partitions from S3
        s3_client = boto3.client('s3')
        
        # Parse S3 path correctly
        if S3_TARGET_PATH.startswith('s3://'):
            s3_path_parts = S3_TARGET_PATH[5:].split('/', 1)
            bucket_name = s3_path_parts[0]
            prefix = s3_path_parts[1] if len(s3_path_parts) > 1 else ''
        else:
            raise ValueError(f"Invalid S3 path format: {S3_TARGET_PATH}")
        
        logger.info(f"Scanning S3 bucket: {bucket_name}, prefix: {prefix}")
        
        paginator = s3_client.get_paginator('list_objects_v2')
        partitions_found = set()
        
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Look for partition structure: periodico=X/year=Y/month=Z/day=W/
                    if '/periodico=' in key and '/year=' in key and '/month=' in key and '/day=' in key:
                        # Extract partition values
                        parts = key.split('/')
                        partition_info = {}
                        for part in parts:
                            if '=' in part:
                                k, v = part.split('=', 1)
                                partition_info[k] = v
                        
                        if all(k in partition_info for k in ['periodico', 'year', 'month', 'day']):
                            partition_tuple = (
                                partition_info['periodico'],
                                partition_info['year'], 
                                partition_info['month'],
                                partition_info['day']
                            )
                            partitions_found.add(partition_tuple)
        
        logger.info(f"Found {len(partitions_found)} partitions in S3")
        
        # Add partitions to Glue table
        partitions_added = 0
        for periodico, year, month, day in partitions_found:
            try:
                partition_location = f"{S3_TARGET_PATH}/periodico={periodico}/year={year}/month={month}/day={day}/"
                
                glue_client.create_partition(
                    DatabaseName=DATABASE_NAME,
                    TableName='headlines',
                    PartitionInput={
                        'Values': [periodico, year, month, day],
                        'StorageDescriptor': {
                            'Columns': [
                                {'Name': 'fecha', 'Type': 'string'},
                                {'Name': 'categoria', 'Type': 'string'},
                                {'Name': 'titular', 'Type': 'string'},
                                {'Name': 'enlace', 'Type': 'string'}
                            ],
                            'Location': partition_location,
                            'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                            'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                            'SerdeInfo': {
                                'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
                                'Parameters': {
                                    'field.delim': ',',
                                    'skip.header.line.count': '1'
                                }
                            }
                        }
                    }
                )
                partitions_added += 1
                logger.info(f"Added partition: {periodico}/{year}/{month}/{day}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'AlreadyExistsException':
                    logger.info(f"Partition already exists: {periodico}/{year}/{month}/{day}")
                else:
                    logger.warning(f"Could not add partition {periodico}/{year}/{month}/{day}: {str(e)}")
        
        logger.info(f"Partition repair completed. Added {partitions_added} new partitions")
        return True
        
    except Exception as e:
        logger.error(f"Error repairing partitions: {str(e)}")
        return False 