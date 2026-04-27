import requests

BASE_URL = "http://localhost:8000"

def test_custom_code():
    print("Testing custom short codes...\n")
    
    # Test 1: Create with custom code
    print("1. Creating short URL with custom code 'mytest'...")
    resp = requests.get(f"{BASE_URL}/shorten?long_url=https://google.com&custom_code=mytest")
    print(f"   Response: {resp.json()}")
    assert resp.status_code == 200
    print("   ✅ Passed\n")
    
    # Test 2: Try duplicate
    print("2. Trying to create same custom code again...")
    resp = requests.get(f"{BASE_URL}/shorten?long_url=https://google.com&custom_code=mytest")
    print(f"   Response: {resp.json()}")
    assert resp.status_code == 400
    print("   ✅ Passed (error received)\n")
    
    # Test 3: Invalid characters
    print("3. Trying invalid custom code 'test!'...")
    resp = requests.get(f"{BASE_URL}/shorten?long_url=https://google.com&custom_code=test!")
    print(f"   Response: {resp.json()}")
    assert resp.status_code == 400
    print("   ✅ Passed (error received)\n")
    
    # Test 4: Random code (no custom)
    print("4. Creating URL without custom code...")
    resp = requests.get(f"{BASE_URL}/shorten?long_url=https://google.com")
    data = resp.json()
    print(f"   Got short code: {data['short_code']}")
    assert len(data['short_code']) == 6
    print("   ✅ Passed\n")
    
    # Test 5: Visit the short URL
    print("5. Visiting the short URL...")
    resp = requests.get(f"{BASE_URL}/mytest", allow_redirects=False)
    print(f"   Redirect status: {resp.status_code}")
    assert resp.status_code == 307
    print("   ✅ Passed\n")
    
    # Test 6: Check stats
    print("6. Checking stats...")
    resp = requests.get(f"{BASE_URL}/stats/mytest")
    print(f"   Stats: {resp.json()}")
    assert resp.status_code == 200
    print("   ✅ Passed\n")
    
    print("🎉 All tests passed!")

if __name__ == "__main__":
    test_custom_code()