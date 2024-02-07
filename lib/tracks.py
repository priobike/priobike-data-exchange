import requests
import pandas as pd
from io import StringIO

def fetch_tracks(
    tracking_service_url,
    tracking_service_api_key,
    start_time,
    end_time,
):  
    # Fetch the paginated data from the tracking service
    def fetch():
        tracking_base_url = f'{tracking_service_url}/tracks/list/?key={tracking_service_api_key}&pageSize=100&from={start_time}&to={end_time}'
        response = requests.get(tracking_base_url)
        tracking_data = response.json()
        for track in tracking_data['results']:
            yield track
        tracking_page_count = tracking_data['totalPages']
        for page in range(2, tracking_page_count + 1):
            print(f'Page {page} of {tracking_page_count}...')
            tracking_data = requests.get(f'{tracking_base_url}&page={page}').json()
            for track in tracking_data['results']:
                yield track
                
    tracks = []
    bike_types = []
    gps_data = []
                                
    # Resolve each track with its raw GPS data
    for track in fetch():
        pk = track["pk"]
        raw = requests.get(f'{tracking_service_url}/tracks/fetch/?key={tracking_service_api_key}&pk={pk}').json()
        gps_df = pd.read_csv(StringIO(raw['gpsCSV']))
        if "bikeType" not in raw["metadata"]:
            bike_type = "unavailable"
        else:
            bike_type = str(raw["metadata"]["bikeType"])
        tracks.append(track)
        bike_types.append(bike_type)
        gps_data.append(gps_df)
        
    return zip(tracks, bike_types, gps_data)