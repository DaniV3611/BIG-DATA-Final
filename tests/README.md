# 🧪 Suite de Testing - Big Data Pipeline

Este directorio contiene una suite completa de testing para el proyecto de Big Data Pipeline, cubriendo todos los componentes desde Lambdas hasta EMR y ML.

## 📋 Índice

- [Estructura de Tests](#estructura-de-tests)
- [Instalación](#instalación)
- [Ejecución de Tests](#ejecución-de-tests)
- [Tipos de Tests](#tipos-de-tests)
- [Coverage](#coverage)
- [CI/CD](#cicd)
- [Troubleshooting](#troubleshooting)

## 📁 Estructura de Tests

```
tests/
├── __init__.py                 # Paquete de tests
├── conftest.py                 # Configuración y fixtures de pytest
├── pytest.ini                 # Configuración de pytest
├── requirements-test.txt       # Dependencias de testing
├── run_tests.py               # Script principal de ejecución
├── run_tests.bat              # Script para Windows
├── README.md                  # Esta documentación
│
├── test_lambdas.py            # Tests para funciones Lambda
├── test_glue_jobs.py          # Tests para Glue Jobs
├── test_emr_scripts.py        # Tests para scripts EMR
├── test_integration.py        # Tests de integración
└── test_utils.py              # Tests de utilidades
```

## 🚀 Instalación

### 1. Instalar Dependencias

```bash
# Opción 1: Usar el script (recomendado)
python tests/run_tests.py --install-deps

# Opción 2: Instalar manualmente
pip install -r tests/requirements-test.txt
```

### 2. Verificar Instalación

```bash
pytest --version
```

## 🎯 Ejecución de Tests

### Script Interactivo (Recomendado)

**Windows:**

```cmd
tests\run_tests.bat
```

**Linux/Mac:**

```bash
python tests/run_tests.py
```

### Comandos Directos

#### Tests Rápidos (Recomendado para desarrollo)

```bash
python tests/run_tests.py --fast
```

#### Todos los Tests

```bash
python tests/run_tests.py --all
```

#### Tests por Componente

```bash
# Lambda functions
python tests/run_tests.py --lambda

# Glue Jobs
python tests/run_tests.py --glue

# EMR Scripts
python tests/run_tests.py --emr

# Integración
python tests/run_tests.py --integration
```

#### Tests con Coverage

```bash
python tests/run_tests.py --coverage
```

#### Tests en Paralelo

```bash
python tests/run_tests.py --parallel
```

#### Tests Específicos

```bash
python tests/run_tests.py -k "test_extractor"
```

### Comandos Pytest Directo

```bash
# Ejecutar todos los tests
pytest tests/

# Tests específicos
pytest tests/test_lambdas.py

# Con marcadores
pytest -m "lambda"
pytest -m "not slow"

# Con coverage
pytest --cov=lambdas --cov=glue_jobs --cov=emr_scripts
```

## 🏷️ Tipos de Tests

### Por Categoría

#### 🔧 **Unitarios**

- Tests de funciones individuales
- Mocking de dependencias externas
- Ejecución rápida

```bash
pytest -m unit
```

#### 🔗 **Integración**

- Tests de flujo completo
- Interacción entre componentes
- Uso de servicios AWS mockeados

```bash
pytest -m integration
```

#### ⚡ **Performance**

- Tests de rendimiento
- Métricas de tiempo de ejecución
- Optimización de recursos

```bash
pytest -m slow
```

### Por Componente

#### λ **Lambda Tests**

- `test_lambdas.py`
- Extractor, Processor, Crawler, EMR Manager
- Mock de eventos S3 y respuestas AWS

#### 🔧 **Glue Tests**

- `test_glue_jobs.py`
- Jobs de extracción, procesamiento, crawler
- Workflow y deployment
- RDS integration

#### ⚡ **EMR Tests**

- `test_emr_scripts.py`
- Classification pipeline
- Spark ML components
- Performance optimization

#### 🔄 **Integration Tests**

- `test_integration.py`
- Pipeline completo end-to-end
- Data quality validation
- Error handling

#### 🛠️ **Utility Tests**

- `test_utils.py`
- AWS utilities
- Data processing helpers
- Error handling

## 📊 Coverage

### Generar Reporte

```bash
python tests/run_tests.py --coverage
```

### Ver Reporte HTML

```bash
# El reporte se genera en:
tests/htmlcov/index.html
```

### Configuración de Coverage

- **Umbral mínimo:** 70%
- **Directorios cubiertos:** `lambdas/`, `glue_jobs/`, `emr_scripts/`
- **Reportes:** HTML, XML, Terminal

### Ejemplos de Coverage

```bash
# Coverage específico
pytest --cov=lambdas tests/test_lambdas.py

# Coverage con reporte detallado
pytest --cov=glue_jobs --cov-report=term-missing

# Fallar si coverage < 70%
pytest --cov-fail-under=70
```

## 🏗️ Fixtures Disponibles

### AWS Mocking

- `mock_s3_bucket`: Bucket S3 temporal
- `mock_glue_client`: Cliente Glue mockeado
- `mock_mysql_connection`: Conexión MySQL mockeada

### Data Fixtures

- `sample_html_content`: HTML de prueba
- `sample_csv_data`: DataFrame de prueba
- `sample_news_data`: Datos de noticias
- `sample_lambda_event`: Evento Lambda S3

### Utility Fixtures

- `temp_directory`: Directorio temporal
- `current_date_str`: Fecha actual
- `mock_spark_session`: Sesión Spark mockeada

## 🔧 Configuración

### Variables de Entorno

```bash
# Automáticamente configuradas por el script
export TESTING=true
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
```

### Marcadores Pytest

```ini
# En pytest.ini
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    aws: AWS service tests
    lambda: Lambda function tests
    glue: Glue job tests
    emr: EMR script tests
    s3: S3 operation tests
    rds: RDS operation tests
```

## 🚀 CI/CD Integration

### GitHub Actions (próximo paso)

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.9"
      - name: Install dependencies
        run: python tests/run_tests.py --install-deps
      - name: Run tests
        run: python tests/run_tests.py --all
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: Run tests
        entry: python tests/run_tests.py --fast
        language: system
        pass_filenames: false
```

## 🔍 Calidad de Código

### Ejecutar Checks de Calidad

```bash
python tests/run_tests.py --quality
```

### Herramientas Incluidas

- **flake8**: Linting PEP8
- **black**: Formateo de código
- **isort**: Ordenamiento de imports
- **mypy**: Verificación de tipos
- **bandit**: Análisis de seguridad

## 🐛 Troubleshooting

### Errores Comunes

#### 1. **ImportError: No module named 'moto'**

```bash
pip install -r tests/requirements-test.txt
```

#### 2. **AWS Credentials Error**

```bash
# Las credenciales se configuran automáticamente para testing
# Si persiste el error, ejecutar:
python tests/run_tests.py --clean
```

#### 3. **Spark Context Error**

```bash
# Instalar findspark
pip install findspark pyspark
```

#### 4. **Coverage Too Low**

```bash
# Ver qué líneas no están cubiertas
pytest --cov-report=term-missing
```

### Debug de Tests

```bash
# Ejecutar con más verbosidad
pytest -vvv tests/test_specific.py

# Parar en el primer fallo
pytest -x

# Ejecutar solo tests fallidos
pytest --lf

# Debug con pdb
pytest --pdb
```

### Logs de Testing

```bash
# Ver logs durante tests
pytest -s tests/

# Configurar nivel de logging
pytest --log-cli-level=DEBUG
```

## 📈 Métricas y Reportes

### Métricas Disponibles

- **Coverage:** Porcentaje de código cubierto
- **Execution Time:** Tiempo de ejecución por test
- **Success Rate:** Tasa de éxito de tests
- **Performance:** Métricas de rendimiento

### Comandos de Reporte

```bash
# Reporte de tiempo de ejecución
pytest --durations=10

# Reporte de tests más lentos
pytest --durations=0

# Reporte HTML completo
pytest --html=tests/report.html --self-contained-html
```

## 🤝 Contribución

### Agregar Nuevos Tests

1. **Crear archivo de test:** `test_nuevo_componente.py`
2. **Usar fixtures existentes:** `conftest.py`
3. **Agregar marcadores apropiados:** `@pytest.mark.unit`
4. **Documentar el test:** Docstring descriptivo
5. **Ejecutar y verificar:** `pytest tests/test_nuevo_componente.py`

### Estructura de Test

```python
import pytest
from unittest.mock import Mock, patch

class TestNuevoComponente:
    """Tests para el nuevo componente"""

    @pytest.mark.unit
    def test_funcion_basica(self, sample_data):
        """Test básico con fixture"""
        # Arrange
        input_data = sample_data

        # Act
        result = funcion_a_testear(input_data)

        # Assert
        assert result is not None
        assert len(result) > 0

    @pytest.mark.integration
    @patch('boto3.client')
    def test_integracion_aws(self, mock_boto, mock_s3_bucket):
        """Test de integración con AWS"""
        # Test implementation
        pass
```

---

## 📞 Soporte

Si tienes problemas con los tests:

1. **Revisar logs:** `pytest --log-cli-level=DEBUG`
2. **Limpiar artefactos:** `python tests/run_tests.py --clean`
3. **Reinstalar dependencias:** `python tests/run_tests.py --install-deps`
4. **Ejecutar tests específicos:** `python tests/run_tests.py -k "test_name"`

¡Happy Testing! 🎉
