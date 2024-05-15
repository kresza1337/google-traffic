import googlemaps
import json
import csv
import mysql.connector
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import time
import re
from googlemaps import Client
from dotenv import load_dotenv
import os

def get_coordinates_from_url(api_key, url):
    """Get start and end coordinates from a Google Maps URL."""
    gmaps: Client = googlemaps.Client(key=api_key)

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    print("Parsed URL:", parsed_url)
    print("Query Parameters:", query_params)

    start_location = query_params.get('origin', [''])[0]
    end_location = query_params.get('destination', [''])[0]

    start_coordinates = get_coordinates(gmaps, start_location)
    end_coordinates = get_coordinates(gmaps, end_location)

    return start_coordinates, end_coordinates

def get_coordinates(gmaps, location):
    """Get coordinates (latitude, longitude) for a given location using Google Maps API."""
    try:
        geocode_result = gmaps.geocode(location)
        if not geocode_result:
            print(f"No results found for location: {location}")
            return None
        return geocode_result[0]['geometry']['location']

    except Exception as e:
        print(f"Failed to get coordinates for location: {location}")
        print(f"Error: {e}")
        return None

def calculate_route(api_key, start_coordinates, end_coordinates, routName, connection):
    try:
        gmaps = googlemaps.Client(key=api_key)

        print("Calculating routes...")

        directions_results = gmaps.directions(
            start_coordinates,
            end_coordinates,
            mode="driving",
            departure_time=datetime.now(),
            alternatives=True,
        )

        # ZNAJDOWANIE NAJKRÓTSZEJ TRASY
        shortest_route = min(directions_results, key=lambda x: x['legs'][0]['distance']['value'])

        print("API Response:", shortest_route)

        duration_in_traffic = shortest_route['legs'][0]['duration_in_traffic']['text']
        minute = int(re.search(r'(\d+) min', duration_in_traffic).group(1))
        origin = shortest_route['legs'][0]['start_address'].strip('"')
        destination = shortest_route['legs'][0]['end_address'].strip('"')
        distance = shortest_route['legs'][0]['distance']['text'].replace(' km', '')

        day_of_week = datetime.today().weekday()
        date = datetime.today().strftime('%Y.%m.%d')
        time_of_day = datetime.now().strftime("%H:%M")

        # ZAPIS DO BAZY DANYCH
        cursor = connection.cursor()
        insert_query = """
        INSERT INTO googletraffic.traffic (data, dzien_tygodnia, godzina, nazwa_trasy, dystans, czas_minut)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (date, day_of_week, time_of_day, routName, distance, minute))
        connection.commit()

        print(f"Origin: {origin}")
        print(f"Destination: {destination}")
        print(f"Distance: {distance} km")
        print(f"Duration in traffic: {duration_in_traffic}")

    except Exception as e:
        print(f"Error calculating route: {e}")

def get_routename(url):
    if 'Wrocław+Fashion+Outlet' in url or 'Most+Grunwaldzki' in url:
        return 'WFO-MG'
    elif 'Brama+Grabiszyńska' in url or 'Dolnośląski+Ośrodek+Ruchu+Drogowego' in url:
        return 'BG-DORD'
    elif 'Wrocławski+Rower+Miejski' in url or 'Zwycięska' in url:
        return 'ZWYCIESKA'
    elif 'ZOO' in url or 'Uniwersytet+Wrocławski' in url:
        return 'ZOO-UWR'
    elif 'Pasaż+Grunwaldzki' in url or 'Bielany+Wrocławskie+Wrocław' in url:
        return 'BIELPASAZ'
    else:
        return 'UnknownRoute'

if __name__ == "__main__":
    load_dotenv(dotenv_path='connection.env')
    api_key = os.getenv('API_KEY', default='')

    connection = mysql.connector.connect(user='admin', password='Admin123', database='Googletraffic', host='', port='3306')
    if not api_key:
        print("API key not found. Check the connection.env file.")
    else:
        print("API key has been found")
        google_maps_urls = [
            'https://www.google.com/maps/dir/?api=1&origin=Brama+Grabiszyńska+Wrocław&destination=Dolnośląski+Ośrodek+Ruchu+Drogowego+Wrocław&travelmode=driving',
            'https://www.google.com/maps/dir/?api=1&origin=Wrocław+Fashion+Outlet,+Graniczna+2&destination=Most+Grunwaldzki,+Wrocław&travelmode=driving',
            'https://www.google.com/maps/dir/?api=1&origin=Wrocławski+Rower+Miejski+-+15116+%22Zwycięska%2FAgrestowa%22,+Zwycięska,+53-033+Wrocław&destination=Wrocławski+Rower+Miejski+-+15117+%22al.+Karkonoska%2FJeździecka%22&travelmode=driving',
            'https://www.google.com/maps/dir/?api=1&origin=ZOO+Wrocław+sp.z+o.o.,+Zygmunta+Wróblewskiego+1-5,+51-618+Wrocław&destination=Uniwersytet+Wrocławski,+plac+Uniwersytecki+1,+50-137+Wrocław&travelmode=driving',
            'https://www.google.com/maps/dir/?api=1&origin=Pasaż+Grunwaldzki+Wrocław&destination=Bielany+Wrocławskie+Wrocław&travelmode=driving',
        ]
        routName = 'manualrouteName'
        flag = True

        while flag:
            for google_maps_url in google_maps_urls:
                routName = get_routename(google_maps_url)
                start_coordinates, end_coordinates = get_coordinates_from_url(api_key, google_maps_url)
                calculate_route(api_key, start_coordinates, end_coordinates, routName, connection)
            time.sleep(3600)

    connection.close()
