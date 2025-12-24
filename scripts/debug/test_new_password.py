import asyncio
import asyncpg
import redis.asyncio as aioredis
import sys

async def test_postgres():
    print("=" * 70)
    print("TESTING POSTGRESQL CONNECTION (NEW PASSWORD)")
    print("=" * 70)
    print("Host: 103.118.16.189")
    print("Port: 5432")
    print("Database: algochanakya")
    print("Username: algochanakya_user")
    print("Password: AlgoChanakya2024Secure")
    print("-" * 70)

    try:
        conn = await asyncpg.connect(
            host='103.118.16.189',
            port=5432,
            database='algochanakya',
            user='algochanakya_user',
            password='AlgoChanakya2024Secure',
            timeout=10
        )

        print("[SUCCESS] Connection established!")

        # Test query
        version = await conn.fetchval('SELECT version()')
        print(f"[SUCCESS] PostgreSQL version: {version[:70]}...")

        result = await conn.fetchval('SELECT 1')
        print(f"[SUCCESS] Test query result: {result}")

        # List tables
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """)
        print(f"[SUCCESS] Tables in database: {len(tables)} tables")

        await conn.close()
        print("[SUCCESS] Connection closed successfully")
        return True

    except Exception as e:
        print(f"[FAILED] {type(e).__name__}: {e}")
        return False

async def test_redis():
    print("\n" + "=" * 70)
    print("TESTING REDIS CONNECTION")
    print("=" * 70)
    print("Host: 103.118.16.189")
    print("Port: 6379")
    print("Database: 1")
    print("-" * 70)

    try:
        redis = await aioredis.from_url(
            'redis://103.118.16.189:6379/1',
            encoding="utf-8",
            decode_responses=True
        )

        print("[SUCCESS] Connection established!")

        # Test ping
        result = await redis.ping()
        print(f"[SUCCESS] PING: {result}")

        # Test set/get
        await redis.set('algochanakya_test', 'working')
        value = await redis.get('algochanakya_test')
        print(f"[SUCCESS] SET/GET test: {value}")

        await redis.aclose()
        print("[SUCCESS] Connection closed successfully")
        return True

    except Exception as e:
        print(f"[FAILED] {type(e).__name__}: {e}")
        return False

async def main():
    postgres_ok = await test_postgres()
    redis_ok = await test_redis()

    print("\n" + "=" * 70)
    print("CONNECTION TEST SUMMARY")
    print("=" * 70)
    print(f"PostgreSQL: {'✓ PASSED' if postgres_ok else '✗ FAILED'}")
    print(f"Redis:      {'✓ PASSED' if redis_ok else '✗ FAILED'}")
    print("=" * 70)

    if postgres_ok and redis_ok:
        print("\n[SUCCESS] All connections working! Ready to start backend server.")
        return 0
    else:
        print("\n[FAILED] Some connections failed. Please check configuration.")
        return 1

if __name__ == "__main__":
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
