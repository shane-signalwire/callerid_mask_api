# Caller ID Masking API

A simple stand-alone API using SignalWire to allow contractors (think DoorDash, Uber, etc.) to call or text (sms) clients and vice versa without giving away private information.

## Prerequisites
 - Python3
 - Service needs to be reachable via SWML and LaML webhooks thru SignalWire.
     - Recommended for testing:   An NGROK account and auth token (ngrok.com)

## Installation
1. Clone repository
```
git clone git@github.com:shane-signalwire/callerid_mask_api.git
```

2. OPTIONAL: Create and activate a Python virtual environment for the app.
```
python3 -m venv callerid_mask_api

source callerid_mask_api/bin/activate
```

3.  Install required dependencies
```
pip install -r requirements.txt
```

4.  Start the python application
```
python3 callerid_mask_api.py
```

## Configuration
In a web broswer:
1.  Navigate to <your-signalwire-space>.signalwire.com
2.  Navigate to the desired 'Phone Number'(s) and edit
3.  Set the voice settings of the number to:
    - Handle Calls Using:  A SWML Script
    - When A Call Comes In -> Use External URL for SWML Script Handler
    - https://external_path_to_the_api/calls/route
4.  Set the message settings of the number to:
    - Handle Calls Using:  LaML Webhooks
    - When A Message Comes In -> Use External URL for Message Laml Webhook handler
    - https://external_path_to_the_api/texts/route
5.  Save Settings


## Using the API:
- Add numbers to the number pool to be used for masking.  These MUST be SignalWire numbers.  Each Number in the pool MUST be pointed at the mask API in order to properly conceal Caller ID.
  NOTE: The ```phone_numbers``` param takes a comma separated list of phone numbers in E.164 format.

```
curl -X POST -H "Content-Type: application/json"  -d '{                 
    "phone_numbers": "+15551231111,+15551232222"   
}' "http://127.0.0.1:5000/api/rest/numberPool"
OK
```

- Show numbers in the Pool
```
curl  -X GET "http://127.0.0.1:5000/api/rest/numberPool"
[
  {
    "phone_number": "+15551231111",
    "in_use": 0
  },
  {
    "phone_number": "+15551232222",
    "in_use": 0
  }
]
```

- Add a new mask to link a contractor number with a client number
```
curl -X POST -H "Content-Type: application/json"  -d '{         
    "client_number": "+15559990000",
    "contractor_number": "+15558001234"
}' "http://127.0.0.1:5000/api/rest/numberMask"
{"client_number": "+15559990000", "contractor_number": "+15558001234", "mask_number": "+15551231111", "created_at": "2024-04-03 19:25:31", "expires_at": "2024-04-04 19:25:31", "deleted": 0}
```

- Show the mask bindings
  NOTE: By default, bindings expires 24 hours after creation.
```
curl  -X GET "http://127.0.0.1:5000/api/rest/numberMask/+15551231111"
[
  {
    "client_number": "+15559990000",
    "contractor_number": "+15558001234",
    "mask_number": "+15551231111",
    "created_at": "2024-04-03 19:25:31",
    "expires_at": "2024-04-04 19:25:31",
    "deleted": 0
  }
]
```

- Remove a binding
```
curl  -X DELETE "http://127.0.0.1:5000/api/rest/numberMask/+15551231111
```

- Remove a number from the number pool
```
curl  -X DELETE "http://127.0.0.1:5000/api/rest/numberPool/+15551231111
```
