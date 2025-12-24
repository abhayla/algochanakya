import requests
import json

url = "http://localhost:8000/api/v1/autopilot/strategies"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test_token_for_user_1"
}

payload = {
    "name": "Test SHORT-STRANGLE",
    "description": "Test Decimal serialization",
    "underlying": "NIFTY",
    "expiry_type": "WEEKLY",
    "expiry_date": "2025-01-01",
    "lots": 1,
    "position_type": "SHORT",
    "legs_config": [
        {
            "option_type": "CE",
            "strike_selection": {
                "type": "ATM",
                "offset": 0
            }
        }
    ],
    "entry_conditions": {
        "time_entry": {
            "enabled": True,
            "entry_time": "09:20"
        }
    },
    "adjustment_rules": [],
    "order_settings": {},
    "risk_settings": {
        "max_loss": 15000,
        "max_profit": 10000
    },
    "schedule_config": {},
    "priority": 1
}

try:
    print("Testing strategy creation API...")
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'response'):
        print(f"Response: {e.response.text}")
