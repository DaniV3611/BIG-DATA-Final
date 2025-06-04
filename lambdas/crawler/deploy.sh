#!/bin/bash

# Deploy script for Glue Crawler Lambda
# Usage: ./deploy.sh [dev|prod] [deploy|update]

set -e

# Default values
ENVIRONMENT=${1:-dev}
ACTION=${2:-deploy}

echo "🚀 Deploying Glue Crawler Lambda to $ENVIRONMENT environment"
echo "Action: $ACTION"

# Check if required tools are installed
check_requirements() {
    echo "Checking requirements..."
    
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 is required but not installed"
        exit 1
    fi
    
    if ! command -v pip &> /dev/null; then
        echo "❌ pip is required but not installed"
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI is required but not installed"
        exit 1
    fi
    
    echo "✅ All requirements satisfied"
}

# Install Python dependencies
install_dependencies() {
    echo "Installing Python dependencies..."
    
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate || source venv/Scripts/activate 2>/dev/null || {
        echo "❌ Failed to activate virtual environment"
        exit 1
    }
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Dependencies installed"
}

# Run tests
run_tests() {
    echo "Running tests..."
    
    source venv/bin/activate || source venv/Scripts/activate 2>/dev/null
    
    # Install test dependencies
    pip install pytest pytest-cov moto
    
    # Run tests
    python -m pytest test_crawler.py -v --tb=short
    
    if [ $? -eq 0 ]; then
        echo "✅ All tests passed"
    else
        echo "❌ Tests failed"
        exit 1
    fi
}

# Validate configuration
validate_config() {
    echo "Validating configuration..."
    
    if [ ! -f "zappa_settings.json" ]; then
        echo "❌ zappa_settings.json not found"
        exit 1
    fi
    
    if [ ! -f "config.py" ]; then
        echo "❌ config.py not found"
        exit 1
    fi
    
    # Check AWS credentials
    aws sts get-caller-identity > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ AWS credentials not configured"
        echo "Run: aws configure"
        exit 1
    fi
    
    echo "✅ Configuration validated"
}

# Deploy with Zappa
deploy_lambda() {
    echo "Deploying Lambda function..."
    
    source venv/bin/activate || source venv/Scripts/activate 2>/dev/null
    
    if [ "$ACTION" = "deploy" ]; then
        echo "Creating new deployment..."
        zappa deploy $ENVIRONMENT
    elif [ "$ACTION" = "update" ]; then
        echo "Updating existing deployment..."
        zappa update $ENVIRONMENT
    else
        echo "❌ Invalid action: $ACTION"
        echo "Use 'deploy' or 'update'"
        exit 1
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ Lambda deployed successfully"
    else
        echo "❌ Deployment failed"
        exit 1
    fi
}

# Get deployment info
get_deployment_info() {
    echo "Getting deployment information..."
    
    source venv/bin/activate || source venv/Scripts/activate 2>/dev/null
    
    zappa status $ENVIRONMENT
}

# Create S3 trigger (optional)
setup_s3_trigger() {
    echo "Setting up S3 trigger..."
    
    # Get function ARN
    FUNCTION_NAME=$(zappa status $ENVIRONMENT | grep "Lambda Name" | awk '{print $3}')
    
    if [ -z "$FUNCTION_NAME" ]; then
        echo "❌ Could not determine Lambda function name"
        return 1
    fi
    
    # Note: This would require additional AWS CLI commands to set up S3 trigger
    echo "ℹ️  To set up S3 trigger manually:"
    echo "   1. Go to AWS Lambda console"
    echo "   2. Select function: $FUNCTION_NAME"
    echo "   3. Add S3 trigger with:"
    echo "      - Bucket: your-bucket-name"
    echo "      - Prefix: headlines/final/"
    echo "      - Suffix: .csv"
    echo "      - Event: s3:ObjectCreated:*"
}

# Main execution
main() {
    echo "🔧 Starting deployment process..."
    
    check_requirements
    validate_config
    install_dependencies
    
    # Skip tests in CI/CD or if SKIP_TESTS is set
    if [ "$SKIP_TESTS" != "true" ]; then
        run_tests
    else
        echo "⚠️  Skipping tests (SKIP_TESTS=true)"
    fi
    
    deploy_lambda
    get_deployment_info
    
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Set up S3 trigger (see instructions above)"
    echo "2. Test the function manually"
    echo "3. Monitor CloudWatch logs"
    echo ""
    echo "Useful commands:"
    echo "  zappa tail $ENVIRONMENT        # View logs"
    echo "  zappa invoke $ENVIRONMENT      # Test function"
    echo "  zappa undeploy $ENVIRONMENT    # Remove deployment"
}

# Handle script arguments
case "$1" in
    "test")
        install_dependencies
        run_tests
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [environment] [action]"
        echo ""
        echo "Environments: dev, prod"
        echo "Actions: deploy, update"
        echo ""
        echo "Special commands:"
        echo "  $0 test          # Run tests only"
        echo "  $0 help          # Show this help"
        echo ""
        echo "Environment variables:"
        echo "  SKIP_TESTS=true  # Skip running tests"
        ;;
    *)
        main
        ;;
esac 