import json
import re

html_path = "/home/john/Thunderbird/cruises_web/itinerary_splendor_lyons.html"
with open(html_path, "r") as f:
    html = f.read()

# 1. Insert Transfeero - ATH to Grande Bretagne and Dinner on Aug 10
aug10_insertion = """
<div class="day-details">
    <h3>Transfers & Activities</h3>
    <ul>
        <li><strong>12:20 PM:</strong> Transfer via Transfeero from ATH Airport to Hotel Grande Bretagne</li>
        <li><strong>7:00 PM (19:00):</strong> Dinner Reservation at Grande Bretagne Roof Garden Restaurant</li>
    </ul>
</div>
"""
html = html.replace('<h2>Day 0 - August 10, 2026 - Piraeus (Athens), Greece</h2>', '<h2>Day 0 - August 10, 2026 - Piraeus (Athens), Greece</h2>\n' + aug10_insertion)

# 2. Insert Transfeero to ship on Aug 11
aug11_insertion = """
<div class="day-details">
    <h3>Transfers</h3>
    <ul>
        <li><strong>11:30 AM:</strong> Transfer via Transfeero from Hotel Grande Bretagne to Ship</li>
    </ul>
</div>
"""
html = html.replace('<h2>Day 1 - August 11, 2026 - Piraeus (Athens), Greece</h2>', '<h2>Day 1 - August 11, 2026 - Piraeus (Athens), Greece</h2>\n' + aug11_insertion)

# 3. Handle Sep 6 (End of cruise) transfers and flights
# Wait, let's see if Sep 6 is Day 26 or Day 27. It's the disembarkation day.
# Actually, the user wants transfers at the bottom of the email or bottom of the itinerary?
# "Place the Dinner Reservation and air inline on the date they are scheduled for. Place the transfers at the bottom."
# Let's add a "Post-Cruise Transfers & Flights" section at the end of the HTML.

transfers_section = """
<div class="day">
    <h2>Post-Cruise Transfers & Flights (September 6, 2026)</h2>
    <div class="day-details">
        <ul>
            <li><strong>9:00 AM:</strong> Transfer from Ship to LaGuardia Airport (LGA)</li>
            <li><strong>12:29 PM - 3:01 PM:</strong> Flight: Delta 2005 (LGA to JAX)</li>
            <li><strong>3:01 PM:</strong> Transfer via Bob's Taxi from JAX Airport to Home</li>
        </ul>
    </div>
</div>
"""
html = html.replace('</body>', transfers_section + '\n</body>')

with open(html_path, "w") as f:
    f.write(html)
