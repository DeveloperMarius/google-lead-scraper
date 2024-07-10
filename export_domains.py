import sqlite3
import uuid
from urllib.parse import urlparse
import argparse

if __name__ == '__main__':
    # Define the command line arguments
    parser = argparse.ArgumentParser(
        prog="Export Domains from Database",
        description="Export domains from the database to a CSV file for further processing.",
        epilog="When more assistance is needed, please contact the authors.",
    )
    parser.add_argument("-id", "--analyzer_id", choices=['uuid', 'rowid'], help="Type of analyzer_id to generate")
    parser.add_argument("-db", "--db_file", nargs="?", default='leads.db', help="SQLite database file")
    parser.add_argument("-m", "--max_leads", nargs="?", default=10000, help="Maximum number of leads to process")
    parser.add_argument("-t", "--business_type", nargs="?", default=None, help="Type of business to process (e.g. electrician). Sould be a substring of the 'types' field or the exact 'type' field in the Google Places API response.")
    parser.add_argument("-c", "--country", nargs="?", default='Deutschland', help="Country to process")
    parser.add_argument("-w", "--website", action=argparse.BooleanOptionalAction, default=False, help="Require website to be present in the data")
    parser.add_argument("-p", "--phone", action=argparse.BooleanOptionalAction, default=False, help="Require phone to be present in the data")

    # Parse the arguments
    args = parser.parse_args()

    # Connect to the database
    with sqlite3.connect(args.db_file) as db_conn:
        cursor = db_conn.cursor()
        cursor.row_factory = sqlite3.Row

        # Search for leads that have not been processed yet
        max_entries = args.max_leads
        page = 0
        locations = []

        while (page+1) * 100 <= max_entries:
            page += 1

            ask_website = '"website" IS NOT NULL' if args.website else 'TRUE'
            ask_phone = '"phone" IS NOT NULL' if args.phone else 'TRUE'
            cursor.execute(
                f'SELECT rowid AS id, * FROM locations where analyzer_id IS NULL AND country = ? and (types like (\'%\' || ? || \'%\') or type = ?) and {ask_website} and {ask_phone} LIMIT 100 OFFSET ?',
                (args.country, args.business_type, args.business_type, (page - 1) * 100))

            locations = locations + [dict(row) for row in cursor.fetchall()]

        print(f'Found {len(locations)} leads matching the criteria')

        # Update the leads with the analyzer_id
        for location in locations:
            if args.analyzer_id == 'uuid':
                location["analyzer_id"] = str(uuid.uuid4())
            elif args.analyzer_id == 'rowid':
                location["analyzer_id"] = str(location["id"])

            cursor.execute('UPDATE locations SET analyzer_id = ? WHERE rowid = ?', (location["analyzer_id"], location['id']))
        db_conn.commit()

        # Clear the file
        with open('leads.csv', 'w') as f:
            f.write('')

        # append domains to analyzer_data.csv
        with open('leads.csv', 'a') as f:
            for location in locations:
                location_website = urlparse(location["website"])
                # extract domain using url parser
                location_domain = location_website.netloc
                f.write(f'{location_domain},{location["analyzer_id"]}\n')
