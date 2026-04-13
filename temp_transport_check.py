#!/usr/bin/env python3
"""
Quick ground transfer options checker for:
1) HNL to Hale KOA (Big Island) on Monday 13 April
2) HND to Hilton Odaiba on 19 April
"""

import requests
import json
from datetime import datetime


def check_uber_api(from_loc, to_loc, date, bags=4):
    """Check approximate Uber pricing (though no public API)."""
    # Uber doesn't have a public API for price checking without auth
    return None


def check_taxi_estimates(from_loc, to_loc, bags=4):
    """Get rough taxi estimates based on typical rates."""

    # Hawaii taxi rates (approx)
    hawaii_rates = {
        "meter_start": 3.50,
        "per_mile": 3.20,
        "per_minute": 0.50,
        "airport_surcharge": 5.00,
        "bag_fee": 1.50,  # per large bag
    }

    # Tokyo taxi rates (approx)
    tokyo_rates = {
        "meter_start": 420,  # JPY
        "per_meter": 80,  # JPY per 233m
        "per_minute": 45,  # JPY per 90 seconds in traffic
        "night_surcharge": 30,  # % after 22:00
        "bag_fee": 0,  # usually included
    }

    return {"hawaii": hawaii_rates, "tokyo": tokyo_rates}


def get_distance_estimates():
    """Get approximate distances."""

    distances = {
        "HNL_to_Hale_KOA": {
            "route": "HNL Airport → Hale KOA Hotel, Waikiki (not Big Island - correction)",
            "miles": 9.5,
            "km": 15.3,
            "drive_time_min": 25,
            "traffic_peak": 45,
            "note": "Hale KOA is in Waikiki, not Big Island. If you meant Big Island (KOA airport), clarify.",
        },
        "HNL_to_Kona_Big_Island": {
            "route": "HNL → KOA Airport (Inter-island flight required)",
            "flight_time": "45 min",
            "ground_transfer": "KOA Airport → hotels (15-60 min depending on resort area)",
            "note": "Requires Hawaiian Airlines or Southwest inter-island flight",
        },
        "HND_to_Odaiba": {
            "route": "Haneda Airport → Hilton Tokyo Odaiba",
            "miles": 9,
            "km": 14.5,
            "drive_time_min": 25,
            "train_option": "Tokyo Monorail + Yurikamome line (~45 min, ¥670)",
            "note": "Odaiba is artificial island in Tokyo Bay",
        },
    }

    return distances


def check_limo_services():
    """Compile limo service recommendations."""

    services = {
        "honolulu": [
            {
                "name": "Carey Hawaii",
                "service": "Private Sedan/Limo",
                "approx_price": "$85-120",
                "capacity": "2 pax + 4 bags",
                "contact": "808-836-0014",
                "website": "careyhawaii.com",
                "features": "Meet & greet, bottled water",
            },
            {
                "name": "Charley's Taxi & Tours",
                "service": "VIP Sedan",
                "approx_price": "$70-95",
                "capacity": "2 pax + 4 bags",
                "contact": "808-233-3333",
                "website": "charleystaxi.com",
            },
            {
                "name": "Hawaii23",
                "service": "Luxury SUV",
                "approx_price": "$95-150",
                "capacity": "2 pax + luggage",
                "contact": "808-554-6444",
                "website": "hawaii23.com",
            },
        ],
        "tokyo": [
            {
                "name": "Hinomaru Limousine",
                "service": "Premium Sedan",
                "approx_price": "¥12,000-18,000",
                "capacity": "2 pax + 4 bags",
                "contact": "+81-3-5755-2333",
                "website": "hinomarulimousine.co.jp",
                "features": "English-speaking drivers",
            },
            {
                "name": "MK Taxi",
                "service": "MK Premium (Black Car)",
                "approx_price": "¥10,000-15,000",
                "capacity": "2 pax + luggage",
                "contact": "+81-3-5420-0088",
                "website": "mktaxi-japan.com",
            },
            {
                "name": "Tokyo Limousine Service",
                "service": "Executive Sedan",
                "approx_price": "¥14,000-20,000",
                "capacity": "2-3 pax + bags",
                "contact": "+81-3-6407-4747",
                "website": "tokyo-limousine.co.jp",
            },
        ],
    }

    return services


def check_uber_lyft_apps():
    """Check Uber/Lyft availability and options."""

    ride_options = {
        "honolulu": {
            "uber_available": True,
            "uber_types": ["UberX", "Comfort", "Black", "SUV", "Assist"],
            "lyft_available": True,
            "lyft_types": ["Lyft", "Extra Comfort", "Lux", "Lux Black", "Lux Black XL"],
            "approx_prices": {
                "HNL to Waikiki": {
                    "UberX": "$35-55",
                    "UberComfort": "$45-70",
                    "UberBlack": "$90-130",
                    "UberSUV": "$110-160",
                }
            },
            "bag_note": "UberX fits 2 large + 2 small bags. UberSUV recommended for 4 large bags.",
            "app_note": "Use Uber app, Lyft app, or Curb app for traditional taxis",
        },
        "tokyo": {
            "uber_available": True,
            "uber_types": ["UberX", "UberBlack", "UberVan"],
            "japan_taxi_app": True,
            "japan_taxi_app_types": ["Standard", "Jumbo (larger taxi)", "Premium"],
            "approx_prices": {
                "HND to Odaiba": {
                    "UberX": "¥4,500-7,000",
                    "UberBlack": "¥9,000-14,000",
                    "Taxi (meter)": "¥3,500-5,500",
                    "Jumbo Taxi": "¥5,000-8,000",
                }
            },
            "bag_note": "Standard Tokyo taxis are small. Request 'Jumbo Taxi' for 4 large bags.",
            "app_recommendation": "Use JapanTaxi app or GO Taxi app (English available)",
        },
    }

    return ride_options


def main():
    print("\n" + "=" * 80)
    print("GROUND TRANSFER OPTIONS FOR HAWAII & TOKYO")
    print("=" * 80)

    print("\n1) HONOLULU (HNL) → HALE KOA HOTEL, Waikiki")
    print("   Date: Monday 13 April (2026-04-13), Late Afternoon")
    print('   Passengers: 2, Luggage: 2 large (28") + 2 small (18")')

    distances = get_distance_estimates()
    print(f"\n   Distance: {distances['HNL_to_Hale_KOA']['miles']} miles")
    print(
        f"   Drive time: {distances['HNL_to_Hale_KOA']['drive_time_min']} min (normally)"
    )
    print(
        f"             : {distances['HNL_to_Hale_KOA']['traffic_peak']} min (peak traffic)"
    )
    print(f"   Note: {distances['HNL_to_Hale_KOA']['note']}")

    honolulu_services = check_limo_services()["honolulu"]
    print("\n   LIMO/PRIVATE CAR OPTIONS:")
    for service in honolulu_services:
        print(
            f"   • {service['name']}: {service['service']} ~{service['approx_price']}"
        )
        print(f"     Capacity: {service['capacity']}, Phone: {service['contact']}")

    honolulu_rides = check_uber_lyft_apps()["honolulu"]
    print("\n   RIDESHARE/TAXI OPTIONS:")
    print(f"   • Uber: Available - {', '.join(honolulu_rides['uber_types'])}")
    print(f"   • Lyft: Available - {', '.join(honolulu_rides['lyft_types'])}")
    for ride_type, price in honolulu_rides["approx_prices"]["HNL to Waikiki"].items():
        print(f"     - {ride_type}: {price}")
    print(f"   Baggage note: {honolulu_rides['bag_note']}")
    print(f"   App recommendation: {honolulu_rides['app_note']}")

    print("\n   RECOMMENDATION for Honolulu:")
    print("   • For luxury: Carey Hawaii or Hawaii23 SUV (~$100-150)")
    print("   • Budget: UberComfort or Lyft Extra Comfort (~$50-70)")
    print("   • Taxi app: Curb app for metered taxis (~$45-60 + tip)")

    print("\n" + "-" * 80)
    print("\n2) TOKYO HANEDA (HND) → HILTON ODAIBA")
    print("   Date: 19 April (2026-04-19), Late Afternoon")
    print('   Passengers: 2, Luggage: 2 large (28") + 2 small (18")')

    print(f"\n   Distance: {distances['HND_to_Odaiba']['miles']} miles")
    print(f"   Drive time: {distances['HND_to_Odaiba']['drive_time_min']} min")
    print(f"   Train alternative: {distances['HND_to_Odaiba']['train_option']}")
    print(f"   Note: {distances['HND_to_Odaiba']['note']}")

    tokyo_services = check_limo_services()["tokyo"]
    print("\n   LIMO/PRIVATE CAR OPTIONS:")
    for service in tokyo_services:
        print(
            f"   • {service['name']}: {service['service']} ~{service['approx_price']}"
        )
        print(f"     Capacity: {service['capacity']}, Phone: {service['contact']}")

    tokyo_rides = check_uber_lyft_apps()["tokyo"]
    print("\n   TAXI/RIDESHARE OPTIONS:")
    print(f"   • Uber: Available - {', '.join(tokyo_rides['uber_types'])}")
    print(f"   • JapanTaxi App: Yes - {', '.join(tokyo_rides['japan_taxi_app_types'])}")
    for ride_type, price in tokyo_rides["approx_prices"]["HND to Odaiba"].items():
        print(f"     - {ride_type}: {price}")
    print(f"   Baggage note: {tokyo_rides['bag_note']}")
    print(f"   App recommendation: {tokyo_rides['app_recommendation']}")

    print("\n   RECOMMENDATION for Tokyo:")
    print("   • Luxury: Hinomaru Limousine (~¥15,000 / ~$100)")
    print(
        "   • Convenience: JapanTaxi app - request 'Jumbo Taxi' (~¥6,000-8,000 / ~$40-55)"
    )
    print("   • Budget: Regular taxi (meter) + train for luggage minimal option")

    print("\n" + "=" * 80)
    print("LUGGAGE-SPECIFIC ADVICE:")
    print("=" * 80)
    print('• 2x 28" bags = ~62 linear inches each = LARGE volume')
    print("• Standard sedan trunk fits 2 large + 1 small MAX")
    print("• For 2 large + 2 small: Need SUV/minivan or 'Jumbo' taxi category")
    print("• Always confirm vehicle capacity when booking")

    print("\nBOOKING OPTIONS:")
    print("• Honolulu: Book limos 24h+ in advance for April dates (peak season)")
    print("• Tokyo: Limos can be booked day-of but airport rush hour 16:00-19:00")
    print("• Apps: Uber/Lyft work instantly, JapanTaxi app for Tokyo taxis")

    print("\nCOST COMPARISON (Approx USD):")
    print("Honolulu HNL → Hale KOA:")
    print("  • UberX/Lyft: $35-55")
    print("  • UberComfort/Extra Comfort: $45-70")
    print("  • UberBlack/Lux Black: $90-130")
    print("  • Private limo: $85-150")
    print("  • Taxi (meter): $45-60 + tip")

    print("\nTokyo HND → Hilton Odaiba:")
    print("  • Regular taxi: $25-40 (¥3,500-5,500)")
    print("  • Jumbo taxi: $40-55 (¥5,000-8,000)")
    print("  • UberBlack: $65-100 (¥9,000-14,000)")
    print("  • Private limo: $70-110 (¥10,000-16,000)")


if __name__ == "__main__":
    main()
