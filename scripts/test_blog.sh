#!/usr/bin/env bash
# =============================================================================
# Ghost Blog & MySQL — Automated Integration Test Runner
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}    Running Ghost Blog Integration & Health Tests   ${NC}"
echo -e "${BLUE}====================================================${NC}"

cd "${ROOT_DIR}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 is required to run the test suite.${NC}" >&2
    exit 1
fi

python3 tests/test_blog_service.py

echo -e "\n${GREEN}✔ All Ghost blog integration and health tests passed successfully!${NC}"
