#!/bin/bash
# Knowledge Base Query Helper
# Usage: ./query-knowledge.sh "ERROR_TYPE" "error_message" "file/path"

ERROR_TYPE=$1
ERROR_MSG=$2
FILE_PATH=$3

# Change to learning directory
cd .claude/learning 2>/dev/null || {
    echo "SKIP: Learning engine not found"
    exit 0
}

# Query with 5-second timeout
timeout 5s python3 << EOF 2>/dev/null || {
    echo "SKIP: Knowledge base query timed out"
    exit 0
}

import sys
sys.path.insert(0, '.')

try:
    from db_helper import record_error, get_strategies

    # Record/retrieve error pattern
    error_id = record_error(
        error_type='$ERROR_TYPE',
        message='$ERROR_MSG',
        file_path='$FILE_PATH'
    )

    # Get top 3 ranked strategies (cap to prevent trying too many)
    strategies = get_strategies('$ERROR_TYPE', limit=3)

    if strategies:
        print('✨ KNOWN PATTERN - Top 3 ranked fixes:')
        for i, s in enumerate(strategies, 1):
            if s['effective_score'] >= 0.3:
                confidence = "🟢 HIGH" if s['effective_score'] >= 0.7 else "🟡 MEDIUM"
                print(f'{i}. [{s["effective_score"]:.2f}] {confidence}: {s["name"]}')
                print(f'   → {s["description"]}')
                if s['effective_score'] >= 0.7:
                    print(f'   ⚡ RECOMMENDED: Try this first!')
        print()
        print(f'Error ID: {error_id} (use for tracking)')
    else:
        print('🆕 UNKNOWN PATTERN - Will record new pattern when fixed')
        print(f'Error ID: {error_id}')

except Exception as e:
    print(f'⚠️  Knowledge base error: {e}')
    print('Proceeding with standard diagnosis...')
    sys.exit(0)
EOF
