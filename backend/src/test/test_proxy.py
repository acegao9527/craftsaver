import os
import requests
import sys

def test_proxy(proxy_url):
    print(f"Testing proxy: {proxy_url}")
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }
    
    try:
        print("Attempting to connect to Telegram API...")
        # 设置较短的超时时间
        response = requests.get("https://api.telegram.org/getMe", proxies=proxies, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response: {response.json()}")
        except:
            print(f"Response Text: {response.text}")
            
        if response.status_code in [200, 401, 404]:
            print("\n✅ SUCCESS! The proxy is working and can reach Telegram.")
            print("(Note: 401/404 is normal here because we didn't provide a valid Bot Token, but it proves connectivity)")
        else:
            print("\n❌ FAILED. Server returned unexpected status.")
            
    except requests.exceptions.ProxyError as e:
        print(f"\n❌ PROXY ERROR: {e}")
        print("Tip: If you see '405 Method Not Allowed', the server is refusing to act as a proxy.")
        print("     Try changing 'https://' to 'http://' in your proxy URL.")
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ CONNECTION ERROR: {e}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://baxian:shentong@www.la.cloudailab.org:443"
    
    if not url:
        print("Please provide a proxy URL as an argument or set TELEGRAM_PROXY_URL env var.")
        print("Usage: python3 test_proxy.py http://user:pass@host:port")
        sys.exit(1)
        
    test_proxy(url)
