#!/usr/bin/env python3
import os
import json
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.travel.thunderbird_flight_search import AmadeusFlightSearcher

def main():
    print("=== Testing MSN Flight Search via Amadeus API ===")
    
    # Initialize Amadeus API
    searcher = AmadeusFlightSearcher()
    
    # Search COS-MSN on 2026-09-07 for 2 passengers
    print("Searching COS-MSN on 2026-09-07...")
    
    try:
        results = searcher.search_one_way(
            origin='COS',
            destination='MSN',
            departure_date='2026-09-07',
            adults=2,
            cabin_class='ECONOMY'
        )
        
        print(f"Found {len(results)} results")
        
        if results:
            # Display first 3 results
            for i, flight in enumerate(results[:3]):
                print(f"\n{i+1}. Airline: {flight.get('carrierCode', 'N/A')} {flight.get('flightNumber', 'N/A')}")
                print(f"   Price: ${flight.get('total', 'N/A')}")
                print(f"   Duration: {flight.get('duration', 'N/A')}")
                print(f"   Stops: {flight.get('stops', 'N/A')}")
                
                # Save to the data file
                output_file = project_root / "core" / "travel" / "data" / "airline_test_COS_MSN_2026-09-07.json"
                
                # Load existing data
                if output_file.exists():
                    with open(output_file, 'r') as f:
                        data = json.load(f)
                else:
                    data = {
                        "route": "COS-MSN",
                        "depart_date": "2026-09-07",
                        "adults": 2,
                        "scraped_at": None,
                        "skiplagged": {},
                        "kayak": {},
                        "expedia": {},
                        "cheaptickets": {},
                        "centrav": {}
                    }
                
                # Add Amadeus results
                if "amadeus" not in data:
                    data["amadeus"] = {}
                
                data["amadeus"]["economy"] = {
                    "source": "amadeus",
                    "cabin": "economy",
                    "url": "https://developers.amadeus.com/self-service/category/flights/api-doc/flight-offers-search",
                    "adults": 2,
                    "depart_date": "2026-09-07",
                    "raw_prices": results,
                    "lowest_price_pp": min([r.get('total', 0) for r in results]) / 2 if results else None,
                    "total_lowest": min([r.get('total', 0) for r in results]) if results else None,
                    "airlines_found": list(set([r.get('carrierCode', '') for r in results if r.get('carrierCode')])),
                    "status": "success" if results else "no_prices_found"
                }
                
                # Save updated data
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"\nSaved results to {output_file}")
        else:
            print("No flights found for COS-MSN on 2026-09-07")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()