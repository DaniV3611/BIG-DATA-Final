# Parcial Final - Big Data Pipeline

Este proyecto implementa un pipeline completo de procesamiento de datos de noticias utilizando servicios de AWS, incluyendo extracción web, procesamiento, almacenamiento y análisis con machine learning.

## Descripción del Proyecto

Pipeline de datos que extrae, procesa y analiza noticias de periódicos colombianos utilizando arquitectura serverless y servicios de AWS.

## Requisitos del Proyecto

### a) Lambda de Extracción Web con Zappa

Crear un lambda usando **Zappa** que descargue cada día la página principal de:

- El Tiempo
- El Espectador (o Publímetro)

**Estructura de almacenamiento en S3:**

```
s3://bucket/headlines/raw/contenido-yyyy-mm-dd.html
```

### b) Lambda de Procesamiento con BeautifulSoup

Una vez llega el archivo a la carpeta `raw`, se debe activar un segundo lambda que procese los datos utilizando **BeautifulSoup**.

**Extracción de datos:**

- Categoría
- Titular
- Enlace

**Estructura de salida CSV:**

```
s3://bucket/headlines/final/periodico=xxx/year=xxx/month=xxx/day=xxx
```

### c) Lambda de Actualización de Catálogo

Crear un tercer lambda que ejecute un **crawler en Glue** (usando boto3) para:

- Actualizar las particiones en el catálogo de Glue
- Permitir visualización de datos por **AWS Athena**

### d) Migración a Glue Jobs y Workflows

Repetir los puntos **a)** al **c)** implementados como:

- **Jobs de Python en Glue**
- Articulados en un **workflow** como el del parcial 2

### e) Integración con RDS MySQL

**Base de datos:**

- Crear BD **MySQL en RDS** con la tabla respectiva
- Mapear con un crawler al catálogo de Glue

**Job de inserción:**

- Usar **AWS Glue Connectors** y **AWS Job**
- Copiar de tabla a tabla (S3 → RDS en el catálogo)
- **Activar "job bookmarks"** para evitar duplicados

### f) Pipeline de Machine Learning con PySpark

Crear un pipeline de procesamiento usando **PySpark ML** en **Notebook sobre EMR**:

**Características:**

- Vectorización con **TF-IDF**
- Modelo de clasificación (si aplica conocimiento de Aprendizaje de Máquina)
- Resultados escritos en **S3**

### g) Automatización EMR con Lambda

**Implementación:**

- Convertir notebook anterior en **script ejecutable**
- Crear lambda que:
  - Lance un cluster EMR
  - Ejecute el script con `spark-submit`
  - Apague el cluster automáticamente

## Requisitos de Entrega

### 📋 Obligatorios

- **Código en GitHub** con:
  - ✅ Uso de ramas
  - ✅ Commits descriptivos
  - ✅ Código limpio y comentado
  - ✅ Pruebas unitarias (donde aplique)

> **⚠️ Penalización:** Menos una unidad si no se cumple

### 🚀 Puntos Adicionales

- **Pipeline de despliegue continuo** en GitHub para scripts de jobs
- **Puntos a-d obligatorios** implementados por código con:
  - Pruebas unitarias
  - Despliegue continuo en GitHub

## Tecnologías Utilizadas

- **AWS Lambda** - Funciones serverless
- **Zappa** - Framework para deployment de Lambda
- **AWS S3** - Almacenamiento de objetos
- **AWS Glue** - ETL y catálogo de datos
- **AWS Athena** - Consultas SQL sobre S3
- **AWS RDS MySQL** - Base de datos relacional
- **AWS EMR** - Cluster de Spark
- **BeautifulSoup** - Web scraping
- **PySpark ML** - Machine Learning distribuido
- **GitHub Actions** - CI/CD

## Estructura del Proyecto

```
├── lambdas/
│   ├── extractor/
│   ├── processor/
│   └── crawler/
├── glue_jobs/
├── emr_scripts/
├── tests/
├── .github/workflows/
└── README.md
```
