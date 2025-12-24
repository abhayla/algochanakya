import asyncio
import asyncpg
import psycopg2
import sys

def test_with_psycopg2():
    """Test with psycopg2 (synchronous)"""
    print("=" * 70)
    print("TEST 1: Using psycopg2 (standard synchronous driver)")
    print("=" * 70)

    try:
        # Test 1: Using parameters
        print("\nMethod A: Using connection parameters")
        print("-" * 70)
        conn = psycopg2.connect(
            host='103.118.16.189',
            port=5432,
            database='algochanakya',
            user='algochanakya_user',
            password='Alg0Ch@nakya#2024!Sec'
        )

        print("[SUCCESS] Connected with parameters!")

        cursor = conn.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()[0]
        print(f"[SUCCESS] PostgreSQL version: {version[:60]}...")

        cursor.execute('SELECT 1')
        result = cursor.fetchone()[0]
        print(f"[SUCCESS] Test query: {result}")

        cursor.close()
        conn.close()
        print("[SUCCESS] Connection closed")
        return True

    except psycopg2.OperationalError as e:
        print(f"[FAILED] psycopg2 with parameters: {e}")
    except Exception as e:
        print(f"[FAILED] Unexpected error: {type(e).__name__}: {e}")

    try:
        # Test 2: Using connection string
        print("\nMethod B: Using connection string (URL-encoded)")
        print("-" * 70)
        conn_string = "postgresql://algochanakya_user:Alg0Ch%40nakya%232024!Sec@103.118.16.189:5432/algochanakya"
        print(f"Connection string: {conn_string}")

        conn = psycopg2.connect(conn_string)

        print("[SUCCESS] Connected with connection string!")

        cursor = conn.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()[0]
        print(f"[SUCCESS] PostgreSQL version: {version[:60]}...")

        cursor.close()
        conn.close()
        print("[SUCCESS] Connection closed")
        return True

    except psycopg2.OperationalError as e:
        print(f"[FAILED] psycopg2 with connection string: {e}")
    except Exception as e:
        print(f"[FAILED] Unexpected error: {type(e).__name__}: {e}")

    return False

async def test_with_asyncpg():
    """Test with asyncpg (asynchronous)"""
    print("\n" + "=" * 70)
    print("TEST 2: Using asyncpg (async driver - what FastAPI uses)")
    print("=" * 70)

    try:
        # Test 1: Using parameters
        print("\nMethod A: Using connection parameters")
        print("-" * 70)
        conn = await asyncpg.connect(
            host='103.118.16.189',
            port=5432,
            database='algochanakya',
            user='algochanakya_user',
            password='Alg0Ch@nakya#2024!Sec',
            timeout=10
        )

        print("[SUCCESS] Connected with parameters!")

        version = await conn.fetchval('SELECT version()')
        print(f"[SUCCESS] PostgreSQL version: {version[:60]}...")

        result = await conn.fetchval('SELECT 1')
        print(f"[SUCCESS] Test query: {result}")

        await conn.close()
        print("[SUCCESS] Connection closed")
        return True

    except Exception as e:
        print(f"[FAILED] asyncpg with parameters: {type(e).__name__}: {e}")

    try:
        # Test 2: Using connection string with asyncpg
        print("\nMethod B: Using connection string")
        print("-" * 70)
        conn_string = "postgresql://algochanakya_user:Alg0Ch%40nakya%232024!Sec@103.118.16.189:5432/algochanakya"
        print(f"Connection string: {conn_string}")

        conn = await asyncpg.connect(conn_string, timeout=10)

        print("[SUCCESS] Connected with connection string!")

        version = await conn.fetchval('SELECT version()')
        print(f"[SUCCESS] PostgreSQL version: {version[:60]}...")

        await conn.close()
        print("[SUCCESS] Connection closed")
        return True

    except Exception as e:
        print(f"[FAILED] asyncpg with connection string: {type(e).__name__}: {e}")

    return False

async def main():
    # Test with psycopg2 (sync)
    psycopg2_ok = test_with_psycopg2()

    # Test with asyncpg (async)
    asyncpg_ok = await test_with_asyncpg()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"psycopg2 (sync):  {'PASSED' if psycopg2_ok else 'FAILED'}")
    print(f"asyncpg (async):  {'PASSED' if asyncpg_ok else 'FAILED'}")
    print("=" * 70)

if __name__ == "__main__":
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    asyncio.run(main())
