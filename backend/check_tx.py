import requests

ADDRESS = '0xa30A689ec0F9D717C5bA1098455B031b868B720f'

url = f'https://api.basescan.org/api?module=account&action=txlist&address={ADDRESS}&startblock=0&endblock=99999999&page=1&offset=5&sort=desc'

try:
    resp = requests.get(url, timeout=10)
    data = resp.json()
    if data['status'] == '1':
        print('Recent transactions:')
        for tx in data['result'][:5]:
            status = 'SUCCESS' if tx['isError'] == '0' else 'FAILED'
            print(f"  TX: {tx['hash'][:20]}...")
            print(f"      Block: {tx['blockNumber']}")
            print(f"      Status: {status}")
            print()
    else:
        print(f"API error: {data['message']}")
except Exception as e:
    print(f'Error: {e}')
