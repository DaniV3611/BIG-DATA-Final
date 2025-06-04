#!/usr/bin/env python3
"""
AWS Glue Workflow Definition
Creates and manages the workflow for the news processing pipeline
"""

import boto3
import json
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Glue client
glue_client = boto3.client('glue')

# Configuration
WORKFLOW_NAME = 'news-processing-workflow'
DATABASE_NAME = 'news_headlines_db'
S3_BUCKET = 'your-bucket-name'  # Replace with your actual bucket name
IAM_ROLE_ARN = 'arn:aws:iam::your-account:role/GlueServiceRole'  # Replace with your IAM role

# Job definitions
JOBS_CONFIG = {
    'news-extractor-job': {
        'script_location': 's3://your-bucket-name/glue-scripts/extractor_job.py',
        'description': 'Extract news from Colombian newspapers',
        'arguments': {
            '--S3_BUCKET': S3_BUCKET,
            '--S3_PREFIX': 'headlines/raw'
        }
    },
    'news-processor-job': {
        'script_location': 's3://your-bucket-name/glue-scripts/processor_job.py',
        'description': 'Process HTML files and extract structured news data',
        'arguments': {
            '--S3_BUCKET': S3_BUCKET,
            '--S3_INPUT_PREFIX': 'headlines/raw',
            '--S3_OUTPUT_PREFIX': 'headlines/final'
        }
    },
    'news-crawler-job': {
        'script_location': 's3://your-bucket-name/glue-scripts/crawler_job.py',
        'description': 'Run crawler to update Glue catalog',
        'arguments': {
            '--S3_BUCKET': S3_BUCKET,
            '--DATABASE_NAME': DATABASE_NAME,
            '--CRAWLER_NAME': 'news-headlines-crawler',
            '--IAM_ROLE_ARN': IAM_ROLE_ARN,
            '--S3_TARGET_PATH': f's3://{S3_BUCKET}/headlines/final/'
        }
    }
}

def create_or_update_job(job_name, job_config):
    """
    Create or update a Glue job
    @param job_name: Name of the job
    @param job_config: Job configuration
    @return: Success boolean
    """
    try:
        job_definition = {
            'Name': job_name,
            'Description': job_config['description'],
            'Role': IAM_ROLE_ARN,
            'Command': {
                'Name': 'glueetl',
                'ScriptLocation': job_config['script_location'],
                'PythonVersion': '3'
            },
            'DefaultArguments': {
                '--job-bookmark-option': 'job-bookmark-enable',
                '--enable-metrics': 'true',
                '--enable-continuous-cloudwatch-log': 'true',
                '--TempDir': f's3://{S3_BUCKET}/temp/',
                **job_config['arguments']
            },
            'MaxRetries': 1,
            'Timeout': 60,  # 1 hour timeout
            'GlueVersion': '3.0',
            'WorkerType': 'G.1X',
            'NumberOfWorkers': 2
        }
        
        try:
            # Try to get existing job
            glue_client.get_job(JobName=job_name)
            
            # Job exists, update it
            glue_client.update_job(
                JobName=job_name,
                JobUpdate=job_definition
            )
            logger.info(f"Updated job: {job_name}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                # Job doesn't exist, create it
                glue_client.create_job(**job_definition)
                logger.info(f"Created job: {job_name}")
            else:
                raise e
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating/updating job {job_name}: {str(e)}")
        return False

def create_workflow():
    """
    Create the Glue workflow
    @return: Success boolean
    """
    try:
        workflow_definition = {
            'Name': WORKFLOW_NAME,
            'Description': 'News processing pipeline workflow - Extract, Process, and Catalog',
            'DefaultRunProperties': {
                'S3_BUCKET': S3_BUCKET,
                'DATABASE_NAME': DATABASE_NAME
            }
        }
        
        try:
            # Try to get existing workflow
            glue_client.get_workflow(Name=WORKFLOW_NAME)
            logger.info(f"Workflow {WORKFLOW_NAME} already exists")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                # Workflow doesn't exist, create it
                glue_client.create_workflow(**workflow_definition)
                logger.info(f"Created workflow: {WORKFLOW_NAME}")
            else:
                raise e
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating workflow: {str(e)}")
        return False

def create_triggers():
    """
    Create triggers to orchestrate the workflow
    @return: Success boolean
    """
    try:
        # Trigger to start the workflow (scheduled daily)
        start_trigger = {
            'Name': f'{WORKFLOW_NAME}-start-trigger',
            'WorkflowName': WORKFLOW_NAME,
            'Type': 'SCHEDULED',
            'Description': 'Daily trigger to start news processing workflow',
            'Schedule': 'cron(0 6 * * ? *)',  # Daily at 6 AM UTC
            'Actions': [
                {
                    'JobName': 'news-extractor-job'
                }
            ]
        }
        
        # Trigger to start processor after extractor completes
        processor_trigger = {
            'Name': f'{WORKFLOW_NAME}-processor-trigger',
            'WorkflowName': WORKFLOW_NAME,
            'Type': 'CONDITIONAL',
            'Description': 'Start processor job after extractor completes successfully',
            'Predicate': {
                'Logical': 'AND',
                'Conditions': [
                    {
                        'LogicalOperator': 'EQUALS',
                        'JobName': 'news-extractor-job',
                        'State': 'SUCCEEDED'
                    }
                ]
            },
            'Actions': [
                {
                    'JobName': 'news-processor-job'
                }
            ]
        }
        
        # Trigger to start crawler after processor completes
        crawler_trigger = {
            'Name': f'{WORKFLOW_NAME}-crawler-trigger',
            'WorkflowName': WORKFLOW_NAME,
            'Type': 'CONDITIONAL',
            'Description': 'Start crawler job after processor completes successfully',
            'Predicate': {
                'Logical': 'AND',
                'Conditions': [
                    {
                        'LogicalOperator': 'EQUALS',
                        'JobName': 'news-processor-job',
                        'State': 'SUCCEEDED'
                    }
                ]
            },
            'Actions': [
                {
                    'JobName': 'news-crawler-job'
                }
            ]
        }
        
        # Create triggers
        triggers = [start_trigger, processor_trigger, crawler_trigger]
        
        for trigger in triggers:
            try:
                # Try to get existing trigger
                glue_client.get_trigger(Name=trigger['Name'])
                
                # Trigger exists, update it
                glue_client.update_trigger(
                    Name=trigger['Name'],
                    TriggerUpdate=trigger
                )
                logger.info(f"Updated trigger: {trigger['Name']}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityNotFoundException':
                    # Trigger doesn't exist, create it
                    glue_client.create_trigger(**trigger)
                    logger.info(f"Created trigger: {trigger['Name']}")
                else:
                    raise e
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating triggers: {str(e)}")
        return False

def start_workflow():
    """
    Start the workflow manually (for testing)
    @return: Success boolean
    """
    try:
        response = glue_client.start_workflow_run(Name=WORKFLOW_NAME)
        run_id = response['RunId']
        logger.info(f"Started workflow run: {run_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error starting workflow: {str(e)}")
        return False

def get_workflow_status():
    """
    Get workflow status and run information
    @return: Workflow status information
    """
    try:
        # Get workflow info
        workflow_response = glue_client.get_workflow(Name=WORKFLOW_NAME)
        workflow = workflow_response['Workflow']
        
        # Get workflow runs
        runs_response = glue_client.get_workflow_runs(Name=WORKFLOW_NAME)
        runs = runs_response['Runs']
        
        status_info = {
            'workflow_name': WORKFLOW_NAME,
            'state': workflow.get('LastRun', {}).get('Status', 'NOT_STARTED'),
            'last_run_id': workflow.get('LastRun', {}).get('WorkflowRunId', 'None'),
            'total_runs': len(runs),
            'recent_runs': []
        }
        
        # Get details of recent runs
        for run in runs[:5]:  # Last 5 runs
            run_info = {
                'run_id': run['WorkflowRunId'],
                'status': run['Status'],
                'started_on': run.get('StartedOn', '').isoformat() if run.get('StartedOn') else '',
                'completed_on': run.get('CompletedOn', '').isoformat() if run.get('CompletedOn') else ''
            }
            status_info['recent_runs'].append(run_info)
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {str(e)}")
        return None

def main():
    """
    Main function to set up the complete workflow
    """
    try:
        logger.info("Setting up news processing workflow...")
        
        # Create all jobs
        logger.info("Creating/updating Glue jobs...")
        for job_name, job_config in JOBS_CONFIG.items():
            success = create_or_update_job(job_name, job_config)
            if not success:
                logger.error(f"Failed to create job: {job_name}")
                return False
        
        # Create workflow
        logger.info("Creating workflow...")
        if not create_workflow():
            logger.error("Failed to create workflow")
            return False
        
        # Create triggers
        logger.info("Creating triggers...")
        if not create_triggers():
            logger.error("Failed to create triggers")
            return False
        
        logger.info("✅ Workflow setup completed successfully!")
        
        # Display status
        status = get_workflow_status()
        if status:
            logger.info(f"Workflow Status: {json.dumps(status, indent=2)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in main setup: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1) 