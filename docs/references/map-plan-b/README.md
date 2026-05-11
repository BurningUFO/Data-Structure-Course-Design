# Map Plan B Reference Materials

This directory stores local snapshots of reference materials used by the experimental `experiment/map-plan-b` branch.

## Source Files

| Local file | Source | Purpose |
| --- | --- | --- |
| `leaflet-geojson-example.html` | https://leafletjs.com/examples/geojson/ | Leaflet GeoJSON rendering examples |
| `leaflet-reference.html` | https://leafletjs.com/reference.html | Leaflet API reference |
| `rfc7946-geojson.txt` | https://www.rfc-editor.org/rfc/rfc7946.txt | GeoJSON standard, especially coordinate order and geometry types |
| `osmnx-getting-started.html` | https://osmnx.readthedocs.io/en/stable/getting-started.html | OSMnx workflow reference |
| `overpass-command-line.html` | https://dev.overpass-api.de/command_line.html | Overpass command line usage |
| `overpass-official-doc-index.html` | https://dev.overpass-api.de/overpass-doc/en/ | Overpass official documentation index |
| `mapshaper-command-reference.html` | https://mapshaper.org/docs/reference.html | Mapshaper command reference |
| `mapshaper-cli-command-line.html` | https://mapshaper.org/docs/essentials/command-line.html | Mapshaper command line workflow |
| `maplibre-add-geojson-line.html` | https://maplibre.org/maplibre-gl-js/docs/examples/add-a-geojson-line/ | Optional MapLibre comparison reference |
| `mapshaper-command-reference.md` | https://raw.githubusercontent.com/wiki/mbloch/mapshaper/Command-Reference.md | Historical wiki pointer to the moved Mapshaper docs |
| `mapshaper-cli-introduction.md` | https://raw.githubusercontent.com/wiki/mbloch/mapshaper/Introduction-to-the-Command-Line-Tool.md | Historical wiki pointer to the moved Mapshaper docs |

## Runtime Assets

Leaflet runtime assets are stored outside this reference directory:

```text
src/ui/static/vendor/leaflet/
```

Files downloaded there:

| Local file | Source |
| --- | --- |
| `leaflet.css` | https://unpkg.com/leaflet@1.9.4/dist/leaflet.css |
| `leaflet.js` | https://unpkg.com/leaflet@1.9.4/dist/leaflet.js |
| `images/marker-icon.png` | https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png |
| `images/marker-icon-2x.png` | https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png |
| `images/marker-shadow.png` | https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png |
| `LICENSE` | https://raw.githubusercontent.com/Leaflet/Leaflet/v1.9.4/LICENSE |

## Notes

Leaflet is the recommended first implementation target for this branch. MapLibre is kept only as a comparison reference because it has a higher visual ceiling but a higher integration risk.

