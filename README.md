## Introduction
A python module that extracts values from GEE image collections for multiple points between two dates. For Landsat 8 [Level 1] and Sentinel 2 [Level 1], it also extracts the angle values [solar and sensor azimuth/zenith] and identifies the pixels as cloud or snow.

---

### How to use

```python
# ------------------------------ Example ------------------------------------ #

point_filename = r'path\to\point\shapefile.shp'
out_df = gee_point_extract(point_filename, sensor = 'Sentinel 2', start_date = '2020-12-01', end_date = '2020-12-31', id_col = 'ID', 
                  bands = ['B1', 'B8A'], product = None, scale = 10)   
```

If Sensor is not Landsat 8 or Sentinel 2, then sensor name could be set to anything, but a valid product ID should be specified. In fact, it is always recommended to specify a product ID. When `sensor = 'Landsat 8'`, then default `product = 'LANDSAT/LC08/C02/T1_TOA'`, which may not be the desired product. 

```python
point_filename = r'path\to\point\shapefile.shp'
out_df = gee_point_extract(point_filename, sensor = 'Others', start_date = '2022-12-01', end_date = '2022-12-31', id_col = 'ID', 
                  bands = ['Optical_Depth_047', 'Optical_Depth_055'], product = 'MODIS/061/MCD19A2_GRANULES', scale = 1000) 
```
