import asyncio
import asyncpg

async def test_postgres():
    print("Testing PostgreSQL connection...")
    print("Host: 103.118.16.189")
    print("Port: 5432")
    print("Database: algochanakya")
    print("Username: algochanakya_user")
    print("-" * 50)

    try:
        conn = await asyncpg.connect(
            host='103.118.16.189',
            port=5432,
            database='algochanakya',
            user='algochanakya_user',
            password='Alg0Ch@nakya#2024!Sec',
            timeout=10
        )

        print("✓ Connection successful!")

        # Test a simple query
        result = await conn.fetchval('SELECT version()')
        print(f"✓ PostgreSQL version: {result}")

        # Check if we can query
        result = await conn.fetchval('SELECT 1')
        print(f"✓ Test query result: {result}")

        await conn.close()
        print("✓ Connection closed successfully")

    except asyncpg.exceptions.InvalidPasswordError as e:
        print(f"✗ Authentication failed: {e}")
    except asyncpg.exceptions.InvalidCatalogNameError as e:
        print(f"✗ Database does not exist: {e}")
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        print(f"✗ Connection lost: {e}")
    except TimeoutError as e:
        print(f"✗ Connection timeout: {e}")
    except OSError as e:
        print(f"✗ Network error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_postgres())
