#!/usr/bin/env python3
"""
Test script to verify RDS connection and job configuration
"""

import boto3
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_rds_connection():
    """
    Test if the RDS connection exists and is properly configured
    """
    try:
        glue_client = boto3.client('glue')
        
        # Test connection exists
        logger.info("🔍 Testing RDS connection...")
        
        connection_name = "news-rds-connection"
        
        try:
            response = glue_client.get_connection(Name=connection_name)
            connection = response['Connection']
            
            logger.info(f"✅ Connection {connection_name} exists")
            logger.info(f"   Type: {connection['ConnectionType']}")
            logger.info(f"   Properties: {list(connection['ConnectionProperties'].keys())}")
            
            # Check JDBC URL
            jdbc_url = connection['ConnectionProperties'].get('JDBC_CONNECTION_URL', 'N/A')
            logger.info(f"   JDBC URL: {jdbc_url}")
            
            return True
            
        except glue_client.exceptions.EntityNotFoundException:
            logger.error(f"❌ Connection {connection_name} not found!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing connection: {str(e)}")
        return False

def test_job_configuration():
    """
    Test if the RDS MySQL job is properly configured
    """
    try:
        glue_client = boto3.client('glue')
        
        logger.info("🔍 Testing job configuration...")
        
        job_name = "news-rds-mysql-job"
        
        try:
            response = glue_client.get_job(JobName=job_name)
            job = response['Job']
            
            logger.info(f"✅ Job {job_name} exists")
            
            # Check connections
            connections = job.get('Connections', {}).get('Connections', [])
            if 'news-rds-connection' in connections:
                logger.info(f"✅ Job has RDS connection configured: {connections}")
            else:
                logger.error(f"❌ Job missing RDS connection. Current connections: {connections}")
                return False
            
            # Check extra JARs
            extra_jars = job.get('DefaultArguments', {}).get('--extra-jars', '')
            if 'mysql-connector' in extra_jars:
                logger.info(f"✅ MySQL driver configured: {extra_jars}")
            else:
                logger.warning(f"⚠️ MySQL driver may not be configured: {extra_jars}")
            
            # Check job arguments
            args = job.get('DefaultArguments', {})
            rds_args = [arg for arg in args.keys() if 'RDS' in arg]
            logger.info(f"✅ RDS arguments: {rds_args}")
            
            return True
            
        except glue_client.exceptions.EntityNotFoundException:
            logger.error(f"❌ Job {job_name} not found!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing job: {str(e)}")
        return False

def test_mysql_driver():
    """
    Test if MySQL driver exists in S3
    """
    try:
        if len(sys.argv) < 2:
            logger.warning("⚠️ S3 bucket not provided, skipping driver test")
            return True
            
        s3_bucket = sys.argv[1]
        s3_client = boto3.client('s3')
        
        logger.info("🔍 Testing MySQL driver in S3...")
        
        driver_key = "drivers/mysql-connector-java-8.0.33.jar"
        
        try:
            s3_client.head_object(Bucket=s3_bucket, Key=driver_key)
            logger.info(f"✅ MySQL driver exists: s3://{s3_bucket}/{driver_key}")
            return True
            
        except s3_client.exceptions.NoSuchKey:
            logger.error(f"❌ MySQL driver not found: s3://{s3_bucket}/{driver_key}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing MySQL driver: {str(e)}")
        return False

def main():
    """
    Run all tests
    """
    logger.info("🚀 Starting RDS connection tests...")
    
    all_tests_passed = True
    
    # Test 1: RDS Connection
    if not test_rds_connection():
        all_tests_passed = False
    
    # Test 2: Job Configuration  
    if not test_job_configuration():
        all_tests_passed = False
    
    # Test 3: MySQL Driver
    if not test_mysql_driver():
        all_tests_passed = False
    
    if all_tests_passed:
        logger.info("🎉 All tests passed! RDS connection should work correctly.")
        logger.info("💡 You can now test the 'news-rds-mysql-job' manually in AWS Glue console.")
    else:
        logger.error("❌ Some tests failed. Please fix the issues before running the job.")
        
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 