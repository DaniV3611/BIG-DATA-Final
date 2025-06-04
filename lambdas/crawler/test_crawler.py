import unittest
import json
from unittest.mock import patch
from moto import mock_glue
import os
from main import lambda_handler, ensure_crawler_exists, start_crawler, create_crawler
from utils import (
    validate_s3_event,
    extract_partition_info_from_s3_key,
    validate_crawler_config,
    format_partition_values
)
from config import CRAWLER_NAME, DATABASE_NAME, IAM_ROLE_ARN

# Mock environment variables
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['S3_BUCKET'] = 'test-bucket'
os.environ['GLUE_DATABASE'] = 'test_db'
os.environ['GLUE_CRAWLER_NAME'] = 'test-crawler'
os.environ['AWS_ACCOUNT_ID'] = '123456789012'


class TestCrawlerLambda(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.sample_s3_event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': 'test-bucket'},
                        'object': {'key': 'headlines/final/periodico=eltiempo/year=2024/month=1/day=15/data.csv'}
                    }
                }
            ]
        }

        self.manual_event = {
            'test': True,
            'manual_trigger': True
        }

    def test_validate_s3_event_valid(self):
        """Test S3 event validation with valid event"""
        self.assertTrue(validate_s3_event(self.sample_s3_event))

    def test_validate_s3_event_invalid(self):
        """Test S3 event validation with invalid event"""
        invalid_event = {'Records': [{'invalid': 'data'}]}
        self.assertFalse(validate_s3_event(invalid_event))

        no_records_event = {'not_records': []}
        self.assertFalse(validate_s3_event(no_records_event))

    def test_extract_partition_info_from_s3_key(self):
        """Test extraction of partition information from S3 key"""
        s3_key = 'headlines/final/periodico=eltiempo/year=2024/month=1/day=15/data.csv'
        expected = {
            'periodico': 'eltiempo',
            'year': '2024',
            'month': '1',
            'day': '15'
        }

        result = extract_partition_info_from_s3_key(s3_key)
        self.assertEqual(result, expected)

    def test_extract_partition_info_invalid_key(self):
        """Test extraction with invalid S3 key"""
        invalid_key = 'some/random/path/without/partitions'
        result = extract_partition_info_from_s3_key(invalid_key)
        self.assertEqual(result, {})

    def test_format_partition_values(self):
        """Test formatting of partition values"""
        partition_info = {
            'periodico': 'eltiempo',
            'year': 2024,
            'month': 1,
            'day': 15
        }

        expected = ['eltiempo', '2024', '1', '15']
        result = format_partition_values(partition_info)
        self.assertEqual(result, expected)

    def test_validate_crawler_config_valid(self):
        """Test crawler configuration validation with valid config"""
        errors = validate_crawler_config(
            'test-crawler',
            'test-db',
            's3://test-bucket/path',
            'arn:aws:iam::123456789012:role/TestRole'
        )
        self.assertEqual(errors, [])

    def test_validate_crawler_config_invalid(self):
        """Test crawler configuration validation with invalid config"""
        errors = validate_crawler_config(
            '',  # Invalid name
            '',  # Invalid database
            'invalid-path',  # Invalid S3 path
            'invalid-arn'    # Invalid IAM role
        )
        self.assertEqual(len(errors), 4)

    @mock_glue
    def test_create_crawler(self):
        """Test crawler creation"""
        with patch('main.glue_client') as mock_glue:
            mock_glue.create_crawler.return_value = {'ResponseMetadata': {'RequestId': 'test-id'}}

            create_crawler()
            # response = create_crawler()

            mock_glue.create_crawler.assert_called_once()
            call_args = mock_glue.create_crawler.call_args[1]

            self.assertEqual(call_args['Name'], CRAWLER_NAME)
            self.assertEqual(call_args['DatabaseName'], DATABASE_NAME)
            self.assertEqual(call_args['Role'], IAM_ROLE_ARN)
            self.assertIn('S3Targets', call_args['Targets'])

    @mock_glue
    def test_start_crawler_success(self):
        """Test successful crawler start"""
        with patch('main.glue_client') as mock_glue:
            # Mock crawler state as READY
            mock_glue.get_crawler.return_value = {
                'Crawler': {'State': 'READY'}
            }
            mock_glue.start_crawler.return_value = {
                'ResponseMetadata': {'RequestId': 'test-request-id'}
            }

            result = start_crawler()

            mock_glue.get_crawler.assert_called_once_with(Name=CRAWLER_NAME)
            mock_glue.start_crawler.assert_called_once_with(Name=CRAWLER_NAME)
            self.assertEqual(result, 'test-request-id')

    @mock_glue
    def test_start_crawler_already_running(self):
        """Test crawler start when already running"""
        with patch('main.glue_client') as mock_glue:
            # Mock crawler state as RUNNING
            mock_glue.get_crawler.return_value = {
                'Crawler': {'State': 'RUNNING'}
            }

            result = start_crawler()

            mock_glue.get_crawler.assert_called_once_with(Name=CRAWLER_NAME)
            mock_glue.start_crawler.assert_not_called()
            self.assertIsNone(result)

    @mock_glue
    def test_ensure_crawler_exists_already_exists(self):
        """Test ensure crawler exists when crawler already exists"""
        with patch('main.glue_client') as mock_glue:
            mock_glue.get_crawler.return_value = {'Crawler': {'Name': CRAWLER_NAME}}

            ensure_crawler_exists()

            mock_glue.get_crawler.assert_called_once_with(Name=CRAWLER_NAME)
            mock_glue.create_crawler.assert_not_called()

    @mock_glue
    def test_ensure_crawler_exists_not_found(self):
        """Test ensure crawler exists when crawler doesn't exist"""
        with patch('main.glue_client') as mock_glue:
            from botocore.exceptions import ClientError

            # Mock crawler not found
            mock_glue.get_crawler.side_effect = ClientError(
                {'Error': {'Code': 'EntityNotFoundException'}},
                'GetCrawler'
            )
            mock_glue.create_crawler.return_value = {'ResponseMetadata': {'RequestId': 'test-id'}}

            ensure_crawler_exists()

            mock_glue.get_crawler.assert_called_once_with(Name=CRAWLER_NAME)
            mock_glue.create_crawler.assert_called_once()

    @mock_glue
    @patch('main.ensure_crawler_exists')
    @patch('main.start_crawler')
    @patch('main.wait_for_crawler_completion')
    @patch('main.optimize_table_for_athena')
    def test_lambda_handler_success(self, mock_optimize, mock_wait, mock_start, mock_ensure):
        """Test successful lambda handler execution"""
        mock_start.return_value = 'test-run-id'
        mock_wait.return_value = True

        response = lambda_handler(self.sample_s3_event, {})

        self.assertEqual(response['statusCode'], 200)

        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['crawler_name'], CRAWLER_NAME)
        self.assertEqual(body['run_id'], 'test-run-id')

        mock_ensure.assert_called_once()
        mock_start.assert_called_once()
        mock_wait.assert_called_once()
        mock_optimize.assert_called_once()

    @mock_glue
    @patch('main.ensure_crawler_exists')
    def test_lambda_handler_error(self, mock_ensure):
        """Test lambda handler with error"""
        mock_ensure.side_effect = Exception("Test error")

        response = lambda_handler(self.sample_s3_event, {})

        self.assertEqual(response['statusCode'], 500)

        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'error')
        self.assertIn('Test error', body['message'])

    def test_lambda_handler_manual_trigger(self):
        """Test lambda handler with manual trigger"""
        with patch('main.ensure_crawler_exists'), \
             patch('main.start_crawler', return_value='manual-run-id'), \
             patch('main.wait_for_crawler_completion', return_value=True), \
             patch('main.optimize_table_for_athena'):

            response = lambda_handler(self.manual_event, {})

            self.assertEqual(response['statusCode'], 200)
            body = json.loads(response['body'])
            self.assertEqual(body['status'], 'success')


class TestCrawlerUtils(unittest.TestCase):

    def test_format_partition_values_missing_keys(self):
        """Test formatting partition values with missing keys"""
        partition_info = {'periodico': 'eltiempo'}  # Missing year, month, day

        result = format_partition_values(partition_info)
        expected = ['eltiempo', '', '', '']

        self.assertEqual(result, expected)

    def test_extract_partition_info_complex_path(self):
        """Test partition extraction from complex S3 path"""
        s3_key = 'prefix/headlines/final/periodico=elespectador/year=2024/month=12/day=31/subfolder/file.csv'

        result = extract_partition_info_from_s3_key(s3_key)
        expected = {
            'periodico': 'elespectador',
            'year': '2024',
            'month': '12',
            'day': '31'
        }

        self.assertEqual(result, expected)


if __name__ == '__main__':
    # Configure test environment
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

    # Run tests
    unittest.main(verbosity=2)
