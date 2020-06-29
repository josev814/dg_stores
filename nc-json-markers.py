import json
import csv

csv_file = 'dg_locations-2020-06-29.csv'

with open(csv_file, 'r') as csvh:
    reader = csv.DictReader(csvh)
    markers = []
    data = [r for r in reader]
    for item in data:
        if item['state'] == 'NC':
            marker = {
                'name': item['name'],
                'description': 'open_date: {}'.format(item['open_date']),
                'location': [
                    float(item['latitude']),
                    float(item['longitude'])
                ]
            }
            markers.append(marker)

print(json.dumps(markers))
