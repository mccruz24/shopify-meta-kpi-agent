#!/usr/bin/env python3
"""
Simple test script to verify environment variables are loaded correctly
"""

import os

print("=== Environment Variables Test ===")
print(f"Current working directory: {os.getcwd()}")

print("\n--- All Environment Variables ---")
for key, value in sorted(os.environ.items()):
    if any(prefix in key.upper() for prefix in ['SHOPIFY', 'META', 'PRINTIFY', 'NOTION']):
        # Mask sensitive values
        if 'TOKEN' in key.upper() or 'SECRET' in key.upper():
            display_value = f"{value[:20]}..." if value and len(value) > 20 else value
        else:
            display_value = value
        print(f"{key}: {display_value}")

print("\n--- Specific Shopify Variables ---")
shopify_url = os.getenv('SHOPIFY_SHOP_URL')
shopify_token = os.getenv('SHOPIFY_ACCESS_TOKEN')

print(f"SHOPIFY_SHOP_URL: {shopify_url}")
print(f"SHOPIFY_ACCESS_TOKEN: {shopify_token[:20] if shopify_token else 'None'}...")

if shopify_url and shopify_token:
    print("✅ Both Shopify environment variables are set")
    print(f"   Shop URL: {shopify_url}")
    print(f"   Token length: {len(shopify_token)} characters")
    print(f"   Token starts with: {shopify_token[:10]}...")
else:
    print("❌ Missing Shopify environment variables:")
    if not shopify_url:
        print("   - SHOPIFY_SHOP_URL is not set")
    if not shopify_token:
        print("   - SHOPIFY_ACCESS_TOKEN is not set")

print("\n--- Test Complete ===")
