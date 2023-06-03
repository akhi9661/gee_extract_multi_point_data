## Introduction
A python module that extracts values from GEE image collections for multiple points between two dates and saves it to excel. For Landsat 8 [[Level 1](LANDSAT/LC08/C02/T1_TOA)] and Sentinel 2 [[Level 1](COPERNICUS/S2_HARMONIZED)], it also extracts the angle values [solar and sensor azimuth/zenith] and identifies the pixels as cloud or snow. Neverthless, if not present by default, any or all available bands can be specified. 

---

### How to use

```python
# ------------------------------ Example ------------------------------------ #

point_filename = r'path\to\point\shapefile.shp'
out_df = gee_point_extract(point_filename, product = 'LANDSAT/LC08/C02/T1_L2', start_date = '2022-12-01', end_date = '2022-12-31', id_col = 'ID', 
                  bands = ['SR_B1', 'SR_B5'], scale = 30)  
```
Check out: [gee_subset](https://github.com/bluegreen-labs/gee_subset)
