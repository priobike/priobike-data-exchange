class SegmentProcessingOutput:
    def __init__(self):
        self.too_short_tracks_count = 0
        self.invalid_tracks_count = 0
        self.tracks_with_map_matching_error_count = 0
        self.tracks_with_invalid_map_matching_count = 0
        self.__all_segments = []
        self.__processed_segments = {}
        
    def __get_segment_key(self, segment):
        return f"{segment[0][0]}_{segment[0][1]}_{segment[1][0]}_{segment[1][1]}"
    
    def add_segment(self, segment):
        self.__all_segments.append(self.__get_segment_key(segment))
    
    def add_processed_segment(self, segment, bike_type, speeds):
        segment_key = self.__get_segment_key(segment)
        if segment_key not in self.__processed_segments:
            self.__processed_segments[segment_key] = {
                "total_count": 1,
                "total_speeds": speeds,
                "profiles": {
                    bike_type: {
                        "count": 1,
                        "speeds": speeds,
                    }
                }
            }
        else:
            self.__processed_segments[segment_key]["total_count"] += 1
            if bike_type in self.__processed_segments[segment_key]["profiles"]:
                self.__processed_segments[segment_key]["profiles"][bike_type]["count"] += 1
                self.__processed_segments[segment_key]["profiles"][bike_type]["speeds"].extend(speeds)
            else:
                self.__processed_segments[segment_key]["profiles"][bike_type] = {
                    "count": 1,
                    "speeds": speeds,
                }
                
    def get_processed_segments(self):
        # Check if the total count matches the sum of the counts of the profiles
        for segment in self.__processed_segments:
            total_count = self.__processed_segments[segment]["total_count"]
            profile_counts = sum([self.__processed_segments[segment]["profiles"][profile]["count"] for profile in self.__processed_segments[segment]["profiles"]])
            if total_count != profile_counts:
                raise ValueError(f"Total count of segment {segment} does not match the sum of the counts of the profiles")
        return self.__processed_segments
            
    def print_meta_stats(self):
        print(f"Found a total of {len(self.__all_segments)} segments")
        print(f"Found {len(self.__processed_segments)} unique segments")
        
        total_unprocessed_segments_count = 0
        unprocessed_segments = set()
        for segment in self.__all_segments:
            if segment not in self.__processed_segments:
                total_unprocessed_segments_count += 1
                unprocessed_segments.add(segment)
        unique_unprocessed_segments = len(unprocessed_segments)
        
        print(f"Found {total_unprocessed_segments_count} unprocessed segments")
        print(f"Found {unique_unprocessed_segments} unique unprocessed segments")
        
        print(f"Found {self.too_short_tracks_count} too short tracks")
        print(f"Found {self.invalid_tracks_count} invalid tracks")
        print(f"Found {self.tracks_with_map_matching_error_count} tracks with map matching errors")
        print(f"Found {self.tracks_with_invalid_map_matching_count} tracks with invalid map matching")
        
    