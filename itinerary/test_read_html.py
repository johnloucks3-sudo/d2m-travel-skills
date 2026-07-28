with open("/home/john/Thunderbird/itinerary/lyons_itinerary.html", "r") as f:
    html = f.read()

import re
aug10 = re.search(r'(?s)(August 10.*?</div>)', html)
print(aug10.group(1) if aug10 else "Not found")
