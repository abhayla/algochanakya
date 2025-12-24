"""
Test script to verify error handling and visibility in AutoPilot strategy creation.
Run this after restarting the backend with the new error handling code.
"""
import requests
import json

# Get a valid token first
print("Step 1: Getting authentication token...")
auth_response = requests.post(
    "http://localhost:8000/api/auth/test-token",
    json={"user_id": 1}
)

if auth_response.status_code == 200:
    token = auth_response.json().get("token")
    print(f"✓ Got token: {token[:20]}...")

    url = "http://localhost:8000/api/v1/autopilot/strategies"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # Test payload - same as E2E test
    payload = {
        "name": "Test SHORT-STRANGLE",
        "description": "Test error visibility",
        "underlying": "NIFTY",
        "expiry_type": "current_week",
        "expiry_date": None,
        "lots": 1,
        "position_type": "positional",
        "legs_config": [
            {
                "id": "leg_1",
                "transaction_type": "SELL",
                "contract_type": "CE",
                "strike_selection": {"mode": "fixed", "fixed_strike": 24150},
                "strike_price": 24150,
                "expiry_date": "2025-12-23",
                "lots": 1,
                "entry_price": 1785,
                "target_price": None,
                "stop_loss_price": None,
                "trailing_stop": False
            },
            {
                "id": "leg_2",
                "transaction_type": "SELL",
                "contract_type": "PE",
                "strike_selection": {"mode": "fixed", "fixed_strike": 27800},
                "strike_price": 27800,
                "expiry_date": "2025-12-23",
                "lots": 1,
                "entry_price": 1960,
                "target_price": None,
                "stop_loss_price": None,
                "trailing_stop": False
            }
        ],
        "entry_conditions": {"logic": "AND", "conditions": []},
        "adjustment_rules": [],
        "order_settings": {
            "order_type": "MARKET",
            "execution_style": "sequential"
        },
        "risk_settings": {
            "max_loss": 15000,
            "max_profit": 10000
        },
        "schedule_config": {},
        "priority": 100
    }

    print("\nStep 2: Testing strategy creation...")
    print(f"Sending POST request to {url}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"\n✓ Status Code: {response.status_code}")

        if response.status_code == 201:
            print("✓ SUCCESS! Strategy created successfully")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Response: {json.dumps(response.json(), indent=2)}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
else:
    print(f"✗ Failed to get token: {auth_response.status_code}")
    print(auth_response.text)

print("\n" + "="*60)
print("If you see detailed error messages above (not just 'Network Error'),")
print("then the error handling is working correctly!")
print("="*60)
