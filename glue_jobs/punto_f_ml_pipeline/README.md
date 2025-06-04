# Punto f) Pipeline de Machine Learning con PySpark

Pipeline de procesamiento usando **PySpark ML** en **Notebook sobre EMR** para análisis de las noticias extraídas.

## 🚧 Estado: PENDIENTE

Este punto está pendiente de implementación como parte del parcial final.

## 📋 Especificaciones

### Características Requeridas

- **Vectorización con TF-IDF** - Análisis de texto de titulares
- **Modelo de clasificación** - Si aplica conocimiento de Aprendizaje de Máquina
- **Resultados en S3** - Almacenamiento de modelos y predicciones

### Tecnologías

- **AWS EMR** - Cluster de Spark para procesamiento distribuido
- **PySpark ML** - Librería de Machine Learning
- **Jupyter Notebook** - Desarrollo interactivo
- **S3** - Almacenamiento de datos y modelos

## 🎯 Objetivos del Pipeline

### Análisis de Texto

1. **Preprocessing**: Limpieza y normalización de titulares
2. **Vectorización**: Conversión de texto a vectores usando TF-IDF
3. **Feature Engineering**: Extracción de características adicionales

### Modelado

1. **Clasificación de Categorías**: Predicción automática de categorías
2. **Análisis de Sentimientos**: Clasificación positivo/negativo/neutral
3. **Detección de Temas**: Clustering de noticias similares
4. **Análisis de Tendencias**: Identificación de patrones temporales

## 📊 Fuentes de Datos

### Entrada

- **Fuente**: Tabla `news_headlines` en Glue Data Catalog
- **Formato**: CSV particionado por fecha y periódico
- **Campos**: fecha, categoria, titular, enlace, periodico

### Salida Esperada

```
s3://bucket/ml-results/
├── models/
│   ├── tfidf-vectorizer.model
│   ├── category-classifier.model
│   └── sentiment-classifier.model
├── predictions/
│   ├── year=2024/month=12/day=06/
│   │   └── predictions.parquet
└── analysis/
    ├── category-analysis.json
    ├── sentiment-trends.json
    └── topic-clusters.json
```

## 🔗 Referencias

- [PySpark ML Guide](https://spark.apache.org/docs/latest/ml-guide.html)
- [AWS EMR Notebooks](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-managed-notebooks.html)
- [TF-IDF in Spark](https://spark.apache.org/docs/latest/ml-features.html#tf-idf)
