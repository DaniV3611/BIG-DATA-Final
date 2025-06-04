#!/usr/bin/env python3
"""
Deployment script for Glue Jobs and Workflow
Uploads scripts to S3 and sets up the complete workflow
"""

import boto3
import os
import sys
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GlueJobDeployer:

    def __init__(self, s3_bucket, aws_region='us-east-1'):
        """
        Initialize the deployer
        @param s3_bucket: S3 bucket for storing Glue scripts
        @param aws_region: AWS region
        """
        self.s3_bucket = s3_bucket
        self.aws_region = aws_region
        self.s3_client = boto3.client('s3', region_name=aws_region)
        self.glue_client = boto3.client('glue', region_name=aws_region)
        self.sts_client = boto3.client('sts', region_name=aws_region)
        # Script mappings
        self.scripts = {
            'punto_d_glue_migration/extractor_job.py': 'glue-scripts/extractor_job.py',
            'punto_d_glue_migration/processor_job.py': 'glue-scripts/processor_job.py',
            'punto_d_glue_migration/crawler_job.py': 'glue-scripts/crawler_job.py',
            'punto_e_rds_integration/rds_mysql_job.py': 'glue-scripts/rds_mysql_job.py',
            'punto_e_rds_integration/rds_crawler_job.py': 'glue-scripts/rds_crawler_job.py'
        }

    def get_full_iam_role_arn(self, role_name_or_arn):
        """
        Convert role name to full ARN if needed
        @param role_name_or_arn: Role name or ARN
        @return: Full IAM role ARN
        """
        try:
            # If already an ARN, return as is
            if role_name_or_arn.startswith('arn:aws:iam::'):
                return role_name_or_arn
            # Get account ID
            account_id = self.sts_client.get_caller_identity()['Account']
            # Construct full ARN
            full_arn = f'arn:aws:iam::{account_id}:role/{role_name_or_arn}'
            logger.info(f"📝 Converted role name '{role_name_or_arn}' to ARN: {full_arn}")
            return full_arn
        except Exception as e:
            logger.error(f"❌ Error converting role to ARN: {str(e)}")
            return role_name_or_arn

    def check_s3_bucket_exists(self):
        """
        Check if S3 bucket exists
        @return: Success boolean
        """
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
            logger.info(f"✅ S3 bucket {self.s3_bucket} exists")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"❌ S3 bucket {self.s3_bucket} does not exist")
                return False
            else:
                logger.error(f"❌ Error checking S3 bucket: {str(e)}")
                return False

    def upload_script_to_s3(self, local_path, s3_key):
        """
        Upload a script file to S3
        @param local_path: Local file path
        @param s3_key: S3 key path
        @return: Success boolean
        """
        try:
            if not os.path.exists(local_path):
                logger.error(f"❌ Local file does not exist: {local_path}")
                return False
            self.s3_client.upload_file(local_path, self.s3_bucket, s3_key)
            logger.info(f"✅ Uploaded {local_path} to s3://{self.s3_bucket}/{s3_key}")
            return True
        except Exception as e:
            logger.error(f"❌ Error uploading {local_path}: {str(e)}")
            return False

    def upload_all_scripts(self):
        """
        Upload all Glue job scripts to S3
        @return: Success boolean
        """
        logger.info("📤 Uploading Glue job scripts to S3...")
        success_count = 0
        for local_file, s3_key in self.scripts.items():
            success = self.upload_script_to_s3(local_file, s3_key)
            if success:
                success_count += 1
        if success_count == len(self.scripts):
            logger.info(f"✅ Successfully uploaded all {len(self.scripts)} scripts")
            return True
        else:
            logger.error(f"❌ Only uploaded {success_count}/{len(self.scripts)} scripts")
            return False

    def create_glue_jobs(self, iam_role_arn):
        """
        Create Glue jobs using the workflow definition
        @param iam_role_arn: IAM role ARN for Glue jobs
        @return: Success boolean
        """
        try:
            logger.info("🔧 Creating Glue jobs...")
            # Convert role name to full ARN if needed
            full_iam_role_arn = self.get_full_iam_role_arn(iam_role_arn)
            # Update the workflow definition with correct S3 paths
            import workflow_definition
            # Update configuration
            workflow_definition.S3_BUCKET = self.s3_bucket
            workflow_definition.IAM_ROLE_ARN = full_iam_role_arn
            # Update job script locations
            for job_name, job_config in workflow_definition.JOBS_CONFIG.items():
                # Generate correct script name by replacing hyphens with underscores
                base_name = job_name.replace('news-', '').replace('-job', '')
                script_name = base_name.replace('-', '_') + '_job.py'
                job_config['script_location'] = f's3://{self.s3_bucket}/glue-scripts/{script_name}'
                # Update IAM role in job arguments if present
                if '--IAM_ROLE_ARN' in job_config['arguments']:
                    job_config['arguments']['--IAM_ROLE_ARN'] = full_iam_role_arn
            # Create jobs
            success = workflow_definition.main()
            if success:
                logger.info("✅ Successfully created Glue jobs and workflow")
                return True
            else:
                logger.error("❌ Failed to create Glue jobs and workflow")
                return False
        except Exception as e:
            logger.error(f"❌ Error creating Glue jobs: {str(e)}")
            return False

    def validate_deployment(self):
        """
        Validate that all components are deployed correctly
        @return: Success boolean
        """
        logger.info("🔍 Validating deployment...")
        try:
            # Check if scripts exist in S3
            for local_file, s3_key in self.scripts.items():
                try:
                    self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
                    logger.info(f"✅ Script validated: s3://{self.s3_bucket}/{s3_key}")
                except ClientError:
                    logger.error(f"❌ Script not found: s3://{self.s3_bucket}/{s3_key}")
                    return False
            # Check if MySQL driver exists
            try:
                self.s3_client.head_object(Bucket=self.s3_bucket, Key="drivers/mysql-connector-java-8.0.33.jar")
                logger.info(f"✅ MySQL driver validated: s3://{self.s3_bucket}/drivers/mysql-connector-java-8.0.33.jar")
            except ClientError:
                logger.warning(f"Driver not found: s3://{self.s3_bucket}/drivers/mysql-connector-java-8.0.33.jar")
            # Check if RDS connection exists
            try:
                self.glue_client.get_connection(Name="news-rds-connection")
                logger.info("✅ RDS connection validated: news-rds-connection")
            except ClientError:
                logger.error("❌ RDS connection not found: news-rds-connection")
                return False
            # Check if Glue jobs exist
            jobs_to_check = [
                'news-extractor-job',
                'news-processor-job',
                'news-crawler-job',
                'news-rds-mysql-job',
                'news-rds-crawler-job'
            ]
            for job_name in jobs_to_check:
                try:
                    self.glue_client.get_job(JobName=job_name)
                    logger.info(f"✅ Glue job validated: {job_name}")
                except ClientError:
                    logger.error(f"❌ Glue job not found: {job_name}")
                    return False
            # Check if workflow exists
            try:
                self.glue_client.get_workflow(Name='news-processing-workflow')
                logger.info("✅ Workflow validated: news-processing-workflow")
            except ClientError:
                logger.error("❌ Workflow not found: news-processing-workflow")
                return False
            logger.info("✅ All components validated successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error during validation: {str(e)}")
            return False

    def deploy(self, iam_role_arn):
        """
        Complete deployment process
        @param iam_role_arn: IAM role ARN for Glue jobs
        @return: Success boolean
        """
        logger.info("🚀 Starting Glue jobs deployment...")
        # Check S3 bucket
        if not self.check_s3_bucket_exists():
            return False
        # Upload MySQL JDBC driver
        if not self.upload_mysql_driver():
            logger.warning("⚠️ MySQL driver upload failed, but continuing deployment...")
        # Create RDS connection
        if not self.create_rds_connection():
            logger.error("❌ Failed to create RDS connection")
            return False
        # Upload scripts
        if not self.upload_all_scripts():
            return False
        # Create Glue jobs and workflow
        if not self.create_glue_jobs(iam_role_arn):
            return False
        # Validate deployment
        if not self.validate_deployment():
            return False
        logger.info("🎉 Deployment completed successfully!")
        return True

    def upload_mysql_driver(self):
        """
        Download and upload MySQL JDBC driver to S3
        @return: Success boolean
        """
        try:
            import urllib.request
            import tempfile
            import os
            logger.info("📦 Setting up MySQL JDBC driver...")
            # MySQL JDBC driver URL
            driver_url = "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.2.0/mysql-connector-j-8.2.0.jar"
            s3_key = "drivers/mysql-connector-java-8.0.33.jar"
            # Check if driver already exists in S3
            try:
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
                logger.info(f"✅ MySQL driver already exists: s3://{self.s3_bucket}/{s3_key}")
                return True
            except ClientError:
                logger.info("MySQL driver not found in S3, downloading...")
            # Download driver to temp file with proper cleanup
            temp_file = None
            temp_path = None
            try:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jar')
                temp_path = temp_file.name
                temp_file.close()  # Close file handle before downloading
                logger.info(f"Downloading MySQL driver from: {driver_url}")
                urllib.request.urlretrieve(driver_url, temp_path)
                # Upload to S3
                self.s3_client.upload_file(temp_path, self.s3_bucket, s3_key)
                logger.info(f"✅ Uploaded MySQL driver to s3://{self.s3_bucket}/{s3_key}")
                return True
            finally:
                # Clean up temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except Exception as cleanup_error:
                        logger.warning(f"Could not clean up temp file: {cleanup_error}")
        except Exception as e:
            logger.error(f"❌ Error uploading MySQL driver: {str(e)}")
            logger.error("You may need to manually upload the MySQL JDBC driver to S3")
            logger.error("Download from: https://dev.mysql.com/downloads/connector/j/")
            logger.error(f"Upload to: s3://{self.s3_bucket}/drivers/mysql-connector-java-8.0.33.jar")
            return False

    def create_rds_connection(self):
        """
        Create RDS connection in Glue
        @return: Success boolean
        """
        try:
            logger.info("🔗 Creating RDS connection in Glue...")
            connection_name = "news-rds-connection"
            # Check if connection already exists
            try:
                self.glue_client.get_connection(Name=connection_name)
                logger.info(f"✅ Connection {connection_name} already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    logger.info(f"Connection {connection_name} does not exist, creating...")
                else:
                    raise e
            # RDS endpoint - you should update this with your real endpoint
            rds_endpoint = "news2.cevqoilkonik.us-east-1.rds.amazonaws.com"
            rds_database = "news"
            rds_username = "admin"
            rds_password = "123456789"
            # JDBC URL for MySQL
            jdbc_url = f"jdbc:mysql://{rds_endpoint}:3306/{rds_database}"
            # Connection properties
            connection_properties = {
                'Name': connection_name,
                'ConnectionType': 'JDBC',
                'ConnectionProperties': {
                    'JDBC_CONNECTION_URL': jdbc_url,
                    'USERNAME': rds_username,
                    'PASSWORD': rds_password,
                    'JDBC_DRIVER_CLASS_NAME': 'com.mysql.cj.jdbc.Driver'
                },
                'Description': 'Connection to news RDS MySQL database for Glue jobs'
            }
            # Create the connection
            self.glue_client.create_connection(ConnectionInput=connection_properties)
            logger.info(f"✅ Successfully created connection: {connection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating RDS connection: {str(e)}")
            logger.error("Make sure:")
            logger.error("1. RDS instance is running and accessible")
            logger.error("2. Security groups allow Glue connections")
            logger.error("3. RDS credentials are correct")
            return False


def main():
    """
    Main deployment function
    """
    if len(sys.argv) < 3:
        print("Usage: python deploy.py <S3_BUCKET> <IAM_ROLE_NAME_OR_ARN> [AWS_REGION]")
        print("Example: python deploy.py my-glue-bucket LabRole us-east-1")
        print("Example: python deploy.py my-glue-bucket arn:aws:iam::123456789012:role/GlueServiceRole us-east-1")
        sys.exit(1)
    s3_bucket = sys.argv[1]
    iam_role_arn = sys.argv[2]
    aws_region = sys.argv[3] if len(sys.argv) > 3 else 'us-east-1'
    # Initialize deployer
    deployer = GlueJobDeployer(s3_bucket, aws_region)
    # Deploy
    success = deployer.deploy(iam_role_arn)
    if success:
        print("\n✅ Deployment Summary:")
        print(f"   📦 S3 Bucket: {s3_bucket}")
        print("   🔧 Glue Jobs: 5 jobs created")
        print("     - news-extractor-job (Web scraping)")
        print("     - news-processor-job (HTML processing)")
        print("     - news-crawler-job (S3 catalog update)")
        print("     - news-rds-mysql-job (S3 → RDS copy)")
        print("     - news-rds-crawler-job (RDS catalog mapping)")
        print("   🔄 Workflow: news-processing-workflow")
        print("   🔗 RDS Connection: news-rds-connection (created)")
        print("   📅 Schedule: Daily at 6 AM UTC")
        print("   🗄️ RDS Integration: MySQL database mapping")
        print(f"   🌍 Region: {aws_region}")
        print("\n🎯 Next steps:")
        print("   1. ✅ RDS connection created and ready")
        print("   2. Test individual jobs manually in AWS Glue console")
        print("   3. Monitor CloudWatch logs for job execution")
        print("   4. Verify data flows: S3 → Glue Catalog → RDS MySQL")
        print("   5. Query data via Athena (S3 tables) or directly from RDS")
        print("\n🔧 Manual Testing:")
        print("   - news-rds-mysql-job: Should now work without connection errors")
        print("   - news-rds-crawler-job: Will create RDS tables in Glue catalog")
        sys.exit(0)
    else:
        print("\n❌ Deployment failed. Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
