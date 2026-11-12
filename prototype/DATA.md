# Data used by the Stonehenge prototypes

All open data. Fetched on 12 November 2026. The prototype scripts hold absolute paths from the
test session; replace them with paths inside the new repository.

## Stone footprints, ditch and bank: OpenStreetMap
- Fetch: `https://www.openstreetmap.org/api/0.6/map?bbox=-1.8275,51.1782,-1.8250,51.1796` (XML, WGS84).
- 47 stone footprints (`historic=stone` + `natural=stone`; a few carry `name` and `ref`: Heel Stone 96,
  Slaughter Stone 95, Altar Stone 80, Station Stones 91 and 93), the ditch (`barrier=ditch`), the bank
  (`man_made=embankment`), the North and South Barrows.
- Licence: ODbL 1.0. Credit: "(c) OpenStreetMap contributors". `phase-model/osm_ways.json` is the parsed copy.

## Laser scan: Environment Agency National LIDAR Programme, tile SU1040
- Catalogue search: POST a GeoJSON polygon (Content-Type `application/geo+json`) to
  `https://environment.data.gov.uk/backend/catalog/api/tiles/collections/survey/search`.
- Files (zip): `https://environment.data.gov.uk/tiles/collections/survey/<product>/<year>/1/SU1040` with
  - `national_lidar_programme_point_cloud/2021`: LAZ, 65.8 million points, EPSG:27700, flown 2021-04-04,
    classes 1, 2 (ground), 3-5; about 1.7 points per square metre at the stones (188 MB)
  - `national_lidar_programme_dsm/2021`: 1 m surface model (GeoTIFF)
  - `lidar_composite_dtm/2022`: 1 m ground model (GeoTIFF)
- Stonehenge's centre is near E 412245, N 142195.
- Licence: expected Open Government Licence v3.0. Confirm the exact attribution wording before release.
- Python: `pip install laspy lazrs tifffile`.

## Archive scans: William Stukeley, "Stonehenge, a temple restor'd to the British Druids" (London, 1740)
- Wellcome Library copy on the Internet Archive, identifier `b30448554`, Public Domain Mark.
- Full-resolution page scans: `https://archive.org/download/b30448554/b30448554_jp2.zip` (164 JP2, 121 MB);
  record: `https://archive.org/metadata/b30448554`.
- Plates used: scan 0067 = TAB. XIII, "Prospect of Stonehenge from the Southwest", p. 24;
  scan 0059 = TAB. XI, "The Geometrical Ground-plot of Stonehenge" (the circle drawn complete).
- Wikimedia Commons rate-limited the test machine; the Internet Archive and the Library of Congress were reachable.

## Narrator
- `pip install kokoro-onnx soundfile`; model files `kokoro-v1.0.onnx` and `voices-v1.0.bin` from
  `https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/`. Kokoro-82M is Apache-2.0.
- Chosen voice: `bm_fable`, lang `en-gb`, speed 0.92. Example: `voice/synth.py`.

## Style reference
- `styles/white-model/STYLE.md` and `styles/archive-lighttable/STYLE.md` in github.com/lemomo-ai/lemo-opuscar (MIT).
  Design reference only: its demo code, assets and colours were not used.

## Not carried over
- The laser-scan look was tested and not chosen. The ground model shows the ditch and bank clearly but not the Avenue.
