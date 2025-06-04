#!/usr/bin/env python3
"""
Debug script for RDS connection issues
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_connection():
    """
    Get detailed connection information
    """
    try:
        glue_client = boto3.client('glue')
        
        logger.info("🔍 Getting detailed connection information...")
        
        response = glue_client.get_connection(Name="news-rds-connection")
        connection = response['Connection']
        
        logger.info("📋 Complete Connection Details:")
        logger.info(f"   Name: {connection['Name']}")
        logger.info(f"   Type: {connection['ConnectionType']}")
        logger.info(f"   Creation Time: {connection.get('CreationTime', 'N/A')}")
        
        # Connection Properties
        props = connection.get('ConnectionProperties', {})
        logger.info("🔧 Connection Properties:")
        for key, value in props.items():
            # Hide password
            display_value = "***HIDDEN***" if 'PASSWORD' in key.upper() else value
            logger.info(f"   {key}: {display_value}")
        
        # Physical Connection Requirements (VPC config)
        physical_req = connection.get('PhysicalConnectionRequirements', {})
        if physical_req:
            logger.info("🌐 Physical Connection Requirements:")
            logger.info(f"   Subnet ID: {physical_req.get('SubnetId', 'N/A')}")
            logger.info(f"   Security Group IDs: {physical_req.get('SecurityGroupIdList', [])}")
            logger.info(f"   Availability Zone: {physical_req.get('AvailabilityZone', 'N/A')}")
        else:
            logger.warning("⚠️ No Physical Connection Requirements found!")
            logger.warning("   This might be the issue - RDS connections typically need VPC config")
        
        # Match Requirements
        match_criteria = connection.get('MatchCriteria', [])
        if match_criteria:
            logger.info(f"🎯 Match Criteria: {match_criteria}")
        
        return connection
        
    except Exception as e:
        logger.error(f"❌ Error getting connection details: {str(e)}")
        return None

def debug_job_configuration():
    """
    Get detailed job configuration
    """
    try:
        glue_client = boto3.client('glue')
        
        logger.info("🔍 Getting job configuration...")
        
        response = glue_client.get_job(JobName="news-rds-mysql-job")
        job = response['Job']
        
        logger.info("📋 Job Connection Configuration:")
        
        # Connections
        connections = job.get('Connections', {})
        logger.info(f"   Connections: {connections}")
        
        # Default Arguments
        args = job.get('DefaultArguments', {})
        logger.info("🔧 Job Arguments (RDS related):")
        for key, value in args.items():
            if any(keyword in key.upper() for keyword in ['RDS', 'JDBC', 'MYSQL', 'DATABASE', 'CONNECTION']):
                display_value = "***HIDDEN***" if 'PASSWORD' in key.upper() else value
                logger.info(f"   {key}: {display_value}")
        
        # Role
        logger.info(f"📋 IAM Role: {job.get('Role', 'N/A')}")
        
        # Glue Version and Worker config
        logger.info(f"📋 Glue Version: {job.get('GlueVersion', 'N/A')}")
        logger.info(f"📋 Worker Type: {job.get('WorkerType', 'N/A')}")
        logger.info(f"📋 Number of Workers: {job.get('NumberOfWorkers', 'N/A')}")
        
        return job
        
    except Exception as e:
        logger.error(f"❌ Error getting job details: {str(e)}")
        return None

def check_rds_accessibility():
    """
    Check if RDS instance is accessible
    """
    try:
        rds_client = boto3.client('rds')
        
        logger.info("🔍 Checking RDS instance...")
        
        # Try to describe DB instances
        response = rds_client.describe_db_instances()
        
        # Look for our instance
        for db in response['DBInstances']:
            if 'news2' in db['DBInstanceIdentifier']:
                logger.info(f"📋 Found RDS Instance: {db['DBInstanceIdentifier']}")
                logger.info(f"   Status: {db['DBInstanceStatus']}")
                logger.info(f"   Engine: {db['Engine']}")
                logger.info(f"   Endpoint: {db['Endpoint']['Address']}")
                logger.info(f"   Port: {db['Endpoint']['Port']}")
                logger.info(f"   VPC ID: {db.get('DbSubnetGroup', {}).get('VpcId', 'N/A')}")
                
                # VPC Security Groups
                vpc_groups = db.get('VpcSecurityGroups', [])
                if vpc_groups:
                    logger.info("🔒 VPC Security Groups:")
                    for group in vpc_groups:
                        logger.info(f"   {group['VpcSecurityGroupId']}: {group['Status']}")
                
                return True
        
        logger.warning("⚠️ RDS instance 'news2' not found")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking RDS: {str(e)}")
        return False

def suggest_fixes(connection, job):
    """
    Suggest potential fixes based on configuration
    """
    logger.info("💡 Potential Solutions:")
    
    # Check if connection has VPC config
    physical_req = connection.get('PhysicalConnectionRequirements', {}) if connection else {}
    
    if not physical_req:
        logger.info("1. ❗ CRITICAL: Add VPC configuration to the connection")
        logger.info("   - RDS connections require subnet and security group configuration")
        logger.info("   - Your RDS instance is in a VPC, but the Glue connection isn't configured for VPC")
        logger.info("   - This is likely the root cause of the connection issue")
    
    logger.info("2. 🔒 Check Security Groups:")
    logger.info("   - Ensure RDS security group allows inbound connections from Glue")
    logger.info("   - Glue uses dynamic IP addresses, consider allowing VPC CIDR range")
    
    logger.info("3. 🌐 Network Configuration:")
    logger.info("   - Verify RDS and Glue are in the same VPC/region")
    logger.info("   - Check subnet routing and NAT Gateway configuration")
    
    logger.info("4. 📋 Alternative approach:")
    logger.info("   - Consider using Glue's built-in JDBC writing without pre-configured connection")
    logger.info("   - Or use direct JDBC connection in the job code")

def main():
    """
    Main debug function
    """
    logger.info("🚀 Starting comprehensive RDS connection debug...")
    
    # Get connection details
    connection = debug_connection()
    
    # Get job details
    job = debug_job_configuration()
    
    # Check RDS accessibility
    check_rds_accessibility()
    
    # Suggest fixes
    suggest_fixes(connection, job)
    
    logger.info("🎯 Debug completed!")

if __name__ == "__main__":
    main() 