# SKILL: Itinerary Map Generation (A6/A3 Hybrid)
**Trigger:** Whenever a travel itinerary, day trip, or walking route is finalized for a client.
**Output Location:** `/home/john/Thunderbird/output/` (for immediate web viewing) and `/home/john/Thunderbird/reverie/` (for backup).

## DIRECTIVE
When an itinerary is complete, you must offer to (or autonomously) generate a high-resolution, interactive Leaflet HTML map to visually render the spatial flow of the day for the client.

## THE HTML TEMPLATE
You must strictly use this HTML/JS template. Do NOT use Mermaid flowcharts or raw `.md` files for geographic routing. 

### Key Features Required in the Template:
1.  **Base Layer:** Esri World Imagery (Satellite) overlaid with CartoDB Labels.
2.  **Markers:** Use `L.circleMarker` or custom pins. You MUST include `bindTooltip` for hover-effects so clients don't have to click to see the description.
3.  **Routing:** 
    *   For walking/driving: Connect the coordinates using an array of lat/lng points via `L.polyline`.
    *   For trains: Use a dashed polyline (`dashArray: '10, 10'`).
4.  **Auto-Bounds:** Always end the script with `map.fitBounds(polyline.getBounds(), { padding: [50, 50] });` so the map auto-focuses on the route.

### Example Code Block to Inject:
```html
<!DOCTYPE html>
<html>
<head>
    <title>[ITINERARY TITLE]</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>body { padding: 0; margin: 0; } #map { height: 100vh; width: 100vw; }</style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([0, 0], 2); 
        
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19
        }).addTo(map);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png', {
            maxZoom: 19
        }).addTo(map);

        var points = [
            { lat: 35.6812, lng: 139.7671, name: "Tokyo", desc: "Departure point" }
        ];

        var routeCoords = points.map(p => [p.lat, p.lng]);
        var routeLine = L.polyline(routeCoords, { color: '#e74c3c', weight: 4 }).addTo(map);

        points.forEach(p => {
            L.circleMarker([p.lat, p.lng], { radius: 8, fillColor: "#3498db", color: "#fff", weight: 2, fillOpacity: 0.9 })
            .addTo(map)
            .bindTooltip("<b>" + p.name + "</b><br>" + p.desc, { direction: 'top', offset: [0, -10] });
        });

        map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
    </script>
</body>
</html>
```

## OSRM / NOMINATIM NOTE
Do not guess coordinates. Scrape them from Maps, use native tools, or query the Nominatim API directly before rendering.
