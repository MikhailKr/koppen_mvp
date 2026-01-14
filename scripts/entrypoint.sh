#!/bin/bash
set -e

# Database connection check function
wait_for_db() {
    local host=$1
    local port=$2
    local user=$3
    local db=$4
    local max_attempts=30
    local attempt=1

    echo "Waiting for database to be ready at $host:$port..."

    while [ $attempt -le $max_attempts ]; do
        if python3 -c "
import asyncpg
import asyncio
import sys

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host='$host',
            port=$port,
            user='$user',
            password='$POSTGRES_PASSWORD',
            database='$db'
        )
        await conn.close()
        return True
    except Exception as e:
        print(f'Connection failed: {e}', file=sys.stderr)
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
" 2>/dev/null; then
            echo "Database is ready!"
            return 0
        fi

        echo "Attempt $attempt/$max_attempts: Database not ready, waiting..."
        sleep 2
        ((attempt++))
    done

    echo "Database connection failed after $max_attempts attempts"
    return 1
}

# Wait for database to be ready
wait_for_db "$POSTGRES_HOST" "$POSTGRES_PORT" "$POSTGRES_USER" "$POSTGRES_DB"

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"

