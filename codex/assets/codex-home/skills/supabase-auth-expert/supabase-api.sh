#!/bin/bash
# Supabase API Helper Script
# Provides common functions for making REST API calls to Supabase

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate required environment variables
validate_env() {
    if [[ -z "${SUPABASE_URL}" ]]; then
        echo -e "${RED}Error: SUPABASE_URL environment variable is not set${NC}" >&2
        echo "Please set it with: export SUPABASE_URL='https://your-project.supabase.co'" >&2
        return 1
    fi

    if [[ -z "${SUPABASE_KEY}" ]]; then
        echo -e "${RED}Error: SUPABASE_KEY environment variable is not set${NC}" >&2
        echo "Please set it with: export SUPABASE_KEY='your-anon-or-service-role-key'" >&2
        return 1
    fi

    return 0
}

# GET request to Supabase
# Usage: supabase_get "/rest/v1/table_name?select=*"
supabase_get() {
    local endpoint="$1"

    if ! validate_env; then
        return 1
    fi

    curl -s -X GET \
        "${SUPABASE_URL}${endpoint}" \
        -H "apikey: ${SUPABASE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_KEY}" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}" | {
            local response=$(cat)
            local http_code=$(echo "$response" | tail -n1)
            local body=$(echo "$response" | sed '$d')

            if [[ $http_code -ge 200 && $http_code -lt 300 ]]; then
                echo "$body"
                return 0
            else
                echo -e "${RED}Error: HTTP $http_code${NC}" >&2
                echo "$body" >&2
                return 1
            fi
        }
}

# POST request to Supabase
# Usage: supabase_post "/rest/v1/table_name" '{"column": "value"}'
supabase_post() {
    local endpoint="$1"
    local data="$2"

    if ! validate_env; then
        return 1
    fi

    curl -s -X POST \
        "${SUPABASE_URL}${endpoint}" \
        -H "apikey: ${SUPABASE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_KEY}" \
        -H "Content-Type: application/json" \
        -H "Prefer: return=representation" \
        -d "$data" \
        -w "\n%{http_code}" | {
            local response=$(cat)
            local http_code=$(echo "$response" | tail -n1)
            local body=$(echo "$response" | sed '$d')

            if [[ $http_code -ge 200 && $http_code -lt 300 ]]; then
                echo "$body"
                return 0
            else
                echo -e "${RED}Error: HTTP $http_code${NC}" >&2
                echo "$body" >&2
                return 1
            fi
        }
}

# PATCH request to Supabase
# Usage: supabase_patch "/rest/v1/table_name?id=eq.1" '{"column": "new_value"}'
supabase_patch() {
    local endpoint="$1"
    local data="$2"

    if ! validate_env; then
        return 1
    fi

    curl -s -X PATCH \
        "${SUPABASE_URL}${endpoint}" \
        -H "apikey: ${SUPABASE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_KEY}" \
        -H "Content-Type: application/json" \
        -H "Prefer: return=representation" \
        -d "$data" \
        -w "\n%{http_code}" | {
            local response=$(cat)
            local http_code=$(echo "$response" | tail -n1)
            local body=$(echo "$response" | sed '$d')

            if [[ $http_code -ge 200 && $http_code -lt 300 ]]; then
                echo "$body"
                return 0
            else
                echo -e "${RED}Error: HTTP $http_code${NC}" >&2
                echo "$body" >&2
                return 1
            fi
        }
}

# DELETE request to Supabase
# Usage: supabase_delete "/rest/v1/table_name?id=eq.1"
supabase_delete() {
    local endpoint="$1"

    if ! validate_env; then
        return 1
    fi

    curl -s -X DELETE \
        "${SUPABASE_URL}${endpoint}" \
        -H "apikey: ${SUPABASE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_KEY}" \
        -H "Content-Type: application/json" \
        -H "Prefer: return=representation" \
        -w "\n%{http_code}" | {
            local response=$(cat)
            local http_code=$(echo "$response" | tail -n1)
            local body=$(echo "$response" | sed '$d')

            if [[ $http_code -ge 200 && $http_code -lt 300 ]]; then
                echo "$body"
                return 0
            else
                echo -e "${RED}Error: HTTP $http_code${NC}" >&2
                echo "$body" >&2
                return 1
            fi
        }
}

# Helper to format JSON output (requires jq)
format_json() {
    if command -v jq &> /dev/null; then
        jq '.'
    else
        cat
    fi
}

# Display success message
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Display warning message
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Display error message
error() {
    echo -e "${RED}✗ $1${NC}" >&2
}
