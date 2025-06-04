# Parcial Final - Big Data Pipeline

Este proyecto implementa un pipeline completo de procesamiento de datos de noticias utilizando servicios de AWS, incluyendo extracción web, procesamiento, almacenamiento y análisis con machine learning.

## Descripción del Proyecto

Pipeline de datos que extrae, procesa y analiza noticias de periódicos colombianos utilizando arquitectura serverless y servicios de AWS.

## Progreso del Proyecto

### ✅ Completados

#### a) Lambda de Extracción Web con Zappa ✅

Crear un lambda usando **Zappa** que descargue cada día la página principal de:

- El Tiempo
- El Espectador (o Publímetro)

**Estructura de almacenamiento en S3:**

```
s3://bucket/headlines/raw/contenido-yyyy-mm-dd.html
```

#### b) Lambda de Procesamiento con BeautifulSoup ✅

Una vez llega el archivo a la carpeta `raw`, se debe activar un segundo lambda que procese los datos utilizando **BeautifulSoup**.

**Extracción de datos:**

- Categoría
- Titular
- Enlace

**Estructura de salida CSV:**

```
s3://bucket/headlines/final/periodico=xxx/year=xxx/month=xxx/day=xxx
```

#### c) Lambda de Actualización de Catálogo ✅

Crear un tercer lambda que ejecute un **crawler en Glue** (usando boto3) para:

- Actualizar las particiones en el catálogo de Glue
- Permitir visualización de datos por **AWS Athena**

#### d) Migración a Glue Jobs y Workflows ✅

Repetir los puntos **a)** al **c)** implementados como:

- **Jobs de Python en Glue** ✅
- Articulados en un **workflow** como el del parcial 2 ✅

**📂 Implementación disponible en:** `glue_jobs/`

**Características implementadas:**

- 3 Glue Jobs (extractor, processor, crawler)
- Workflow completo con triggers condicionales
- Script de deployment automatizado
- Suite de testing comprehensiva
- Documentación detallada

#### e) Integración con RDS MySQL ✅

**Base de datos:**

- Crear BD **MySQL en RDS** con la tabla respectiva ✅
- Mapear con un crawler al catálogo de Glue ✅

**Job de inserción:**

- Usar **AWS Glue Connectors** y **AWS Job** ✅
- Copiar de tabla a tabla (S3 → RDS en el catálogo) ✅
- **Activar "job bookmarks"** para evitar duplicados ✅

**📂 Implementación disponible en:** `glue_jobs/`

**Características implementadas:**

- Job de copia S3 → RDS MySQL (`rds_mysql_job.py`)
- Crawler para mapeo RDS → Glue Catalog (`rds_crawler_job.py`)
- Conexión JDBC automática con driver MySQL
- Workflow extendido (5 jobs total)
- Script SQL para setup de tabla
- Documentación completa en `RDS_SETUP.md`

### 🚧 Pendientes

#### f) Pipeline de Machine Learning con PySpark

Crear un pipeline de procesamiento usando **PySpark ML** en **Notebook sobre EMR**:

**Características:**

- Vectorización con **TF-IDF**
- Modelo de clasificación (si aplica conocimiento de Aprendizaje de Máquina)
- Resultados escritos en **S3**

#### g) Automatización EMR con Lambda

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
│   ├── extractor/               # Lambda de extracción web
│   ├── processor/               # Lambda de procesamiento HTML
│   └── crawler/                # Lambda de crawler Glue
├── glue_jobs/                  # ✅ Jobs y Workflows de Glue (Organizados por Puntos)
│   ├── punto_d_glue_migration/  # ✅ Punto d) Migración a Glue Jobs
│   │   ├── extractor_job.py     # Job de extracción migrado
│   │   ├── processor_job.py     # Job de procesamiento migrado
│   │   ├── crawler_job.py       # Job de crawler migrado
│   │   └── README.md           # Documentación punto d
│   ├── punto_e_rds_integration/ # ✅ Punto e) Integración RDS MySQL
│   │   ├── rds_mysql_job.py     # Job de copia S3 → RDS MySQL
│   │   ├── rds_crawler_job.py   # Job de crawler RDS → Glue Catalog
│   │   ├── setup_mysql_table.sql # Script SQL para crear tabla RDS
│   │   └── RDS_SETUP.md        # Documentación RDS detallada
│   ├── punto_f_ml_pipeline/     # 🚧 Punto f) Pipeline de ML con PySpark
│   │   └── README.md           # Especificaciones y plan
│   ├── punto_g_emr_automation/  # 🚧 Punto g) Automatización EMR
│   │   └── README.md           # Especificaciones y plan
│   ├── workflow_definition.py   # Definición del workflow completo (5 jobs)
│   ├── deploy.py               # Script de deployment
│   ├── test_jobs.py           # Suite de testing
│   ├── requirements.txt        # Dependencias
│   └── README.md              # Documentación general
├── emr_scripts/               # Scripts para EMR (pendiente)
├── tests/                     # Pruebas unitarias
├── .github/workflows/         # CI/CD pipelines
└── README.md                  # Esta documentación
```

## 🚀 Quick Start - Glue Jobs (Puntos d y e)

### 1. Configurar credenciales AWS

```bash
aws configure
```

### 2. Setup RDS MySQL (Punto e)

```bash
# Configurar la tabla en tu instancia RDS
mysql -h news2.cluster-xxxxx.us-east-1.rds.amazonaws.com -u admin -p news < glue_jobs/punto_e_rds_integration/setup_mysql_table.sql

# Actualizar endpoint real en workflow_definition.py
# Reemplazar 'news2.cluster-xxxxx.us-east-1.rds.amazonaws.com' con tu endpoint real
```

### 3. Desplegar Glue Jobs y Workflow (5 jobs)

```bash
cd glue_jobs/
python deploy.py YOUR_BUCKET_NAME YOUR_IAM_ROLE_ARN us-east-1
```

### 4. Probar el workflow

```bash
python test_jobs.py all YOUR_BUCKET_NAME
```

### 5. Verificar en AWS Console

- **AWS Glue > Workflows**: Verificar `news-processing-workflow` (5 jobs)
- **AWS Athena**: Consultar datos en `news_headlines_db` y `news_rds_db`
- **S3**: Verificar estructura de particiones
- **RDS MySQL**: Consultar tabla `noticias`

Para más detalles sobre RDS, consultar: [`glue_jobs/punto_e_rds_integration/RDS_SETUP.md`](glue_jobs/punto_e_rds_integration/RDS_SETUP.md)
Para detalles del punto d, consultar: [`glue_jobs/punto_d_glue_migration/README.md`](glue_jobs/punto_d_glue_migration/README.md)
Para detalles generales, consultar: [`glue_jobs/README.md`](glue_jobs/README.md)

## 📈 Roadmap

- [x] **Punto a)** - Lambda Extractor con Zappa
- [x] **Punto b)** - Lambda Processor con BeautifulSoup
- [x] **Punto c)** - Lambda Crawler para Glue
- [x] **Punto d)** - Migración a Glue Jobs y Workflows
- [x] **Punto e)** - Integración con RDS MySQL
- [ ] **Punto f)** - Pipeline de ML con PySpark
- [ ] **Punto g)** - Automatización EMR con Lambda
- [ ] **CI/CD** - Pipeline de despliegue continuo
- [ ] **Testing** - Cobertura completa de pruebas

## 📊 Arquitectura Actual

```mermaid
graph TB
    subgraph "Glue Workflow (✅ Implementado)"
        A[Daily Trigger<br/>6 AM UTC] --> B[Extractor Job]
        B --> C[Processor Job]
        C --> D[Crawler Job]
    end

    subgraph "Storage & Catalog"
        E[S3 Raw HTML]
        F[S3 Partitioned CSV]
        G[Glue Data Catalog]
        H[Athena Queries]
    end

    B --> E
    C --> F
    D --> G
    G --> H

    subgraph "Future (Pendiente)"
        I[RDS MySQL]
        J[EMR ML Pipeline]
        K[Lambda EMR Manager]
    end

    F -.-> I
    F -.-> J
    K -.-> J
```

## 🔗 Enlaces Útiles

- [Documentación AWS Glue](https://docs.aws.amazon.com/glue/)
- [Documentación Zappa](https://github.com/zappa/Zappa)
- [AWS CLI Setup](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
