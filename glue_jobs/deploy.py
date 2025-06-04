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
            'extractor_job.py': 'glue-scripts/extractor_job.py',
            'processor_job.py': 'glue-scripts/processor_job.py',
            'crawler_job.py': 'glue-scripts/crawler_job.py'
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
                script_name = job_name.replace('news-', '').replace('-job', '_job.py')
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
            
            # Check if Glue jobs exist
            jobs_to_check = ['news-extractor-job', 'news-processor-job', 'news-crawler-job']
            
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
        print(f"   🔧 Glue Jobs: 3 jobs created")
        print(f"   🔄 Workflow: news-processing-workflow")
        print(f"   📅 Schedule: Daily at 6 AM UTC")
        print(f"   🌍 Region: {aws_region}")
        print("\n🎯 Next steps:")
        print("   1. Test the workflow manually in AWS Glue console")
        print("   2. Monitor CloudWatch logs for job execution")
        print("   3. Verify data is being created in S3 and Glue catalog")
        sys.exit(0)
    else:
        print("\n❌ Deployment failed. Check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 