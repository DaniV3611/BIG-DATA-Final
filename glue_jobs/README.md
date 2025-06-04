# AWS Glue Jobs y Workflow - Punto D

Esta implementación migra los Lambda functions de los puntos a), b) y c) a **AWS Glue Jobs** organizados en un **Workflow** como se requiere en el punto d) del proyecto.

## 🔄 Migración de Lambda a Glue Jobs

### Jobs Implementados

#### 1. **Extractor Job** (`extractor_job.py`)
- **Funcionalidad**: Extrae páginas web de periódicos colombianos
- **Migrado de**: `lambdas/extractor/`
- **Características**:
  - Descarga diaria de El Tiempo y El Espectador
  - Almacenamiento en S3 con estructura `headlines/raw/`
  - Manejo de errores y reintentos

#### 2. **Processor Job** (`processor_job.py`)
- **Funcionalidad**: Procesa HTML con BeautifulSoup y extrae datos estructurados
- **Migrado de**: `lambdas/processor/`
- **Características**:
  - Extracción de categoría, titular y enlace
  - Particionado por `periodico/year/month/day`
  - Salida en formato CSV

#### 3. **Crawler Job** (`crawler_job.py`)
- **Funcionalidad**: Ejecuta crawler de Glue para actualizar catálogo
- **Migrado de**: `lambdas/crawler/`
- **Características**:
  - Creación automática de base de datos y crawler
  - Actualización de particiones
  - Métricas y logging detallado

## 🔄 Workflow de Orquestación

```mermaid
graph LR
    A[Daily Trigger<br/>6 AM UTC] --> B[Extractor Job]
    B --> C[Processor Job]
    C --> D[Crawler Job]
    D --> E[Data Available<br/>in Athena]
```

### Triggers Configurados

1. **Start Trigger**: Cron diario (6 AM UTC)
2. **Processor Trigger**: Condicional (después de Extractor)
3. **Crawler Trigger**: Condicional (después de Processor)

## 📁 Estructura de Archivos

```
glue_jobs/
├── extractor_job.py          # Job de extracción web
├── processor_job.py          # Job de procesamiento HTML
├── crawler_job.py            # Job de actualización de catálogo
├── workflow_definition.py    # Definición del workflow
├── deploy.py                 # Script de deployment
├── requirements.txt          # Dependencias
└── README.md                # Esta documentación
```

## 🚀 Deployment

### Prerrequisitos

1. **AWS CLI configurado** con permisos para:
   - AWS Glue (jobs, workflows, crawlers)
   - S3 (lectura/escritura)
   - IAM (para roles de Glue)

2. **S3 Bucket** para almacenar scripts y datos

3. **IAM Role** para Glue con políticas:
   - `AWSGlueServiceRole`
   - `AmazonS3FullAccess`
   - Permisos para CloudWatch logs

### Pasos de Deployment

#### 1. Configurar variables

Editar `workflow_definition.py`:

```python
S3_BUCKET = 'your-bucket-name'  # Tu bucket de S3
IAM_ROLE_ARN = 'arn:aws:iam::account:role/GlueServiceRole'
```

#### 2. Ejecutar deployment

```bash
cd glue_jobs/
python deploy.py YOUR_BUCKET_NAME YOUR_IAM_ROLE_ARN us-east-1
```

**Ejemplo:**
```bash
python deploy.py my-news-pipeline-bucket arn:aws:iam::123456789012:role/GlueServiceRole us-east-1
```

#### 3. Verificar deployment

El script automáticamente:
- ✅ Sube scripts a S3
- ✅ Crea 3 Glue jobs
- ✅ Crea workflow con triggers
- ✅ Valida configuración

## 🎯 Parámetros de Jobs

### Extractor Job
```python
--S3_BUCKET: Bucket para almacenar datos
--S3_PREFIX: Prefijo para archivos raw (default: headlines/raw)
```

### Processor Job
```python
--S3_BUCKET: Bucket de datos
--S3_INPUT_PREFIX: Prefijo de archivos HTML (default: headlines/raw)
--S3_OUTPUT_PREFIX: Prefijo de salida CSV (default: headlines/final)
```

### Crawler Job
```python
--S3_BUCKET: Bucket de datos
--DATABASE_NAME: Base de datos Glue (default: news_headlines_db)
--CRAWLER_NAME: Nombre del crawler (default: news-headlines-crawler)
--IAM_ROLE_ARN: Role ARN para el crawler
--S3_TARGET_PATH: Path objetivo para crawling
```

## 📊 Monitoring y Logs

### CloudWatch Logs

Cada job genera logs en CloudWatch con grupos:
- `/aws-glue/jobs/logs-v2/news-extractor-job`
- `/aws-glue/jobs/logs-v2/news-processor-job`
- `/aws-glue/jobs/logs-v2/news-crawler-job`

### Métricas de Workflow

```python
# Obtener estado del workflow
from workflow_definition import get_workflow_status
status = get_workflow_status()
print(json.dumps(status, indent=2))
```

## 🧪 Testing

### Ejecución Manual

```python
# Ejecutar workflow manualmente
from workflow_definition import start_workflow
start_workflow()
```

### Validación de Datos

1. **Verificar archivos en S3**:
   ```
   s3://bucket/headlines/raw/eltiempo-2024-01-15.html
   s3://bucket/headlines/final/periodico=eltiempo/year=2024/month=01/day=15/
   ```

2. **Consultar en Athena**:
   ```sql
   SELECT * FROM news_headlines_db.headlines_final
   WHERE periodico = 'eltiempo'
   AND year = '2024'
   LIMIT 10;
   ```

## 🔧 Configuración Avanzada

### Modificar Schedule

Editar en `workflow_definition.py`:
```python
'Schedule': 'cron(0 6 * * ? *)',  # Daily at 6 AM UTC
```

### Ajustar Recursos

```python
'MaxCapacity': 2.0,      # DPU capacity
'WorkerType': 'G.1X',    # Worker type
'NumberOfWorkers': 2,    # Number of workers
'Timeout': 60,           # Timeout in minutes
```

### Configurar Job Bookmarks

Los jobs tienen habilitado job bookmarks por defecto para evitar reprocesamiento:
```python
'--job-bookmark-option': 'job-bookmark-enable'
```

## 🆚 Comparación Lambda vs Glue Jobs

| Aspecto | Lambda | Glue Jobs |
|---------|--------|-----------|
| **Duración máxima** | 15 minutos | Sin límite |
| **Memoria** | Hasta 10 GB | Configurable por DPU |
| **Networking** | VPC opcional | VPC integrado |
| **Spark/PySpark** | Manual setup | Nativo |
| **Job Bookmarks** | Manual | Integrado |
| **Workflow** | Step Functions | Glue Workflows |
| **Costo** | Por invocación | Por tiempo DPU |

## ⚡ Ventajas de la Migración

1. **Escalabilidad**: Sin límites de tiempo de ejecución
2. **Orquestación**: Workflow nativo con dependencias
3. **Monitoring**: Integración completa con CloudWatch
4. **Job Bookmarks**: Prevención automática de duplicados
5. **Spark Ready**: Preparado para el punto f) (ML Pipeline)

## 📈 Próximos Pasos

Una vez implementado este workflow:
1. **Punto e)**: Integración con RDS MySQL
2. **Punto f)**: Pipeline de ML con PySpark
3. **Punto g)**: Automatización con EMR

El workflow actual es la base perfecta para estos desarrollos futuros.

## 🐛 Troubleshooting

### Error común: Role permissions
```
Solution: Verificar que el IAM role tenga:
- AWSGlueServiceRole
- AmazonS3FullAccess
- CloudWatch logs permissions
```

### Error: Scripts not found in S3
```
Solution: Ejecutar deploy.py nuevamente o verificar bucket permissions
```

### Job failed: Module not found
```
Solution: Verificar requirements.txt y dependencias de Glue 3.0
``` 