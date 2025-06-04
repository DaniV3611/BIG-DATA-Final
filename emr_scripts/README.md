# EMR Scripts - News Classification Pipeline

Este directorio contiene scripts para ejecutar el pipeline de machine learning en Amazon EMR.

## 📄 Archivos

### `classification_pipeline.py`
Script principal que implementa el pipeline de clasificación de noticias usando PySpark ML.

**Características:**
- Convierte el notebook Jupyter en script ejecutable
- Valores fijos predefinidos (como en el notebook original)
- Manejo robusto de errores y logging
- Optimizado para ejecución en cluster EMR
- Múltiples formatos de salida (CSV, Parquet)

## 🚀 Uso del Script

### Ejecución Local (para testing)
```bash
spark-submit classification_pipeline.py
```

### Ejecución en EMR Cluster
```bash
spark-submit \
    --deploy-mode cluster \
    --driver-memory 4g \
    --executor-memory 4g \
    --executor-cores 2 \
    --num-executors 3 \
    classification_pipeline.py
```

## ⚙️ Configuración Fija

El script usa valores predefinidos (idénticos al notebook original):

| Configuración | Valor |
|---------------|-------|
| **Input Path** | `s3://final-gizmo/headlines/final/periodico=*/year=*/month=*/day=*/*.csv` |
| **Output Path** | `s3://final-gizmo/resultados` |
| **TF-IDF Features** | `10000` |
| **Max Iterations** | `10` |
| **App Name** | `NewsClassificationPipeline` |

## 📊 Pipeline de Procesamiento

1. **Carga de Datos**: Lee archivos CSV particionados desde S3
2. **Preprocesamiento**: 
   - Limpieza de texto (caracteres especiales, normalización)
   - Filtrado de registros vacíos
   - Análisis de distribución de categorías
3. **Feature Engineering**:
   - Tokenización de texto
   - Remoción de stop words
   - Vectorización TF-IDF
4. **Entrenamiento**: Entrenamiento de Logistic Regression en todo el dataset
5. **Predicciones**: Generación de predicciones para todo el dataset
6. **Almacenamiento**: 
   - CSV con predicciones principales
   - CSV con probabilidades
   - Parquet completo

## 📈 Resultados

El script genera exactamente la misma salida que el notebook original:

```
s3://final-gizmo/resultados/
├── predicciones.csv           # Predicciones principales (como notebook)
├── predicciones_prob.csv      # Predicciones con probabilidades
└── predicciones_parquet/      # Dataset completo en Parquet
```

### Formato de Salida CSV
```csv
clean_text,label,prediction
"ubicacin secreta carros alta gama...",Unidad investigativa,3.0
"procuradura abre investigacin...",Unidad investigativa,3.0
```

### Formato de Salida CSV con Probabilidades
```csv
clean_text,label,prediction,probability_str
"ubicacin secreta carros alta gama...",Unidad investigativa,3.0,"[0.001, 0.002, ...]"
```

## 🔧 Configuración para EMR

### Configuración Recomendada del Cluster
```json
{
  "Name": "news-classification-cluster",
  "ReleaseLabel": "emr-6.15.0",
  "Applications": [
    {"Name": "Spark"},
    {"Name": "Hadoop"}
  ],
  "InstanceGroups": [
    {
      "Name": "Master",
      "InstanceRole": "MASTER",
      "InstanceType": "m5.xlarge",
      "InstanceCount": 1
    },
    {
      "Name": "Core",
      "InstanceRole": "CORE", 
      "InstanceType": "m5.xlarge",
      "InstanceCount": 2
    }
  ]
}
```

### Configuraciones Spark Recomendadas
- `spark.sql.adaptive.enabled=true`: Optimización adaptativa de consultas
- `spark.sql.adaptive.coalescePartitions.enabled=true`: Optimización de particiones
- `spark.serializer=org.apache.spark.serializer.KryoSerializer`: Serialización optimizada

## 📝 Logging

El script utiliza logging estándar de Python con nivel INFO. Los logs incluyen:
- Estadísticas de carga de datos
- Progreso del entrenamiento
- Información de guardado de resultados
- Distribución de predicciones

## 🐛 Troubleshooting

### Errores Comunes

1. **OutOfMemoryError**: Aumentar `--driver-memory` y `--executor-memory`
2. **Timeout en S3**: Verificar permisos IAM del cluster
3. **Particiones pequeñas**: Ajustar `num-executors` y `executor-cores`

### Para Modificar Configuración

Si necesitas cambiar las rutas o parámetros, edita estas constantes al inicio del script:

```python
INPUT_PATH = "s3://tu-bucket/ruta/entrada/*.csv"
OUTPUT_BASE_PATH = "s3://tu-bucket/resultados"
NUM_FEATURES = 10000
MAX_ITER = 10
```

## 🔗 Próximos Pasos

Este script está listo para ser usado por el Lambda del punto g) que:
1. Lanzará un cluster EMR
2. Ejecutará este script con `spark-submit`
3. Monitoreará la ejecución
4. Apagará el cluster automáticamente 