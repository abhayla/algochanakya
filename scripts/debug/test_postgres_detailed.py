import asyncio
import asyncpg
import sys

async def test_postgres_variations():
    print("=" * 70)
    print("DETAILED POSTGRESQL DIAGNOSTICS")
    print("=" * 70)

    test_cases = [
        {
            "name": "Test 1: Original credentials to 'algochanakya' database",
            "host": "103.118.16.189",
            "port": 5432,
            "database": "algochanakya",
            "user": "algochanakya_user",
            "password": "Alg0Ch@nakya#2024!Sec"
        },
        {
            "name": "Test 2: Connect to 'postgres' database (default)",
            "host": "103.118.16.189",
            "port": 5432,
            "database": "postgres",
            "user": "algochanakya_user",
            "password": "Alg0Ch@nakya#2024!Sec"
        },
        {
            "name": "Test 3: Try without special characters in password",
            "host": "103.118.16.189",
            "port": 5432,
            "database": "algochanakya",
            "user": "algochanakya_user",
            "password": "Alg0Chanakya2024Sec"
        },
        {
            "name": "Test 4: Try with URL-encoded password",
            "host": "103.118.16.189",
            "port": 5432,
            "database": "algochanakya",
            "user": "algochanakya_user",
            "password": "Alg0Ch%40nakya%232024!Sec"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{test['name']}")
        print("-" * 70)
        print(f"Host: {test['host']}")
        print(f"Port: {test['port']}")
        print(f"Database: {test['database']}")
        print(f"User: {test['user']}")
        print(f"Password: {test['password']}")

        try:
            conn = await asyncpg.connect(
                host=test['host'],
                port=test['port'],
                database=test['database'],
                user=test['user'],
                password=test['password'],
                timeout=5
            )

            print("[SUCCESS] Connected!")

            # Try to get version
            version = await conn.fetchval('SELECT version()')
            print(f"[SUCCESS] PostgreSQL version: {version[:60]}...")

            # Try to list databases
            databases = await conn.fetch("SELECT datname FROM pg_database WHERE datistemplate = false")
            print(f"[SUCCESS] Available databases: {[db['datname'] for db in databases]}")

            await conn.close()
            print("[SUCCESS] Connection closed")
            print("\n*** THIS CONNECTION WORKS! ***")
            return True

        except asyncpg.exceptions.InvalidPasswordError as e:
            print(f"[FAILED] Authentication Error: {e}")
        except asyncpg.exceptions.InvalidCatalogNameError as e:
            print(f"[FAILED] Database '{test['database']}' does not exist: {e}")
        except TimeoutError as e:
            print(f"[FAILED] Timeout: {e}")
        except Exception as e:
            print(f"[FAILED] Error ({type(e).__name__}): {e}")

    print("\n" + "=" * 70)
    print("ALL TESTS FAILED")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Verify the user 'algochanakya_user' exists on VPS")
    print("2. Verify the password is exactly: Alg0Ch@nakya#2024!Sec")
    print("3. Check if user has permission to connect remotely")
    print("4. Verify pg_hba.conf has entry for your IP: 116.74.160.211")
    print("\nRun these commands on VPS:")
    print("  sudo -u postgres psql -c \"\\du\"")
    print("  sudo -u postgres psql -c \"\\l\"")
    print("  sudo cat /etc/postgresql/*/main/pg_hba.conf | grep algochanakya")

    return False

if __name__ == "__main__":
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    asyncio.run(test_postgres_variations())
