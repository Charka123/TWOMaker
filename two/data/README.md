# Basemap data

These Natural Earth 1:50m layers come from the pinned v5.1.2 repository release.
They are bundled unchanged so image generation needs no network connection.

- Land: https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_50m_land.geojson
- Lakes: https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_50m_lakes.geojson
- Country borders: https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_50m_admin_0_boundary_lines_land.geojson
- State boundaries: https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_50m_admin_1_states_provinces_lines.geojson
- License: public domain, https://www.naturalearthdata.com/about/terms-of-use/

The renderer selects only `ADM0_A3 == "USA"` from the state boundary layer.
Country borders use the source's default boundary representation. Country lines
are darker and thicker than state lines; disturbance markings are drawn last.
Lakes are filled with the ocean color above land and below borders, preserving
lake islands as land. This includes all five Great Lakes.
Small islands and coastlines are still simplified at this scale, but are more
detailed than the previous 1:110m basemap.
