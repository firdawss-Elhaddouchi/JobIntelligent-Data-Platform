import requests
import pandas  as pd
api_keys = '5f08f697-2811-4c29-b1dd-77db0440416b'
base_url = 'https://www.reed.co.uk/api/1.0/search'# ?keywords=accountant&location=london&employerid=123&distancefromlocation=15'
prm = {'keywords':'data','location':'london'}
response = requests.get(base_url,auth=(api_keys,''))
if response.status_code == 200:
    rep = response.json()['results']

df = pd.DataFrame(rep)
df.to_csv('df.csv')
# Save as lines (JSONL format)
df.to_json('df.json', orient='records', lines=True)
print(df)
