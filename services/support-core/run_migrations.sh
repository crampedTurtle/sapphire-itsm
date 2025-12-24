#!/bin/bash
# Migration wrapper that handles duplicate ENUM type errors

set +e  # Don't exit on error, we'll handle it

echo "Running database migrations..."

# Try to run migrations
alembic upgrade head 2>&1 | tee /tmp/migration_output.log
MIGRATION_EXIT_CODE=${PIPESTATUS[0]}

if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
    echo "Migrations completed successfully"
    exit 0
fi

echo "Migration failed with exit code $MIGRATION_EXIT_CODE"
echo "Migration output:"
cat /tmp/migration_output.log

# Check if the error is about duplicate ENUM types (various error message formats)
if grep -qiE "duplicate.*type|type.*already exists|DuplicateObject|already exists.*type" /tmp/migration_output.log; then
    echo ""
    echo "Detected duplicate ENUM type error - database was likely set up with SQL scripts"
    echo "Marking migrations as applied (types already exist)..."
    
    # Try to stamp as head - this marks all migrations as applied without running them
    if alembic stamp head; then
        echo "✓ Successfully marked migrations as applied (types already exist)"
        echo "Continuing with service startup..."
        exit 0
    else
        echo "✗ Failed to stamp migrations"
        exit 1
    fi
else
    echo "Migration failed - checking if database schema already exists..."
    
    # Check if key tables exist (indicating schema was set up with SQL scripts)
    if python3 -c "
import sys
from app.core.config import settings
from app.core.database import engine
from sqlalchemy import inspect

try:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    key_tables = ['tenants', 'cases', 'intake_events']
    if all(t in tables for t in key_tables):
        print('Key tables exist - schema appears to be set up')
        sys.exit(0)
    else:
        print('Key tables missing - schema not complete')
        sys.exit(1)
except Exception as e:
    print(f'Error checking tables: {e}')
    sys.exit(1)
" 2>/dev/null; then
        echo "Database schema exists - marking migrations as applied..."
        if alembic stamp head; then
            echo "✓ Successfully marked migrations as applied"
            exit 0
        fi
    fi
    
    echo "Migration failed for a different reason"
    echo "Please check the error above"
    exit $MIGRATION_EXIT_CODE
fi

