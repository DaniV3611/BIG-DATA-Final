# Glue Crawler Lambda Function

Este Lambda ejecuta un crawler de AWS Glue para actualizar automáticamente las particiones en el catálogo de Glue, permitiendo que los datos procesados sean consultables a través de AWS Athena.

## Funcionalidad

- **Ejecuta crawler de Glue**: Crea y ejecuta un crawler que descubre automáticamente nuevas particiones
- **Actualiza catálogo**: Mantiene actualizado el catálogo de datos de Glue
- **Optimiza para Athena**: Configura la tabla con partition projection para mejorar el rendimiento en Athena
- **Gestión automática**: Crea la base de datos y crawler si no existen

## Estructura de Datos

El crawler está configurado para procesar datos con la siguiente estructura de particiones:

```
s3://bucket/headlines/final/
├── periodico=eltiempo/
│   ├── year=2024/
│   │   ├── month=1/
│   │   │   ├── day=1/
│   │   │   │   └── data.csv
│   │   │   └── day=2/
│   │   │       └── data.csv
│   │   └── month=2/
│   └── year=2023/
└── periodico=elespectador/
    └── year=2024/
        └── month=1/
            └── day=1/
                └── data.csv
```

## Configuración

### Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `S3_BUCKET` | Bucket de S3 donde están los datos | `big-data-news-headlines` |
| `GLUE_DATABASE` | Nombre de la base de datos en Glue | `news_headlines_db` |
| `GLUE_CRAWLER_NAME` | Nombre del crawler | `news-headlines-crawler` |
| `AWS_ACCOUNT_ID` | ID de la cuenta AWS | `123456789012` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `CRAWLER_MAX_WAIT_TIME` | Tiempo máximo de espera del crawler (segundos) | `300` |

### Permisos IAM Requeridos

El Lambda necesita los siguientes permisos:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "glue:CreateCrawler",
                "glue:DeleteCrawler",
                "glue:GetCrawler",
                "glue:StartCrawler",
                "glue:StopCrawler",
                "glue:UpdateCrawler",
                "glue:GetCrawlerMetrics",
                "glue:GetDatabase",
                "glue:CreateDatabase",
                "glue:GetTable",
                "glue:UpdateTable",
                "glue:GetPartitions",
                "glue:CreatePartition",
                "glue:BatchCreatePartition"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::*:role/GlueCrawlerRole"
        }
    ]
}
```

## Despliegue

### Usando Zappa

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar AWS CLI**:
   ```bash
   aws configure
   ```

3. **Desplegar en desarrollo**:
   ```bash
   zappa deploy dev
   ```

4. **Actualizar deployment**:
   ```bash
   zappa update dev
   ```

5. **Desplegar en producción**:
   ```bash
   zappa deploy prod
   ```

### Configuración de Triggers

#### Trigger por S3

Para que el crawler se ejecute automáticamente cuando lleguen nuevos datos:

1. En la consola de AWS Lambda, configurar un trigger de S3
2. Bucket: `your-bucket-name`
3. Prefix: `headlines/final/`
4. Suffix: `.csv`
5. Event: `s3:ObjectCreated:*`

#### Trigger por EventBridge

Para ejecución programada (por ejemplo, cada hora):

```json
{
    "Rules": [{
        "Name": "RunCrawlerHourly",
        "ScheduleExpression": "rate(1 hour)",
        "State": "ENABLED",
        "Targets": [{
            "Id": "1",
            "Arn": "arn:aws:lambda:us-east-1:123456789012:function:news-crawler-dev"
        }]
    }]
}
```

## Uso

### Invocación Manual

```python
import boto3

lambda_client = boto3.client('lambda')

# Ejecutar manualmente
response = lambda_client.invoke(
    FunctionName='news-crawler-dev',
    Payload='{"manual_trigger": true}'
)

print(response['Payload'].read())
```

### Verificar Estado del Crawler

```python
import boto3

glue_client = boto3.client('glue')

# Obtener estado del crawler
response = glue_client.get_crawler(Name='news-headlines-crawler')
print(f"Estado: {response['Crawler']['State']}")
```

## Consultas en Athena

Una vez que el crawler haya ejecutado, podrás consultar los datos en Athena:

### Consulta Básica

```sql
SELECT * FROM news_headlines_db.headlines 
LIMIT 10;
```

### Consulta con Filtros de Partición

```sql
SELECT categoria, titular, enlace
FROM news_headlines_db.headlines 
WHERE periodico = 'eltiempo' 
  AND year = 2024 
  AND month = 1 
  AND day = 15;
```

### Análisis por Periódico

```sql
SELECT periodico, COUNT(*) as total_noticias
FROM news_headlines_db.headlines 
WHERE year = 2024 AND month = 1
GROUP BY periodico;
```

### Tendencias por Categoría

```sql
SELECT categoria, COUNT(*) as cantidad,
       year, month, day
FROM news_headlines_db.headlines 
WHERE year = 2024
GROUP BY categoria, year, month, day
ORDER BY year, month, day, cantidad DESC;
```

## Pruebas

### Ejecutar Pruebas Unitarias

```bash
# Instalar dependencias de testing
pip install pytest pytest-cov moto

# Ejecutar todas las pruebas
python -m pytest test_crawler.py -v

# Ejecutar con coverage
python -m pytest test_crawler.py --cov=main --cov=utils --cov=config
```

### Pruebas de Integración

```bash
# Probar creación de crawler
python test_crawler.py TestCrawlerLambda.test_create_crawler

# Probar handler completo
python test_crawler.py TestCrawlerLambda.test_lambda_handler_success
```

## Monitoreo

### Métricas en CloudWatch

El Lambda genera las siguientes métricas automáticamente:

- `Duration`: Tiempo de ejecución
- `Errors`: Número de errores
- `Invocations`: Número de invocaciones
- `Throttles`: Número de throttling events

### Logs Personalizados

El código incluye logging detallado:

```python
import logging
logger = logging.getLogger(__name__)

# Los logs aparecen en CloudWatch Logs
logger.info("Crawler ejecutado exitosamente")
logger.error("Error al crear crawler")
```

### Alertas Recomendadas

1. **Error Rate > 5%**
2. **Duration > 5 minutos**
3. **Crawler falló 3 veces consecutivas**

## Troubleshooting

### Problemas Comunes

1. **Crawler no se crea**:
   - Verificar permisos IAM
   - Verificar que el rol `GlueCrawlerRole` existe
   - Verificar que el bucket S3 existe

2. **Datos no aparecen en Athena**:
   - Verificar que el crawler terminó exitosamente
   - Verificar la estructura de particiones
   - Ejecutar `MSCK REPAIR TABLE` en Athena

3. **Timeout del Lambda**:
   - Aumentar el timeout a 15 minutos
   - Considerar usar modo asíncrono
   - Usar Step Functions para workflows largos

### Debugging

```bash
# Ver logs en tiempo real
aws logs tail /aws/lambda/news-crawler-dev --follow

# Obtener métricas del crawler
aws glue get-crawler-metrics --crawler-name-list news-headlines-crawler
```

## Arquitectura

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   S3 Event  │───▶│   Lambda     │───▶│   Glue      │
│             │    │   Crawler    │    │   Crawler   │
└─────────────┘    └──────────────┘    └─────────────┘
                           │                    │
                           ▼                    ▼
                   ┌──────────────┐    ┌─────────────┐
                   │  CloudWatch  │    │    Glue     │
                   │     Logs     │    │  Catalog    │
                   └──────────────┘    └─────────────┘
                                              │
                                              ▼
                                      ┌─────────────┐
                                      │   Athena    │
                                      │  Queries    │
                                      └─────────────┘
```

## Próximos Pasos

1. **Optimizaciones**:
   - Implementar partition projection automático
   - Agregar compresión de datos
   - Implementar data lifecycle policies

2. **Integraciones**:
   - Conectar con QuickSight para visualizaciones
   - Integrar con Step Functions
   - Añadir notificaciones SNS

3. **Monitoring Avanzado**:
   - Métricas personalizadas
   - Dashboard en CloudWatch
   - Alertas proactivas 