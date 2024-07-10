import math
import time
from shapely.geometry import Point
import geopandas as gpd
import requests
import json
import sqlite3
import argparse


class GooglePlacesAPI:

    def __init__(self, api_key):
        self.request_count = 0
        self.api_key = api_key

    def text_search(self, query, rect1, rect2, page=None):
        self.request_count += 1
        req = requests.post('https://places.googleapis.com/v1/places:searchText', json={
            'locationRestriction': {
                "rectangle": {
                    "low": {
                        "latitude": rect1.y,
                        "longitude": rect1.x
                    },
                    "high": {
                        "latitude": rect2.y,
                        "longitude": rect2.x
                    }
                }
                # "circle": {
                #     "center": {
                #         "latitude": latitude,
                #         "longitude": longitude
                #     },
                #     "radius": radius
                # }
            },
            'pageSize': 20,
            'pageToken': page,
            'languageCode': 'de',
            'textQuery': query
        }, headers={
            'X-Goog-Api-Key': self.api_key,
            'X-Goog-FieldMask': 'nextPageToken,places.id,places.name,places.displayName,places.primaryType,places.types,places.nationalPhoneNumber,places.internationalPhoneNumber,places.formattedAddress,places.addressComponents,places.location,places.rating,places.userRatingCount,places.googleMapsUri,places.websiteUri,places.regularOpeningHours'
        })
        data = json.loads(req.text)
        if 'error' in data:
            raise Exception(f'Error: {data}')
        return data


# Thanks to ChatGPT for the Rasterize class
class Rasterize:

    def calculate_rectangle(self, width=25000, height=25000):
        # Festlegung der Grenzen Deutschlands
        min_lat, max_lat = 47, 55
        min_lon, max_lon = 6, 15

        # Umrechnung von Metern in geografische Grad
        deg_per_km = 1 / 111  # 1 Breitengrad entspricht etwa 111 km
        delta_lat = (height / 1000) * deg_per_km

        # Berechnung des mittleren Breitengrads Deutschlands
        mid_lat = (min_lat + max_lat) / 2

        # Umrechnung von Metern in geografische Grad abhängig vom Breitengrad
        delta_lon = (width / 1000) * deg_per_km / math.cos(math.radians(mid_lat))

        # Laden der Deutschland-Grenzen (GeoJSON-Datei)
        germany = gpd.read_file('germany.geo.json')  # Pfad zur GeoJSON-Datei
        germany_polygon = germany.unary_union  # Vereinigung aller Polygone zu einem

        # Generierung der Eckpunkte der Rechtecke
        rectangles = []

        lat = min_lat
        while lat + delta_lat <= max_lat:
            lon = min_lon
            while lon + delta_lon <= max_lon:
                bottom_left = Point(lon, lat)
                top_right = Point(lon + delta_lon, lat + delta_lat)
                if germany_polygon.contains(bottom_left) and germany_polygon.contains(top_right):
                    rectangles.append((bottom_left, top_right))
                lon += delta_lon
            lat += delta_lat

        # Ausgabe der Rechteck-Eckpunkte
        return rectangles

    def calculate_circle(self, radius=50000):
        # Festlegung der Grenzen Deutschlands
        min_lat, max_lat = 47, 55
        min_lon, max_lon = 6, 15

        # Radius des Kreises in Metern
        distance_between_points = radius  # 25 km (50 is max for Google Places API)

        # Umrechnung von Metern in geografische Grad
        deg_per_km = 1 / 111  # 1 Breitengrad entspricht etwa 111 km
        delta_lat = (distance_between_points / 1000) * deg_per_km

        # Berechnung des mittleren Breitengrads Deutschlands
        mid_lat = (min_lat + max_lat) / 2

        # Umrechnung von Metern in geografische Grad abhängig vom Breitengrad
        delta_lon = (distance_between_points / 1000) * deg_per_km / math.cos(math.radians(mid_lat))

        # Laden der Deutschland-Grenzen (GeoJSON-Datei)
        germany = gpd.read_file('germany.geo.json')  # Pfad zur GeoJSON-Datei
        germany_polygon = germany.unary_union  # Vereinigung aller Polygone zu einem

        # Generierung der Mittelpunkte
        lat_points = []
        lon_points = []

        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                point = Point(lon, lat)
                if germany_polygon.contains(point):
                    lat_points.append(lat)
                    lon_points.append(lon)
                lon += delta_lon
            lat += delta_lat

        # Ausgabe der Mittelpunkte
        midpoints = list(zip(lat_points, lon_points))
        return midpoints


if __name__ == '__main__':
    # Define the command line arguments
    parser = argparse.ArgumentParser(
        prog="Google Places Scraper",
        description="Scrape business data from Google Places API and save it in a database.",
        epilog="When more assistance is needed, please contact the authors.",
    )
    parser.add_argument("-q", "--search_query", required=True, help="Search query for Google Places API")
    parser.add_argument("-t", "--tag", required=True, help="Tag for the locations to be inserted into the database")
    parser.add_argument("-ro", "--rect_offset", nargs="?", default=0, help="Offset for the rectangles when resuming the script")
    parser.add_argument("-db", "--db_file", nargs="?", default='leads.db', help="SQLite database file")
    parser.add_argument("-rw", "--rect_width", nargs="?", default=25000, help="Width of the rectangles in meters")
    parser.add_argument("-rh", "--rect_height", nargs="?", default=25000, help="Height of the rectangles in meters")
    parser.add_argument("-k", "--google_api_key", required=True, help="Google Places (new) API key")
    parser.add_argument("-s", "--sleep", nargs="?", default=2, help="Sleep time between requests in seconds (default: 2)")

    # Parse the arguments
    args = parser.parse_args()

    # Initialize variables
    api = GooglePlacesAPI(args.google_api_key)
    rects = Rasterize().calculate_rectangle(args.rect_width, args.rect_height)

    # Connect to the database
    with sqlite3.connect(args.db_file) as db_conn:
        db_cursor = db_conn.cursor()

        # Loop through the rectangles
        rect_id = 0
        for rect in rects:
            rect_id += 1
            if rect_id < args.rect_offset:
                continue
            # Sleep for x seconds to avoid rate limiting
            time.sleep(args.sleep)

            # Paginate through the results in the given rectangle
            # BL = Bottom Left, TR = Top Right
            print(f'Processing rectangle {rect_id} -> BL ({rect[0].y}, {rect[0].x}) TR ({rect[1].y}, {rect[1].x})')
            response = None
            fake_page_id = 0
            while response is None or ('nextPageToken' in response and 'places' in response and len(response['places']) == 20):
                fake_page_id += 1
                print(f'Fetching page {fake_page_id}...')

                # Fetch the next page of results
                response = api.text_search(args.search_query, rect[0], rect[1], response['nextPageToken'] if response else None)

                # Catch corner case when there are no places in the response of the first request
                if 'places' not in response:
                    continue

                # Loop through the places in the response
                for place in response['places']:
                    try:
                        # Check if the place is already in the database
                        db_cursor.execute('SELECT * FROM locations WHERE google_place_id = ?', (place['id'],))
                        if db_cursor.fetchone() is not None:
                            print(f'Skipping place {place["id"]} because it already exists in the database.')
                            continue

                        # Parse the address components
                        street = None
                        street_nr = None
                        city = None
                        city_backup = None
                        state = None
                        addr_zip = None
                        country = None
                        for component in place['addressComponents']:
                            if 'street_number' in component['types']:
                                street_nr = component['longText']
                            if 'route' in component['types']:
                                street = component['longText']
                            if 'locality' in component['types']:
                                city = component['longText']
                            if 'sublocality' in component['types']:
                                city_backup = component['longText']
                            if 'administrative_area_level_1' in component['types']:
                                state = component['longText']
                            if 'country' in component['types']:
                                country = component['longText']
                            if 'postal_code' in component['types']:
                                addr_zip = component['longText']

                        # Insert the place into the database
                        db_cursor.execute('INSERT INTO locations (google_place_id, google_maps_url, display_name, phone, website, formatted_address, street, city, state, zip, country, latitude, longitude, rating, rating_count, opening_hours, type, types, tag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                            place['id'],
                            place['googleMapsUri'],
                            place['displayName']['text'],
                            place['internationalPhoneNumber'] if 'internationalPhoneNumber' in place else place['nationalPhoneNumber'] if 'nationalPhoneNumber' in place else None,
                            place['websiteUri'] if 'websiteUri' in place else None,
                            place['formattedAddress'],
                            f'{street} {street_nr}' if street and street_nr else None,
                            city if city else city_backup if city_backup else None,
                            state,
                            addr_zip,
                            country,
                            place['location']['latitude'],
                            place['location']['longitude'],
                            place['rating'] if 'rating' in place else None,
                            place['userRatingCount'] if 'userRatingCount' in place else None,
                            json.dumps(place['regularOpeningHours']) if 'regularOpeningHours' in place else None,
                            place['primaryType'] if 'primaryType' in place else None,
                            json.dumps(place['types']) if 'types' in place and len(place['types']) > 0 else None,
                            args.tag
                        ))
                    except Exception as e:
                        print(e)
                        print(place)
                        print(response)
                        print('Skipping because of failure', place['id'])
                db_conn.commit()

    print(f'Done in {api.request_count} api requests')
