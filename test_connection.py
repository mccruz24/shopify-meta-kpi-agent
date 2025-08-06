import requests
import os
from dotenv import load_dotenv

load_dotenv()

shop_url = os.getenv('SHOPIFY_SHOP_URL')
access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')

print(f'Shop URL: {shop_url}')
print(f'Token: {access_token[:20]}...')

headers = {'X-Shopify-Access-Token': access_token}
url = f'https://{shop_url}/admin/api/2023-10/shop.json'

print(f'Testing URL: {url}')
response = requests.get(url, headers=headers)
print(f'Status: {response.status_code}')
if response.status_code != 200:
    print(f'Error: {response.text}')
else:
    print('✅ Connection successful!')
    data = response.json()
    print(f'Shop: {data.get("shop", {}).get("name", "Unknown")}')