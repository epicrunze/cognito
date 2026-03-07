#!/bin/bash
# Verify a Vikunja API endpoint by making a real HTTP request.
#
# Usage:
#   ./verify-endpoint.sh METHOD PATH [JSON_BODY]
#
# Examples:
#   ./verify-endpoint.sh GET /projects
#   ./verify-endpoint.sh PUT /projects/1/tasks '{"title":"Test task"}'
#   ./verify-endpoint.sh POST /tasks/1 '{"done":true}'
#   ./verify-endpoint.sh DELETE /tasks/1
#
# Environment:
#   VIKUNJA_URL       - Base URL (required, or set in .env — ask user for their endpoint)
#   VIKUNJA_API_TOKEN - Bearer token (required, or set in .env)

set -euo pipefail

# Load .env from project root if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
    set +a
fi

if [[ -z "${VIKUNJA_URL:-}" ]]; then
    echo "ERROR: VIKUNJA_URL is not set. Set it in .env or environment." >&2
    echo "       Ask the user where their Vikunja instance is hosted." >&2
    exit 1
fi
METHOD="${1:?Usage: $0 METHOD PATH [JSON_BODY]}"
PATH_SEGMENT="${2:?Usage: $0 METHOD PATH [JSON_BODY]}"
BODY="${3:-}"

if [[ -z "${VIKUNJA_API_TOKEN:-}" ]]; then
    echo "ERROR: VIKUNJA_API_TOKEN is not set. Set it in .env or environment." >&2
    exit 1
fi

URL="${VIKUNJA_URL}/api/v1${PATH_SEGMENT}"

echo ">>> ${METHOD} ${URL}"
echo ""

CURL_ARGS=(
    -s
    -w "\n---\nHTTP Status: %{http_code}\n"
    -D -
    -X "$METHOD"
    -H "Authorization: Bearer ${VIKUNJA_API_TOKEN}"
    -H "Content-Type: application/json"
)

if [[ -n "$BODY" ]]; then
    CURL_ARGS+=(-d "$BODY")
fi

RESPONSE=$(curl "${CURL_ARGS[@]}" "$URL" 2>&1)

# Split headers and body
HEADERS=$(echo "$RESPONSE" | sed -n '1,/^\r$/p')
BODY_CONTENT=$(echo "$RESPONSE" | sed -n '/^\r$/,$p' | tail -n +2)

# Show pagination headers if present
echo "=== Response Headers ==="
echo "$HEADERS" | grep -iE "^(x-pagination|x-max-permission|HTTP/)" || true
echo ""

echo "=== Response Body (first 500 chars) ==="
if command -v jq &>/dev/null; then
    echo "$BODY_CONTENT" | head -c 2000 | jq '.' 2>/dev/null || echo "$BODY_CONTENT" | head -c 500
else
    echo "$BODY_CONTENT" | head -c 500
fi
echo ""

# Extract status code and exit accordingly
STATUS=$(echo "$RESPONSE" | grep "^HTTP Status:" | tail -1 | awk '{print $3}')
if [[ "$STATUS" =~ ^2 ]]; then
    echo "OK (${STATUS})"
    exit 0
else
    echo "FAILED (${STATUS})"
    exit 1
fi
