import os

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# S3 Configuration
S3_BUCKET = os.getenv('S3_BUCKET', 'final-gizmo')
S3_TARGET_PATH = f's3://{S3_BUCKET}/headlines/final'

# Glue Configuration
DATABASE_NAME = os.getenv('GLUE_DATABASE', 'news_headlines_db')
CRAWLER_NAME = os.getenv('GLUE_CRAWLER_NAME', 'news-headlines-crawler')

# IAM Role for Glue Crawler - Using LabRole that's available
IAM_ROLE_ARN = os.getenv('GLUE_CRAWLER_ROLE_ARN', 
                        f'arn:aws:iam::{os.getenv("AWS_ACCOUNT_ID", "913112112666")}:role/LabRole')

# Lambda Configuration
LAMBDA_TIMEOUT = int(os.getenv('LAMBDA_TIMEOUT', '900'))  # 15 minutes
LAMBDA_MEMORY = int(os.getenv('LAMBDA_MEMORY', '512'))

# Crawler Configuration
CRAWLER_MAX_WAIT_TIME = int(os.getenv('CRAWLER_MAX_WAIT_TIME', '300'))  # 5 minutes
ENABLE_ASYNC_MODE = os.getenv('ENABLE_ASYNC_MODE', 'false').lower() == 'true'

# Athena Configuration
ATHENA_WORKGROUP = os.getenv('ATHENA_WORKGROUP', 'primary')
ATHENA_OUTPUT_LOCATION = f's3://{S3_BUCKET}/athena-results/'

# Table Configuration
TABLE_NAME = 'final_headlines'
TABLE_DESCRIPTION = 'Headlines from El Tiempo and El Espectador'

# Partition Configuration
PARTITION_KEYS = ['periodico', 'year', 'month', 'day']
SUPPORTED_NEWSPAPERS = ['eltiempo', 'elespectador']

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Development/Testing Configuration
IS_DEVELOPMENT = os.getenv('ENVIRONMENT', 'prod').lower() in ['dev', 'development', 'test'] 
