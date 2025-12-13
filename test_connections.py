import asyncio
import asyncpg
import sys

async def test_postgres():
    print("=" * 60)
    print("TESTING POSTGRESQL CONNECTION")
    print("=" * 60)
    print("Host: 103.118.16.189")
    print("Port: 5432")
    print("Database: algochanakya")
    print("Username: algochanakya_user")
    print("Password: Alg0Ch@nakya#2024!Sec")
    print("-" * 60)

    try:
        conn = await asyncpg.connect(
            host='103.118.16.189',
            port=5432,
            database='algochanakya',
            user='algochanakya_user',
            password='Alg0Ch@nakya#2024!Sec',
            timeout=10
        )

        print("[SUCCESS] Connection successful!")

        # Test a simple query
        result = await conn.fetchval('SELECT version()')
        print(f"[SUCCESS] PostgreSQL version: {result[:50]}...")

        # Check if we can query
        result = await conn.fetchval('SELECT 1')
        print(f"[SUCCESS] Test query result: {result}")

        await conn.close()
        print("[SUCCESS] Connection closed")
        return True

    except asyncpg.exceptions.InvalidPasswordError as e:
        print(f"[FAILED] Authentication Error: {e}")
        print("\nPossible causes:")
        print("1. Password is incorrect")
        print("2. User 'algochanakya_user' may not exist")
        print("3. User exists but password is different")
        return False
    except asyncpg.exceptions.InvalidCatalogNameError as e:
        print(f"[FAILED] Database Error: {e}")
        print("\nThe database 'algochanakya' does not exist on the server")
        return False
    except TimeoutError as e:
        print(f"[FAILED] Connection Timeout: {e}")
        print("\nThe server is not responding (firewall issue)")
        return False
    except OSError as e:
        print(f"[FAILED] Network Error: {e}")
        print("\nCannot reach the server")
        return False
    except Exception as e:
        print(f"[FAILED] Unexpected Error: {type(e).__name__}: {e}")
        return False

async def test_redis():
    print("\n" + "=" * 60)
    print("TESTING REDIS CONNECTION")
    print("=" * 60)
    print("Host: 103.118.16.189")
    print("Port: 6379")
    print("Database: 1")
    print("-" * 60)

    try:
        import redis.asyncio as aioredis

        redis = await aioredis.from_url(
            'redis://103.118.16.189:6379/1',
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=10
        )

        print("[SUCCESS] Connection created!")

        # Test ping
        result = await redis.ping()
        print(f"[SUCCESS] PING response: {result}")

        # Test set/get
        await redis.set('test_key', 'test_value')
        value = await redis.get('test_key')
        print(f"[SUCCESS] SET/GET test: {value}")

        await redis.close()
        print("[SUCCESS] Connection closed")
        return True

    except TimeoutError as e:
        print(f"[FAILED] Connection Timeout: {e}")
        print("\nRedis server is not responding (firewall issue)")
        return False
    except Exception as e:
        print(f"[FAILED] Error: {type(e).__name__}: {e}")
        return False

async def main():
    postgres_ok = await test_postgres()
    redis_ok = await test_redis()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"PostgreSQL: {'PASSED' if postgres_ok else 'FAILED'}")
    print(f"Redis:      {'PASSED' if redis_ok else 'FAILED'}")
    print("=" * 60)

if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    asyncio.run(main())
