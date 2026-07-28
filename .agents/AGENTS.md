# Workspace Rules & Lessons Learned

## Regent Seven Seas Cruises Portal Automation
* **Login Modal Flow**: Do not attempt to load the `/sign-in` URL directly (which returns a 404). Always navigate to the homepage (`https://www.rssc.com/`) first, wait for the page load, accept cookies if prompted, and click on `a[href*="modal-mainHeader-my-account"]` to open the sign-in modal.
* **Direct Purchases Scraping**: Instead of relying on UI colorbox popup clicks to parse booked activities, execute a direct `fetch` POST request in the browser context to `/WebServices/Booking/Booking.asmx/GetPurchasesDetailsPopUpHtml` with payload `{"bookingNumber": "2979301", "iata": "32535134"}`. This returns a clean HTML body containing all excursions.
* **Preventing Context Destruction**: When clicking on sequential itinerary days, postback events can destroy the browser context. Refresh the page or navigate back to the main booking details URL between clicks to ensure a fresh, valid DOM context.
