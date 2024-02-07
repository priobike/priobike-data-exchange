import json

class DataExchangeDebugger:
    def __init__(self, active=False):
        self.active = active
            
    def new_geojson(self):
        if self.active:
            self.geojson ={
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "type": "track",   
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "type": "map_matched_track",   
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [],
                        },
                    },
                    {
                        "type": "Feature",
                        "properties": {
                            "type": "snap_lines",   
                        },
                        "geometry": {
                            "type": "MultiLineString",
                            "coordinates": [],
                        },
                    },
                ],
            }
            
    def add_track_point(self, lng, lat):
        if not self.active:
            return
        if not self.geojson:
            raise ValueError("No geojson object created.")
        self.geojson["features"][0]["geometry"]["coordinates"].append([lng, lat])
        
    def add_map_matched_point(self, lng, lat):
        if not self.active:
            return
        if not self.geojson:
            raise ValueError("No geojson object created.")
        self.geojson["features"][1]["geometry"]["coordinates"].append([lng, lat])

    def add_snapping_line(self, segment, gps_lng, gps_lat):
        if not self.active:
            return
        if not self.geojson:
            raise ValueError("No geojson object created.")
        segment_center = (
            (segment[0][0] + segment[1][0]) / 2,
            (segment[0][1] + segment[1][1]) / 2,
        )
        self.geojson["features"][2]["geometry"]["coordinates"].append([
            [gps_lng, gps_lat],
            [segment_center[0], segment_center[1]],
        ])
        
    def write_geojson(self, track_idx):
        if not self.active:
            return
        if not self.geojson:
            raise ValueError("No geojson object created.")
        with open(f"debug/track_{track_idx}.geojson", "w") as f:
                json.dump(self.geojson, f)