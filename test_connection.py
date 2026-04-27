# test_connection.py
import redis
import psycopg2

print("=" * 50)
print("Testing Connections for URL Shortener")
print("=" * 50)

# Test 1: Redis
print("\n1. Testing Redis (Memurai)...")
try:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.set('test', 'Redis is working on your machine!')
    result = r.get('test')
    print(f"   ✅ SUCCESS: {result}")
except Exception as e:
    print(f"   ❌ FAILED: {e}")

# Test 2: PostgreSQL
print("\n2. Testing PostgreSQL...")
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='postgres',  # or 'url_shortener' if you created it
        user='postgres',
        password='postgres'  # <--- CHANGE THIS to your actual PostgreSQL password
    )
    cursor = conn.cursor()
    cursor.execute("SELECT 'PostgreSQL is ready!' as message;")
    result = cursor.fetchone()
    print(f"   ✅ SUCCESS: {result[0]}")
    conn.close()
except Exception as e:
    print(f"   ❌ FAILED: {e}")

print("\n" + "=" * 50)
print("If you see two ✅ SUCCESS messages, Phase 1 is complete!")
print("=" * 50)