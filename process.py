import argparse
import time
import requests
import json
import os
import numpy as np
from lib.geo import snap, haversine_distance
from lib.debug import DataExchangeDebugger
from lib.tracks import fetch_tracks
from lib.output import SegmentProcessingOutput

def current_milli_time():
    return round(time.time() * 1000)

def get_time_of_last_bucket():
    index_path = 'static/index.json'
    with open(index_path, 'r') as f:
        index = json.load(f)
    last_time = 0
    for file in index["files"]:
        if file["end_time"] > last_time:
            last_time = file["end_time"]
    if last_time == 0:
        # 2023-01-01 00:00:00
        last_time = 1672531200000
    return last_time

def process_segments(tracking_service_url, tracking_service_api_key, graphhopper_service_url, start_time, end_time, use_debugging=False):
    tracks = fetch_tracks(tracking_service_url, tracking_service_api_key, start_time, end_time)
    
    data_exchange_debugger = DataExchangeDebugger(active=use_debugging)
    output = SegmentProcessingOutput()

    track_idx = 0
    for track, bike_type, gps_data in tracks:
        if track_idx % 100 == 0:
            print(f"{track_idx} tracks processed")
        
        # Skip too short or invalid tracks
        if len(gps_data) < 2:
            output.too_short_tracks_count += 1
            continue
        if 'latitude' not in gps_data.columns or 'longitude' not in gps_data.columns:
            print("No latitude or longitude in gps data")
            print(f"Track: pk {track['pk']}, sessionId {track['sessionId']}, userId {track['userId']}")
            output.invalid_tracks_count += 1
            continue
        data_exchange_debugger.new_geojson()
        
        gpx = "<gpx><trk><trkseg>"
        for _, coordinates in gps_data.iterrows():
            gpx += f"<trkpt lat=\"{coordinates['latitude']}\" lon=\"{coordinates['longitude']}\"></trkpt>"
            data_exchange_debugger.add_track_point(coordinates['longitude'], coordinates['latitude'])
        gpx += "</trkseg></trk></gpx>"
        
        # Send to graphhopper map matching api
        response = requests.post(
            f"{graphhopper_service_url}/match?profile=bike2_default&points_encoded=false&instructions=false",
            data=gpx, 
            headers={'Content-Type': 'application/gpx+xml'},
        )
        
        response_data = response.json()
        
        if "paths" not in response_data:
            print("Error in GraphHopper response")
            print(f"Track: pk {track['pk']}, sessionId {track['sessionId']}, userId {track['userId']}")
            output.tracks_with_map_matching_error_count += 1
            continue
        
        if len(response_data["paths"]) != 1:
            print("Invalid number of paths in GraphHopper response")
            print(f"Track: pk {track['pk']}, sessionId {track['sessionId']}, userId {track['userId']}")
            output.tracks_with_invalid_map_matching_count += 1
            continue
        
        points = response_data["paths"][0]["points"]["coordinates"]
        
        for point in points:
            data_exchange_debugger.add_map_matched_point(point[0], point[1])
        
        gps_point_idx = 0
        
        for point_idx in range(len(points) - 1):
            # Anonyimze by skipping the first and last segment
            if point_idx == 0 or point_idx >= len(points) - 2:
                continue
                      
            point_lng_lat = (points[point_idx][0], points[point_idx][1])
            next_point_lng_lat = (points[point_idx + 1][0], points[point_idx + 1][1])
            segment = (point_lng_lat, next_point_lng_lat)
            
            output.add_segment(segment)
            
            if gps_point_idx >= len(gps_data.index):
                continue
            
            if point_idx < len(points) - 2:
                next_next_point_lng_lat = (points[point_idx + 2][0], points[point_idx + 2][1])
                next_segment = (next_point_lng_lat, next_next_point_lng_lat)
            else:
                next_segment = None
            
            gpx_point_on_segment = True
            
            speeds_on_segment = []
            speeds_on_segment.append(gps_data.iloc[[gps_point_idx]]["speed"].item())
            data_exchange_debugger.add_snapping_line(segment, gps_data.iloc[[gps_point_idx]]["longitude"].item(), gps_data.iloc[[gps_point_idx]]["latitude"].item())
            gps_point_idx += 1
            
            while gpx_point_on_segment and gps_point_idx < len(gps_data.index) - 2:
                if next_segment is None:
                    speeds_on_segment.append(gps_data.iloc[[gps_point_idx]]["speed"].item())
                    data_exchange_debugger.add_snapping_line(segment, gps_data.iloc[[gps_point_idx]]["longitude"].item(), gps_data.iloc[[gps_point_idx]]["latitude"].item())
                    gps_point_idx += 1
                    continue
            
                snapped_to_segment = snap(
                    gps_data.iloc[[gps_point_idx]]["longitude"].item(),
                    gps_data.iloc[[gps_point_idx]]["latitude"].item(),
                    segment[0][0],
                    segment[0][1],
                    segment[1][0],
                    segment[1][1],
                )
                distance_to_segment = haversine_distance(
                    gps_data.iloc[[gps_point_idx]]["longitude"].item(),
                    gps_data.iloc[[gps_point_idx]]["latitude"].item(),
                    snapped_to_segment[0],
                    snapped_to_segment[1],
                )
                snapped_to_next_segment = snap(
                    gps_data.iloc[[gps_point_idx]]["longitude"].item(),
                    gps_data.iloc[[gps_point_idx]]["latitude"].item(),
                    next_segment[0][0],
                    next_segment[0][1],
                    next_segment[1][0],
                    next_segment[1][1],
                )
                distance_to_next_segment = haversine_distance(
                    gps_data.iloc[[gps_point_idx]]["longitude"].item(),
                    gps_data.iloc[[gps_point_idx]]["latitude"].item(),
                    snapped_to_next_segment[0],
                    snapped_to_next_segment[1],
                )
               
                if distance_to_segment < distance_to_next_segment:
                    speeds_on_segment.append(gps_data.iloc[[gps_point_idx]]["speed"].item())
                    data_exchange_debugger.add_snapping_line(segment, gps_data.iloc[[gps_point_idx]]["longitude"].item(), gps_data.iloc[[gps_point_idx]]["latitude"].item())
                    gps_point_idx += 1
                else:
                    gpx_point_on_segment = False
                
            if len(speeds_on_segment) == 0:
                raise ValueError("Expected at least one snapped point on the line")
            
            output.add_processed_segment(segment, bike_type, speeds_on_segment)
        
        data_exchange_debugger.write_geojson(track_idx)
        track_idx += 1
    
    output.print_meta_stats()
        
    return output.get_processed_segments()
        
def anonymize_segments(segments):
    # Anonymization Rules:
    # Delete first and last segment of every track (happens in the previous step (process_segments() already))
    # Delete all segments with a total count of 1
    # Delete all segments with with only one bike type
    
    anonymized_segments = {}
    removed_segments = 0
    for segment in segments:
        if segments[segment]["total_count"] > 1 and len(segments[segment]["profiles"]) > 1:
            anonymized_segments[segment] = segments[segment]
        else:
            removed_segments += 1
            
    print(f"Number of removed segments: {removed_segments}")
    print(f"Number of anonymous segments: {len(anonymized_segments)}")
    
    return anonymized_segments

def create_geojson_output(segments, start_time, end_time):
    geojson = {
        "type": "FeatureCollection",
        "properties": {
            "start_time": start_time,
            "end_time": end_time,
        },
        "features": []
    }
        
    for segment_key, segment_meta in segments.items():
        coordinates = segment_key.split('_')
        start_lng = float(coordinates[0])
        start_lat = float(coordinates[1])
        end_lng = float(coordinates[2])
        end_lat = float(coordinates[3])
        
        total_count = segment_meta['total_count']
        total_median_speed = np.median(segment_meta['total_speeds'])
        
        properties = {
            "total_count": total_count,
            "total_median_speed_ms": total_median_speed,
            "profiles": {},
        }
        
        for profile_key, profile_meta in segment_meta['profiles'].items():
            profile_count = profile_meta['count']
            profile_median_speed = np.median(profile_meta['speeds'])
            
            properties['profiles'][profile_key] = {
                "count": profile_count,
                "median_speed_ms": profile_median_speed,
            }
            
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [start_lng, start_lat],
                    [end_lng, end_lat],
                ],
            },
            "properties": properties,
        }
        
        geojson['features'].append(feature)
        
    with open(f'static/history_polylines/{start_time}_{end_time}.json', 'w') as f:
        json.dump(geojson, f)
        
def update_index(start_time, end_time):
    index_path = 'static/index.json'
    with open(index_path, 'r') as f:
        index = json.load(f)
    index["files"].append({
        "start_time": start_time,
        "end_time": end_time,
        "path": f"history_polylines/{start_time}_{end_time}.geojson",
    })
    index["total_count"] = len(index["files"])
    with open(index_path, 'w') as f:
        json.dump(index, f)
    
def main(tracking_service_url, tracking_service_api_key, graphhopper_service_url, write_output=False, debug=False):
    start_time = get_time_of_last_bucket()
    end_time = current_milli_time()
    
    processed_segments = process_segments(tracking_service_url, tracking_service_api_key, graphhopper_service_url, start_time, end_time, use_debugging=debug)
    if debug:
        with open("processed_segments.json", "w") as f:
            json.dump(processed_segments, f)
    anonymized_segments = anonymize_segments(processed_segments)
    if debug:
        with open("anonymized_segments.json", "w") as f:
            json.dump(anonymized_segments, f)
    if write_output:
        create_geojson_output(anonymized_segments, start_time, end_time)
        update_index(start_time, end_time)

if __name__ == "__main__":
    parser=argparse.ArgumentParser()

    parser.add_argument("--output", help="Write the anonymized geojson output to a file. Default: False. If False, the script will perform a dry run and only print meta information about the theoretical output.")
    parser.add_argument("--debug", help="Create debug geojson files about the map matching and snapping. Default: False.")

    args=parser.parse_args()
    
    write_output = False
    if args.output and args.output.lower() == "true":
        write_output = True
        
    debug = False
    if args.debug and args.debug.lower() == "true":
        debug = True
        
    tracking_service_url = os.environ["TRACKING_SERVICE_URL"]
    tracking_service_api_key = os.environ["TRACKING_SERVICE_API_KEY"]
    graphhopper_service_url = os.environ["GRAPHHOPPER_SERVICE_URL"]
    
    if not tracking_service_url or not tracking_service_api_key:
        raise ValueError("Please set TRACKING_SERVICE_API_KEY and TRACKING_SERVICE_URL")
    if not graphhopper_service_url:
        raise ValueError("Please set GRAPHHOPPER_SERVICE_URL")
        
    print("Starting process_segments.py...")
    print(f"Tracking service URL: {tracking_service_url}")
    print(f"GraphHopper service URL: {graphhopper_service_url}")
    print(f"Write anonymized geojson output: {write_output}")
    print(f"Write debug map matching and snapping geojson output: {debug}")
    
    main(tracking_service_url, tracking_service_api_key, graphhopper_service_url, write_output=write_output, debug=debug)