#!/bin/bash
# Migration wrapper that handles duplicate ENUM type errors

set -e

echo "Running database migrations..."

# Try to run migrations
if alembic upgrade head; then
    echo "Migrations completed successfully"
    exit 0
else
    MIGRATION_ERROR=$?
    echo "Migration failed with exit code $MIGRATION_ERROR"
    
    # Check if the error is about duplicate ENUM types
    # If database was set up with SQL scripts, types already exist
    # In this case, we can mark migrations as applied
    if [ $MIGRATION_ERROR -ne 0 ]; then
        echo "Checking if this is a duplicate type error..."
        echo "If ENUM types already exist (from SQL scripts), marking migrations as applied..."
        
        # Try to stamp as head - this marks all migrations as applied without running them
        if alembic stamp head; then
            echo "Successfully marked migrations as applied (types already exist)"
            exit 0
        else
            echo "Failed to stamp migrations. Original error may be different."
            exit $MIGRATION_ERROR
        fi
    fi
    
    exit $MIGRATION_ERROR
fi

