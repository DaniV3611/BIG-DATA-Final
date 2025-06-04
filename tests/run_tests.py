#!/usr/bin/env python3
"""
Script principal para ejecutar tests del pipeline de Big Data.
Proporciona diferentes opciones de ejecución y configuración.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def setup_environment():
    """Setup del entorno de testing"""
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Set environment variables for testing
    os.environ['TESTING'] = 'true'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    print("🔧 Entorno de testing configurado")


def install_dependencies():
    """Instalar dependencias de testing"""
    print("📦 Instalando dependencias de testing...")
    
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 
            'tests/requirements-test.txt'
        ], check=True, capture_output=True)
        print("✅ Dependencias instaladas correctamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        sys.exit(1)


def run_unit_tests():
    """Ejecutar solo tests unitarios"""
    print("🧪 Ejecutando tests unitarios...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/',
        '-m', 'unit',
        '--tb=short',
        '-v'
    ]
    
    return subprocess.run(cmd)


def run_integration_tests():
    """Ejecutar tests de integración"""
    print("🔗 Ejecutando tests de integración...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/test_integration.py',
        '--tb=short',
        '-v'
    ]
    
    return subprocess.run(cmd)


def run_lambda_tests():
    """Ejecutar tests de Lambda functions"""
    print("λ Ejecutando tests de Lambda...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/test_lambdas.py',
        '--tb=short',
        '-v'
    ]
    
    return subprocess.run(cmd)


def run_glue_tests():
    """Ejecutar tests de Glue Jobs"""
    print("🔧 Ejecutando tests de Glue Jobs...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/test_glue_jobs.py',
        '--tb=short',
        '-v'
    ]
    
    return subprocess.run(cmd)


def run_emr_tests():
    """Ejecutar tests de EMR scripts"""
    print("⚡ Ejecutando tests de EMR...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/test_emr_scripts.py',
        '--tb=short',
        '-v'
    ]
    
    return subprocess.run(cmd)


def run_all_tests():
    """Ejecutar todos los tests"""
    print("🚀 Ejecutando suite completa de tests...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/',
        '--tb=short',
        '-v',
        '--cov=lambdas',
        '--cov=glue_jobs', 
        '--cov=emr_scripts',
        '--cov-report=html:tests/htmlcov',
        '--cov-report=term-missing'
    ]
    
    return subprocess.run(cmd)


def run_fast_tests():
    """Ejecutar solo tests rápidos (excluir tests lentos)"""
    print("⚡ Ejecutando tests rápidos...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/',
        '-m', 'not slow',
        '--tb=short',
        '-v'
    ]
    
    return subprocess.run(cmd)


def run_coverage_report():
    """Generar reporte de coverage detallado"""
    print("📊 Generando reporte de coverage...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/',
        '--cov=lambdas',
        '--cov=glue_jobs',
        '--cov=emr_scripts',
        '--cov-report=html:tests/htmlcov',
        '--cov-report=xml:tests/coverage.xml',
        '--cov-report=term-missing',
        '--cov-fail-under=70'
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("✅ Reporte de coverage generado en tests/htmlcov/index.html")
    else:
        print("❌ Coverage por debajo del umbral requerido (70%)")
    
    return result


def run_parallel_tests():
    """Ejecutar tests en paralelo"""
    print("🏃‍♂️ Ejecutando tests en paralelo...")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/',
        '-n', 'auto',  # pytest-xdist for parallel execution
        '--tb=short',
        '-v'
    ]
    
    return subprocess.run(cmd)


def run_specific_test(test_pattern):
    """Ejecutar tests específicos basados en un patrón"""
    print(f"🎯 Ejecutando tests que coinciden con: {test_pattern}")
    
    cmd = [
        sys.executable, '-m', 'pytest', 
        'tests/',
        '-k', test_pattern,
        '--tb=short',
        '-v'
    ]
    
    return subprocess.run(cmd)


def run_quality_checks():
    """Ejecutar checks de calidad de código"""
    print("✨ Ejecutando checks de calidad de código...")
    
    # Flake8
    print("🔍 Ejecutando flake8...")
    subprocess.run([sys.executable, '-m', 'flake8', 'lambdas/', 'glue_jobs/', 'emr_scripts/', 'tests/'])
    
    # Black (check only)
    print("🔧 Verificando formato con Black...")
    subprocess.run([sys.executable, '-m', 'black', '--check', '--diff', 'lambdas/', 'glue_jobs/', 'emr_scripts/', 'tests/'])
    
    # isort (check only)
    print("📦 Verificando imports con isort...")
    subprocess.run([sys.executable, '-m', 'isort', '--check-only', '--diff', 'lambdas/', 'glue_jobs/', 'emr_scripts/', 'tests/'])
    
    # MyPy
    print("🔒 Ejecutando verificación de tipos con MyPy...")
    subprocess.run([sys.executable, '-m', 'mypy', 'lambdas/', 'glue_jobs/', 'emr_scripts/'])


def clean_test_artifacts():
    """Limpiar artefactos de testing"""
    print("🧹 Limpiando artefactos de testing...")
    
    import shutil
    
    artifacts = [
        'tests/__pycache__',
        'tests/.pytest_cache',
        'tests/htmlcov',
        'tests/coverage.xml',
        '.coverage'
    ]
    
    for artifact in artifacts:
        if os.path.exists(artifact):
            if os.path.isdir(artifact):
                shutil.rmtree(artifact)
            else:
                os.remove(artifact)
    
    print("✅ Artefactos limpiados")


def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(description='Script de testing para Big Data Pipeline')
    
    parser.add_argument('--install-deps', action='store_true', 
                       help='Instalar dependencias de testing')
    parser.add_argument('--unit', action='store_true', 
                       help='Ejecutar solo tests unitarios')
    parser.add_argument('--integration', action='store_true', 
                       help='Ejecutar tests de integración')
    parser.add_argument('--lambda', action='store_true', dest='lambda_tests',
                       help='Ejecutar tests de Lambda')
    parser.add_argument('--glue', action='store_true', 
                       help='Ejecutar tests de Glue Jobs')
    parser.add_argument('--emr', action='store_true', 
                       help='Ejecutar tests de EMR')
    parser.add_argument('--all', action='store_true', 
                       help='Ejecutar todos los tests')
    parser.add_argument('--fast', action='store_true', 
                       help='Ejecutar solo tests rápidos')
    parser.add_argument('--coverage', action='store_true', 
                       help='Generar reporte de coverage')
    parser.add_argument('--parallel', action='store_true', 
                       help='Ejecutar tests en paralelo')
    parser.add_argument('--quality', action='store_true', 
                       help='Ejecutar checks de calidad')
    parser.add_argument('--clean', action='store_true', 
                       help='Limpiar artefactos de testing')
    parser.add_argument('-k', '--pattern', type=str, 
                       help='Ejecutar tests que coincidan con el patrón')
    
    args = parser.parse_args()
    
    setup_environment()
    
    if args.install_deps:
        install_dependencies()
        return
    
    if args.clean:
        clean_test_artifacts()
        return
    
    if args.quality:
        run_quality_checks()
        return
    
    # Ejecutar tests según las opciones seleccionadas
    result = None
    
    if args.unit:
        result = run_unit_tests()
    elif args.integration:
        result = run_integration_tests()
    elif args.lambda_tests:
        result = run_lambda_tests()
    elif args.glue:
        result = run_glue_tests()
    elif args.emr:
        result = run_emr_tests()
    elif args.all:
        result = run_all_tests()
    elif args.fast:
        result = run_fast_tests()
    elif args.coverage:
        result = run_coverage_report()
    elif args.parallel:
        result = run_parallel_tests()
    elif args.pattern:
        result = run_specific_test(args.pattern)
    else:
        # Por defecto, ejecutar tests rápidos
        result = run_fast_tests()
    
    # Exit with the same code as pytest
    if result:
        sys.exit(result.returncode)


if __name__ == '__main__':
    main() 