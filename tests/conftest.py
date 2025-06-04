"""
Configuration and fixtures for pytest testing suite.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
import os
import tempfile
import json
from datetime import date


@pytest.fixture
def sample_html_content():
    """Fixture con contenido HTML de ejemplo para testing"""
    return """
    <html>
        <head><title>El Tiempo - Noticias</title></head>
        <body>
            <article>
                <a href="/politica/noticia1">Noticia de Política</a>
                <span class="categoria">Política</span>
            </article>
            <article>
                <a href="/deportes/noticia2">Noticia de Deportes</a>
                <span class="categoria">Deportes</span>
            </article>
        </body>
    </html>
    """


@pytest.fixture
def sample_csv_data():
    """Fixture con datos CSV de ejemplo"""
    return pd.DataFrame({
        'categoria': ['Política', 'Deportes', 'Economía'],
        'titular': ['Noticia política importante', 'Partido de fútbol', 'Inflación aumenta'],
        'enlace': ['/politica/noticia1', '/deportes/noticia2', '/economia/noticia3'],
        'fecha': ['2024-01-15', '2024-01-15', '2024-01-15'],
        'periodico': ['eltiempo', 'eltiempo', 'eltiempo']
    })


@pytest.fixture
def mock_s3_client():
    """Mock S3 client para testing"""
    mock_s3 = Mock()
    mock_s3.create_bucket.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
    mock_s3.put_object.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
    mock_s3.get_object.return_value = {'Body': Mock(read=Mock(return_value=b'test content'))}
    mock_s3.list_objects_v2.return_value = {'Contents': [{'Key': 'test-file.txt'}]}
    return mock_s3


@pytest.fixture
def mock_glue_client():
    """Mock Glue client para testing"""
    mock_glue = Mock()
    mock_glue.start_crawler.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}
    mock_glue.create_job.return_value = {'Name': 'test-job'}
    return mock_glue


@pytest.fixture
def temp_directory():
    """Temporary directory para testing de archivos"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_lambda_event():
    """Evento Lambda de ejemplo para S3"""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "headlines/raw/eltiempo-2024-01-15.html"}
                }
            }
        ]
    }


@pytest.fixture
def current_date_str():
    """Fecha actual como string para testing"""
    return date.today().strftime("%Y-%m-%d")


@pytest.fixture
def mock_spark_session():
    """Mock Spark session para testing EMR scripts"""
    mock_spark = Mock()
    mock_spark.read.option.return_value.csv.return_value = Mock()
    mock_spark.createDataFrame.return_value = Mock()
    return mock_spark


@pytest.fixture
def sample_news_data():
    """Datos de noticias de ejemplo para ML testing"""
    return [
        {"categoria": "Política", "titular": "Nueva ley aprobada en el congreso", "enlace": "/politica/ley"},
        {"categoria": "Deportes", "titular": "Colombia gana partido de fútbol", "enlace": "/deportes/futbol"},
        {"categoria": "Economía", "titular": "Dólar sube en el mercado", "enlace": "/economia/dolar"},
    ]


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup automático para cada test"""
    # Set environment variables for testing
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['TESTING'] = 'true'
    
    yield
    
    # Cleanup
    test_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'TESTING']
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]


@pytest.fixture
def mock_mysql_connection():
    """Mock MySQL connection para testing RDS"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn 