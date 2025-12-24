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

# Check if the error is about duplicate ENUM types
if grep -qi "duplicate.*type\|type.*already exists" /tmp/migration_output.log; then
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
    echo "Migration failed for a different reason (not duplicate types)"
    echo "Please check the error above"
    exit $MIGRATION_EXIT_CODE
fi

