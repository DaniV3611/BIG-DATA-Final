# EMR Manager Lambda

Lambda function que automatiza la ejecución del pipeline de machine learning en Amazon EMR.

## 🎯 Funcionalidad

Este Lambda implementa el **punto g)** del proyecto final:

1. **Sube el script** de clasificación a S3
2. **Lanza un cluster EMR** con configuración optimizada
3. **Ejecuta el pipeline** de ML con `spark-submit`
4. **Monitorea la ejecución** hasta completarse
5. **Apaga el cluster** automáticamente (ahorro de costos)

## 🚀 Deployment

### 1. Instalar dependencias
```bash
cd lambdas/emr_manager/
pip install -r requirements.txt
pip install zappa
```

### 2. Configurar AWS CLI
```bash
aws configure
```

### 3. Desplegar con Zappa
```bash
# Primera vez
zappa deploy dev

# Actualizaciones
zappa update dev
```

### 4. Deployment en producción
```bash
zappa deploy production
```

## ⚙️ Configuración

### Configuración por Defecto
```python
{
    'cluster_name': 'news-classification-{timestamp}',
    'emr_release': 'emr-6.15.0',
    'master_instance_type': 'm5.xlarge',
    'core_instance_type': 'm5.xlarge', 
    'core_instance_count': 2,
    'bucket_name': 'final-gizmo',
    'timeout_minutes': 60
}
```

### Personalizar Configuración
Puedes override cualquier configuración enviando parámetros en el evento:

```json
{
    "cluster_name": "mi-cluster-custom",
    "core_instance_count": 3,
    "timeout_minutes": 90,
    "master_instance_type": "m5.2xlarge"
}
```

## 📊 Uso

### Invocar desde AWS Console
1. **AWS Lambda Console** → `emr-manager-dev`
2. **Test** → Event template: `API Gateway AWS Proxy`
3. **Execute**

### Invocar desde CLI
```bash
aws lambda invoke \
    --function-name emr-manager-dev \
    --payload '{}' \
    response.json
```

### Invocar con configuración custom
```bash
aws lambda invoke \
    --function-name emr-manager-dev \
    --payload '{"core_instance_count": 3, "timeout_minutes": 90}' \
    response.json
```

### Programar ejecución (EventBridge)
```bash
# Ejecutar todos los días a las 2 AM
aws events put-rule \
    --name "daily-ml-pipeline" \
    --schedule-expression "cron(0 2 * * ? *)"

aws events put-targets \
    --rule "daily-ml-pipeline" \
    --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT:function:emr-manager-dev"
```

## 📈 Monitoreo

### CloudWatch Logs
```bash
# Ver logs en tiempo real
zappa tail dev

# Ver logs específicos
aws logs filter-log-events \
    --log-group-name "/aws/lambda/emr-manager-dev" \
    --start-time $(date -d '1 hour ago' +%s)000
```

### Métricas Importantes
- **Duration**: Tiempo total de ejecución (incluye tiempo de cluster)
- **Errors**: Errores en la ejecución del Lambda
- **EMR Cluster State**: Estado del cluster EMR en CloudWatch

## 🔧 Configuración IAM

El Lambda necesita los siguientes permisos:

### Policy EMR
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "emr:RunJobFlow",
                "emr:DescribeCluster",
                "emr:ListSteps",
                "emr:TerminateJobFlows"
            ],
            "Resource": "*"
        }
    ]
}
```

### Policy S3
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::final-gizmo/*"
        }
    ]
}
```

### Policy IAM PassRole
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": [
                "arn:aws:iam::*:role/EMR_DefaultRole",
                "arn:aws:iam::*:role/EMR_EC2_DefaultRole"
            ]
        }
    ]
}
```

## 📊 Response Format

### Successful Execution
```json
{
    "statusCode": 200,
    "body": {
        "message": "EMR classification pipeline completed successfully",
        "cluster_id": "j-ABC123DEF456",
        "timestamp": "2025-01-15T10:30:00Z",
        "script_location": "s3://final-gizmo/scripts/classification_pipeline.py"
    }
}
```

### Error Response
```json
{
    "statusCode": 500,
    "body": {
        "error": "Failed to launch EMR cluster: Access Denied",
        "timestamp": "2025-01-15T10:30:00Z"
    }
}
```

## 🐛 Troubleshooting

### Errores Comunes

1. **Access Denied**: Verificar permisos IAM
2. **Cluster Launch Failed**: Verificar roles EMR_DefaultRole
3. **Timeout**: Aumentar `timeout_minutes` en configuración
4. **Script Upload Failed**: Verificar permisos S3

### Debugging
```bash
# Ver logs detallados
zappa tail dev --since 1h

# Verificar estado del cluster EMR
aws emr describe-cluster --cluster-id j-CLUSTERID

# Ver steps del cluster
aws emr list-steps --cluster-id j-CLUSTERID
```

## 💰 Optimización de Costos

- **Auto-terminate**: Cluster se apaga automáticamente
- **Spot Instances**: Opcional para reducir costos
- **Timeout**: Evita clusters colgados
- **Instance Types**: Ajustar según carga de trabajo

## 🔗 Integración

### Con EventBridge (Scheduler)
- Ejecutar pipeline diariamente
- Trigger basado en eventos S3
- Integración con otros servicios AWS

### Con API Gateway
- Crear API REST para trigger manual
- Dashboard web para ejecutar pipeline
- Integración con aplicaciones externas

## 📋 Próximos Pasos

1. **Testear** el deployment completo
2. **Configurar** EventBridge para ejecución programada
3. **Optimizar** configuración de cluster según datos
4. **Implementar** notificaciones (SNS/SES)
5. **Crear** dashboard de monitoreo 