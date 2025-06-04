#!/usr/bin/env python3
"""
Testing script for Glue Jobs and Workflow
Validates individual jobs and complete workflow execution
"""

import boto3
import time
import logging
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GlueJobTester:
    def __init__(self, aws_region='us-east-1'):
        """
        Initialize the tester
        @param aws_region: AWS region
        """
        self.aws_region = aws_region
        self.glue_client = boto3.client('glue', region_name=aws_region)
        self.s3_client = boto3.client('s3', region_name=aws_region)

        # Job names
        self.jobs = {
            'extractor': 'news-extractor-job',
            'processor': 'news-processor-job',
            'crawler': 'news-crawler-job'
        }

        self.workflow_name = 'news-processing-workflow'

    def test_job_exists(self, job_name):
        """
        Test if a Glue job exists
        @param job_name: Name of the job
        @return: Success boolean
        """
        try:
            response = self.glue_client.get_job(JobName=job_name)
            logger.info(f"✅ Job exists: {job_name}")

            # Log job details
            job = response['Job']
            logger.info(f"   Role: {job['Role']}")
            logger.info(f"   Glue Version: {job['GlueVersion']}")
            logger.info(f"   Max Capacity: {job.get('MaxCapacity', 'N/A')}")
            logger.info(f"   Worker Type: {job.get('WorkerType', 'N/A')}")

            return True

        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.error(f"❌ Job not found: {job_name}")
            else:
                logger.error(f"❌ Error checking job {job_name}: {str(e)}")
            return False

    def run_job(self, job_name, arguments=None):
        """
        Run a Glue job
        @param job_name: Name of the job
        @param arguments: Job arguments
        @return: Job run ID or None
        """
        try:
            if arguments is None:
                arguments = {}

            response = self.glue_client.start_job_run(
                JobName=job_name,
                Arguments=arguments
            )

            job_run_id = response['JobRunId']
            logger.info(f"🚀 Started job {job_name} with run ID: {job_run_id}")
            return job_run_id

        except Exception as e:
            logger.error(f"❌ Error starting job {job_name}: {str(e)}")
            return None

    def wait_for_job_completion(self, job_name, job_run_id, max_wait_time=1800):
        """
        Wait for job completion
        @param job_name: Name of the job
        @param job_run_id: Job run ID
        @param max_wait_time: Maximum time to wait in seconds
        @return: Success boolean
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                response = self.glue_client.get_job_run(
                    JobName=job_name,
                    RunId=job_run_id
                )

                job_run = response['JobRun']
                state = job_run['JobRunState']

                if state == 'SUCCEEDED':
                    logger.info(f"✅ Job {job_name} completed successfully")

                    # Log execution metrics
                    execution_time = job_run.get('ExecutionTime', 0)
                    dpu_seconds = execution_time * job_run.get('MaxCapacity', 1)

                    logger.info(f"   Execution time: {execution_time} seconds")
                    logger.info(f"   DPU-seconds: {dpu_seconds}")

                    return True

                elif state == 'FAILED':
                    logger.error(f"❌ Job {job_name} failed")

                    # Log error details
                    if 'ErrorMessage' in job_run:
                        logger.error(f"   Error: {job_run['ErrorMessage']}")

                    return False

                elif state in ['STOPPED', 'STOPPING']:
                    logger.warning(f"⚠️ Job {job_name} was stopped")
                    return False

                logger.info(f"⏳ Job {job_name} is {state}, waiting...")
                time.sleep(30)

            except Exception as e:
                logger.error(f"❌ Error checking job status: {str(e)}")
                return False

        logger.warning(f"⏰ Job {job_name} did not complete within {max_wait_time} seconds")
        return False

    def test_individual_job(self, job_type, arguments=None):
        """
        Test an individual job
        @param job_type: Type of job (extractor, processor, crawler)
        @param arguments: Job arguments
        @return: Success boolean
        """
        job_name = self.jobs.get(job_type)
        if not job_name:
            logger.error(f"❌ Unknown job type: {job_type}")
            return False

        logger.info(f"🧪 Testing job: {job_name}")
        
        # Check if job exists
        if not self.test_job_exists(job_name):
            return False

        # Run the job
        job_run_id = self.run_job(job_name, arguments)
        if not job_run_id:
            return False

        # Wait for completion
        success = self.wait_for_job_completion(job_name, job_run_id)

        if success:
            logger.info(f"✅ Job {job_name} test completed successfully")
        else:
            logger.error(f"❌ Job {job_name} test failed")

        return success

    def test_workflow_exists(self):
        """
        Test if the workflow exists
        @return: Success boolean
        """
        try:
            response = self.glue_client.get_workflow(Name=self.workflow_name)
            logger.info(f"✅ Workflow exists: {self.workflow_name}")

            # Log workflow details
            workflow = response['Workflow']
            logger.info(f"   Description: {workflow.get('Description', 'N/A')}")
            logger.info(f"   Created: {workflow.get('CreatedOn', 'N/A')}")

            return True

        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                logger.error(f"❌ Workflow not found: {self.workflow_name}")
            else:
                logger.error(f"❌ Error checking workflow: {str(e)}")
            return False

    def start_workflow(self):
        """
        Start the workflow
        @return: Workflow run ID or None
        """
        try:
            response = self.glue_client.start_workflow_run(Name=self.workflow_name)
            run_id = response['RunId']
            logger.info(f"🚀 Started workflow with run ID: {run_id}")
            return run_id

        except Exception as e:
            logger.error(f"❌ Error starting workflow: {str(e)}")
            return None

    def wait_for_workflow_completion(self, run_id, max_wait_time=3600):
        """
        Wait for workflow completion
        @param run_id: Workflow run ID
        @param max_wait_time: Maximum time to wait in seconds
        @return: Success boolean
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                response = self.glue_client.get_workflow_run(
                    Name=self.workflow_name,
                    RunId=run_id
                )
                
                workflow_run = response['Run']
                status = workflow_run['Status']

                if status == 'COMPLETED':
                    logger.info("✅ Workflow completed successfully")

                    # Log node executions
                    node_details = workflow_run.get('Graph', {}).get('Nodes', [])
                    for node in node_details:
                        node_type = node.get('Type', 'Unknown')
                        node_name = node.get('Name', 'Unknown')
                        logger.info(f"   {node_type}: {node_name}")

                    return True

                elif status == 'FAILED':
                    logger.error(f"❌ Workflow failed")
                    return False

                elif status in ['STOPPED', 'STOPPING']:
                    logger.warning("⚠️ Workflow was stopped")
                    return False

                logger.info(f"⏳ Workflow is {status}, waiting...")
                time.sleep(60)

            except Exception as e:
                logger.error(f"❌ Error checking workflow status: {str(e)}")
                return False

        logger.warning(f"⏰ Workflow did not complete within {max_wait_time} seconds")
        return False

    def test_workflow(self):
        """
        Test the complete workflow
        @return: Success boolean
        """
        logger.info(f"🧪 Testing workflow: {self.workflow_name}")
 
        # Check if workflow exists
        if not self.test_workflow_exists():
            return False

        # Start the workflow
        run_id = self.start_workflow()
        if not run_id:
            return False

        # Wait for completion
        success = self.wait_for_workflow_completion(run_id)

        if success:
            logger.info("✅ Workflow test completed successfully")
        else:
            logger.error("❌ Workflow test failed")

        return success

    def validate_s3_output(self, s3_bucket, date_str=None):
        """
        Validate S3 output structure
        @param s3_bucket: S3 bucket name
        @param date_str: Date string (YYYY-MM-DD), defaults to today
        @return: Success boolean
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        year, month, day = date_str.split('-')

        logger.info(f"🔍 Validating S3 output for date: {date_str}")

        try:
            # Check raw files
            raw_prefix = 'headlines/raw/'
            raw_response = self.s3_client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=raw_prefix
            )

            raw_files = [obj['Key'] for obj in raw_response.get('Contents', [])]
            expected_raw_files = [
                f'{raw_prefix}eltiempo-{date_str}.html',
                f'{raw_prefix}elespectador-{date_str}.html'
            ]

            for expected_file in expected_raw_files:
                if expected_file in raw_files:
                    logger.info(f"✅ Found raw file: {expected_file}")
                else:
                    logger.warning(f"⚠️ Missing raw file: {expected_file}")

            # Check processed files
            final_prefixes = [
                f'headlines/final/periodico=eltiempo/year={year}/month={month}/day={day}/',
                f'headlines/final/periodico=elespectador/year={year}/month={month}/day={day}/'
            ]

            for prefix in final_prefixes:
                final_response = self.s3_client.list_objects_v2(
                    Bucket=s3_bucket,
                    Prefix=prefix
                )

                final_files = final_response.get('Contents', [])
                if final_files:
                    logger.info(f"✅ Found processed files in: {prefix}")
                    for file_obj in final_files:
                        logger.info(f"   - {file_obj['Key']} ({file_obj['Size']} bytes)")
                else:
                    logger.warning(f"⚠️ No processed files in: {prefix}")

            return True

        except Exception as e:
            logger.error(f"❌ Error validating S3 output: {str(e)}")
            return False

    def run_all_tests(self, s3_bucket=None):
        """
        Run all tests
        @param s3_bucket: S3 bucket for validation (optional)
        @return: Success boolean
        """
        logger.info("🚀 Running comprehensive Glue Jobs test suite")

        test_results = {}

        # Test individual jobs exist
        for job_type, job_name in self.jobs.items():
            test_results[f"{job_type}_exists"] = self.test_job_exists(job_name)

        # Test workflow exists
        test_results["workflow_exists"] = self.test_workflow_exists()

        # Test workflow execution (only if all components exist)
        if all(test_results.values()):
            test_results["workflow_execution"] = self.test_workflow()

            # Validate S3 output if bucket provided
            if s3_bucket and test_results["workflow_execution"]:
                test_results["s3_validation"] = self.validate_s3_output(s3_bucket)

        # Summary
        logger.info("\n📊 Test Results Summary:")
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name}: {status}")

        overall_success = all(test_results.values())

        if overall_success:
            logger.info("\n🎉 All tests passed! Glue Jobs and Workflow are working correctly.")
        else:
            logger.error("\n❌ Some tests failed. Check the logs above for details.")

        return overall_success


def main():
    """
    Main testing function
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python test_jobs.py <test_type> [s3_bucket] [aws_region]")
        print("\nTest types:")
        print("  all        - Run all tests")
        print("  extractor  - Test extractor job only")
        print("  processor  - Test processor job only") 
        print("  crawler    - Test crawler job only")
        print("  workflow   - Test workflow only")
        print("  validate   - Validate S3 output only (requires s3_bucket)")
        print("\nExamples:")
        print("  python test_jobs.py all my-bucket us-east-1")
        print("  python test_jobs.py extractor")
        print("  python test_jobs.py validate my-bucket")
        sys.exit(1)

    test_type = sys.argv[1]
    s3_bucket = sys.argv[2] if len(sys.argv) > 2 else None
    aws_region = sys.argv[3] if len(sys.argv) > 3 else 'us-east-1'

    # Initialize tester
    tester = GlueJobTester(aws_region)

    # Run specified test
    if test_type == 'all':
        success = tester.run_all_tests(s3_bucket)
    elif test_type in ['extractor', 'processor', 'crawler']:
        success = tester.test_individual_job(test_type)
    elif test_type == 'workflow':
        success = tester.test_workflow()
    elif test_type == 'validate':
        if not s3_bucket:
            print("❌ S3 bucket required for validation test")
            sys.exit(1)
        success = tester.validate_s3_output(s3_bucket)
    else:
        print(f"❌ Unknown test type: {test_type}")
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
