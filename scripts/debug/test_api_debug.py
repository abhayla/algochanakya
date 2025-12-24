import requests
import json

# Get a valid token first
auth_response = requests.post(
    "http://localhost:8000/api/auth/test-token",
    json={"user_id": 1}
)

if auth_response.status_code == 200:
    token = auth_response.json().get("token")
    print(f"Got token: {token[:20]}...")

    url = "http://localhost:8000/api/v1/autopilot/strategies"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # Simplified payload to test
    payload = {
        "name": "Test Strategy",
        "description": "Test",
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
                "entry_price": 1785
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

    print("Sending POST request...")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"\nError: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
else:
    print(f"Failed to get token: {auth_response.status_code}")
    print(auth_response.text)
