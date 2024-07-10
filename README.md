# Google Lead Scraper

This is a tool to scrape leads from Google Maps. It uses the Google Maps Places API to search for businesses and then store the results.  

## Preparation

Google grants [$200 free usage](https://mapsplatform.google.com/pricing/) every month.  
This script uses "Text Search" to fetch places. It also fetches the [phone and website fields](https://developers.google.com/maps/documentation/places/web-service/data-fields), thus we fall into the "Text Search (Advanced)" pricing category.

1. Create a [Google Cloud project](https://console.cloud.google.com/)
2. Enable the [Google Places API (new)](https://console.cloud.google.com/apis/library/places.googleapis.com)
3. Create an [API Key](https://console.cloud.google.com/apis/credentials)

## Usage

### Scrape Leads

```
./scraper.py   
  -h, --help            show this help message and exit
  -q SEARCH_QUERY, --search_query SEARCH_QUERY
                        Search query for Google Places API
  -t TAG, --tag TAG     Tag for the locations to be inserted into the database
  -ro [RECT_OFFSET], --rect_offset [RECT_OFFSET]
                        Offset for the rectangles when resuming the script
  -db [DB_FILE], --db_file [DB_FILE]
                        SQLite database file
  -rw [RECT_WIDTH], --rect_width [RECT_WIDTH]
                        Width of the rectangles in meters
  -rh [RECT_HEIGHT], --rect_height [RECT_HEIGHT]
                        Height of the rectangles in meters
  -k GOOGLE_API_KEY, --google_api_key GOOGLE_API_KEY
                        Google Places (new) API key
  -s [SLEEP], --sleep [SLEEP]
                        Sleep time between requests in seconds (default: 2)
```

Example: `python3 scraper.py -q elektriker -t electrician -k xyz`

### Export to CSV

```
./export.py   
  -h, --help            show this help message and exit
  -id {uuid,rowid}, --analyzer_id {uuid,rowid}
                        Type of analyzer_id to generate
  -db [DB_FILE], --db_file [DB_FILE]
                        SQLite database file (default: leads.db)
  -m [MAX_LEADS], --max_leads [MAX_LEADS]
                        Maximum number of leads to process
  -t [BUSINESS_TYPE], --business_type [BUSINESS_TYPE]
                        Type of business to process (e.g. electrician). Sould be a substring of the 'types' field or the exact 'type' field in the Google Places API response.
  -c [COUNTRY], --country [COUNTRY]
                        Country to process (default: Deutschland)
  -w, --website, --no-website
                        Require website to be present in the data (default: False)
  -p, --phone, --no-phone
                        Require phone to be present in the data (default: False)
```

Example: `python3 export_domains.py -id uuid -t electrician -w -p`

## Hints

### Don't crawl for types
Don't crawl for business types. Many businesses don't specify a specific type and then you won't find them.  
The best way is to use a text search for the type. Google will figure it out and many businesses have their profession in their name.

## Credits

### GEO Json
Thanks to Francesco Schwarz for the german geojson file from https://github.com/isellsoap/deutschlandGeoJSON.
