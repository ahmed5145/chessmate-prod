#!/bin/bash
# Run all ChessMate health and cache tests

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Set your configuration
BASE_URL="http://localhost:8000"
REDIS_URL="redis://localhost:6379/0"
ADMIN_USER="admin"
ADMIN_PASSWORD="password"
OUTPUT_DIR="./test_results"

# Create output directory
mkdir -p $OUTPUT_DIR

echo -e "${YELLOW}ChessMate Test Suite${NC}"
echo -e "${YELLOW}===================${NC}"
echo "Testing against: $BASE_URL"
echo "Redis URL: $REDIS_URL"
echo "Output directory: $OUTPUT_DIR"
echo

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo -e "${RED}Python is not installed. Please install Python to run the tests.${NC}"
    exit 1
fi

# Check for required packages
echo "Checking for required packages..."
MISSING_PACKAGES=0

if ! python -c "import requests" &> /dev/null; then
    echo -e "${RED}Missing package: requests${NC}"
    MISSING_PACKAGES=1
fi

if ! python -c "import redis" &> /dev/null; then
    echo -e "${RED}Missing package: redis${NC}"
    MISSING_PACKAGES=1
fi

if [ $MISSING_PACKAGES -eq 1 ]; then
    echo -e "${YELLOW}Please install missing packages with: pip install requests redis${NC}"
    exit 1
fi

echo -e "${GREEN}All required packages found.${NC}"
echo

# Check if server is running
echo "Checking if server is running..."
if ! curl -s "$BASE_URL/health/" > /dev/null; then
    echo -e "${RED}Cannot connect to $BASE_URL. Make sure the server is running.${NC}"
    exit 1
fi
echo -e "${GREEN}Server is running.${NC}"
echo

# Run health check tests
echo -e "${YELLOW}Running health check tests...${NC}"
python test_health_checks.py --url $BASE_URL --admin-user $ADMIN_USER --admin-password $ADMIN_PASSWORD --output $OUTPUT_DIR/health_check_results.json
HEALTH_EXIT=$?

echo

# Run cache invalidation tests
echo -e "${YELLOW}Running cache invalidation tests...${NC}"
python test_cache_invalidation.py --url $BASE_URL --redis $REDIS_URL --admin-user $ADMIN_USER --admin-password $ADMIN_PASSWORD --output $OUTPUT_DIR/cache_invalidation_results.json
CACHE_EXIT=$?

echo

# Overall summary
echo -e "${YELLOW}Test Suite Summary${NC}"
echo -e "${YELLOW}================${NC}"
echo "Results saved to: $OUTPUT_DIR"

if [ $HEALTH_EXIT -eq 0 ] && [ $CACHE_EXIT -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Check the output above for details.${NC}"
    exit 1
fi
