import httpx
import gc
import sys

def test_leak():
    client = httpx.Client()
    for _ in range(100):
        resp = client.get("https://google.com")
        resp.close() # we do call close
        
    print(len(gc.get_objects()))

test_leak()
