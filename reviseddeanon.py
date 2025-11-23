import csv
from collections import defaultdict, Counter
from datetime import datetime

# Load your data
def load_data(filename):
    trips = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips.append(row)
    return trips

data = load_data('202510-bluebikes-tripdata.csv')

print("=" * 80)
print("DE-ANONYMIZATION ANALYSIS")
print("Finding trips that are likely the SAME PERSON")
print("=" * 80)
print(f"Total trips in dataset: {len(data)}\n")

# Parse all trips with time info
parsed_trips = []
for trip in data:
    try:
        dt = datetime.strptime(trip['started_at'], '%Y-%m-%d %H:%M:%S.%f')
        parsed_trips.append({
            'ride_id': trip['ride_id'],
            'route': f"{trip['start_station_name']} -> {trip['end_station_name']}",
            'start_station': trip['start_station_name'],
            'end_station': trip['end_station_name'],
            'datetime': dt,
            'date': dt.strftime('%Y-%m-%d'),
            'time': dt.strftime('%H:%M'),
            'hour': dt.hour,
            'minute': dt.minute,
            'day_of_week': dt.weekday(),
            'time_in_minutes': dt.hour * 60 + dt.minute,
            'member_type': trip['member_casual']
        })
    except:
        continue

print(f"Successfully parsed: {len(parsed_trips)} trips\n")

# Group by route
routes = defaultdict(list)
for trip in parsed_trips:
    routes[trip['route']].append(trip)

print(f"Total unique routes: {len(routes)}\n")

# Find routes with repeated patterns (likely same person)
print("=" * 80)
print("FINDING IDENTIFYING PATTERNS")
print("=" * 80)

results = []

for route, route_trips in routes.items():
    if len(route_trips) < 2:
        continue
    
    # For each route, find time clusters (trips within 30 min of each other)
    time_clusters = []
    used_trips = set()
    
    for i, trip1 in enumerate(route_trips):
        if trip1['ride_id'] in used_trips:
            continue
            
        cluster = [trip1]
        used_trips.add(trip1['ride_id'])
        
        for trip2 in route_trips[i+1:]:
            if trip2['ride_id'] in used_trips:
                continue
            
            # Check if within 30 minutes of any trip in cluster
            for cluster_trip in cluster:
                time_diff = abs(trip1['time_in_minutes'] - trip2['time_in_minutes'])
                if time_diff <= 30:
                    cluster.append(trip2)
                    used_trips.add(trip2['ride_id'])
                    break
        
        if len(cluster) >= 2:
            time_clusters.append(cluster)
    
    # Analyze each cluster
    for cluster in time_clusters:
        if len(cluster) >= 2:  # At least 2 trips
            # Calculate average time
            avg_time_min = sum(t['time_in_minutes'] for t in cluster) / len(cluster)
            avg_hour = int(avg_time_min // 60)
            avg_minute = int(avg_time_min % 60)
            
            # Check if commute time
            is_morning_commute = 6 <= avg_hour <= 9
            is_evening_commute = 16 <= avg_hour <= 19
            
            # Determine privacy risk
            if len(cluster) >= 4:
                risk = "CRITICAL"
            elif len(cluster) >= 3:
                risk = "HIGH"
            else:
                risk = "MEDIUM"
            
            trip_type = "Morning Commute" if is_morning_commute else "Evening Commute" if is_evening_commute else "Regular Pattern"
            
            # Add each trip in the cluster to results
            for trip in cluster:
                results.append({
                    'Pattern_ID': f"{route[:30]}|{avg_hour:02d}:{avg_minute:02d}",
                    'Trips_In_Pattern': len(cluster),
                    'Privacy_Risk': risk,
                    'Likely_Same_Person': 'YES - High Confidence' if len(cluster) >= 3 else 'YES - Probable',
                    'Pattern_Type': trip_type,
                    'Route': route,
                    'Start_Station': trip['start_station'],
                    'End_Station': trip['end_station'],
                    'Avg_Time_Window': f"{avg_hour:02d}:{avg_minute:02d}",
                    'This_Trip_Date': trip['date'],
                    'This_Trip_Time': trip['time'],
                    'This_Trip_Day': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][trip['day_of_week']],
                    'Ride_ID': trip['ride_id'],
                    'Member_Type': trip['member_type'],
                    'De_Anonymization_Method': f'{len(cluster)} trips on same route within 30min window'
                })

# Sort by pattern size (most identifying first)
results.sort(key=lambda x: x['Trips_In_Pattern'], reverse=True)

# Write to CSV
output_file = 'deanonymization_results.csv'
if results:
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    # Summary statistics
    patterns = defaultdict(list)
    for r in results:
        patterns[r['Pattern_ID']].append(r)
    
    print(f"\n✓ RESULTS:")
    print(f"  Total identifying patterns found: {len(patterns)}")
    print(f"  Total trips that can be linked: {len(results)}")
    print(f"  These trips likely belong to {len(patterns)} different people")
    print(f"\n✓ Breakdown by pattern size:")
    
    pattern_sizes = Counter([r['Trips_In_Pattern'] for r in results])
    for size in sorted(pattern_sizes.keys(), reverse=True):
        count = pattern_sizes[size]
        print(f"    {size} trips in pattern: {count} instances")
    
    print(f"\n✓ Output saved to: {output_file}")
    print(f"  Open in Excel to see all de-anonymized patterns!")
    
    print(f"\n" + "=" * 80)
    print("INTERPRETATION:")
    print("  Each 'Pattern_ID' represents likely the SAME PERSON")
    print("  Multiple ride_ids with same route + time = one individual")
    print("  Even with 'anonymous' ride IDs, behavior reveals identity!")
    print("=" * 80)
else:
    print("\nNo repeated patterns found.")
    print("Try adjusting thresholds or check if dataset has enough trips.")