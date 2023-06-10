def gee_point_extract(point_filename, product = 'LANDSAT/LC08/C02/T1_TOA', start_date = '2020-12-01', end_date = '2020-12-31', id_col = None, 
                      bands = ['B1', 'B2', 'B3', 'B4'], pad = 0, scale = 30, dest_folder = None):
    
    '''
    This function takes a point shapefile and extracts the pixel values for the specified bands from the specified sensor from 
    Google Earth Engine. The function returns a dataframe with the pixel values for each band and the latitude and longitude of
    the point. The function also returns a dataframe with the metadata [angle, QA_mask] for each point. 

    Parameters:
        point_filename (string): The filename of the point shapefile, a pandas dataframe or a csv file.
        product (string): The product ID of the sensor. Default is 'LANDSAT/LC08/C02/T1_TOA'. 
        start_date (string): The start date of the time period of interest. Format is 'YYYY-MM-DD'. Default is '2020-12-01'
        end_date (string): The end date of the time period of interest. Format is 'YYYY-MM-DD'. Default is '2020-12-31'
        id_col (string): The name of the column in the point shapefile that contains the unique ID for each point. Default is 'FID'.
        bands (list): A list of the bands to extract from the sensor. Default is ['B1', 'B2', 'B3', 'B4'].
        scale (int): The scale of the pixel values. Default is 30.
        dest_folder (string): The destination folder to save the output csv file. Default is None.

    Returns:
        final_df (pandas dataframe): A dataframe with the pixel, angle, and QA_mask values for each band
    
    '''
    
    import ee
    import os
    import re
    from gee_subset import gee_subset
    import pandas as pd
    from datetime import datetime
    import geopandas as gpd
    
    if not ee.data._credentials:
        ee.Authenticate()

    if not ee.data._initialized:
        ee.Initialize()
    
    if dest_folder is not None:
        opf = os.path.join(dest_folder, f'{product.split("/")[-1]}_{start_date}_{end_date}.csv')
    print(f'Processing: Fetching satellite data from "{product}" for time period: [{start_date, end_date}]\n')

    if product == 'LANDSAT/LC08/C02/T1_TOA':
        extra_bands = ['SAA', 'SZA', 'VAA', 'VZA', 'QA_PIXEL']
        for band in extra_bands:
            if band not in bands:
                bands.append(band)
        scale = 30

    if product == 'COPERNICUS/S2_HARMONIZED':
        extra_bands = ['QA60']
        for band in extra_bands:
            if band not in bands:
                bands.append('QA60')
        scale = 10

    if product is None:
        print('Enter a valid product ID')

    if isinstance(point_filename, pd.DataFrame):
        points = point_filename
        if dest_folder is None:
            opf = os.path.join(os.getcwd(), f'{product.split("/")[-1]}_{start_date}_{end_date}.csv')
    elif isinstance(point_filename, str) and point_filename.endswith('.shp'):
        points = gpd.read_file(point_filename)
        if dest_folder is None:
            opf = os.path.join(os.path.dirname(point_filename), f'{product.split("/")[-1]}_{start_date}_{end_date}.csv')
    elif isinstance(point_filename, str) and point_filename.endswith('.csv'):
        points = gpd.read_csv(point_filename)
        if dest_folder is None:
            opf = os.path.join(os.path.dirname(point_filename), f'{product.split("/")[-1]}_{start_date}_{end_date}.csv')
    else:
        print("Invalid input. Expected either a pandas dataframe or csv/shapefile path.")

    count = len(points)
    site = list(range(0, count, 1))    

    values = []

    for i in site:

        print(f"Extracting for {id_col}: {points.iloc[i, points.columns.get_loc(id_col)]}", end = '\r')
        print(' ' * 50, end='\r')
        df = gee_subset.gee_subset(product = product,
                                   bands = bands,
                                   start_date = start_date,
                                   end_date = end_date,
                                   latitude = points.iloc[i, points.columns.get_loc('lat')],
                                   longitude = points.iloc[i, points.columns.get_loc('lon')], 
                                   scale = scale, 
                                   pad = pad)
    
        sid =  str(points.iloc[i, points.columns.get_loc(id_col)])
        df[id_col] = sid
        values.append(df)
        
    df1 = pd.concat(values, ignore_index = True)        
    if 'QA_PIXEL' in bands or 'QA60' in bands:
        final_df = process_bitmask(df1)
    else:
        final_df = df1.copy()
    
    if product == 'COPERNICUS/S2_HARMONIZED':
        
        print(f'Processing: Fetching azimuth and zenith (solar & sensor) from "{product}"\n')
        for band in bands:
            if band == 'QA60':
                continue  
            final_df[band] = final_df[band] * 0.0001
        
        collection = ee.ImageCollection('COPERNICUS/S2')
        cols = [id_col, 'latitude', 'longitude', 'SAA', 'SZA']
            
        df_meta = pd.DataFrame(columns = cols)
        for index, row in points.iterrows():
            latitude = row['lat']
            longitude = row['lon']
            id_var = row[id_col]
            point = ee.Geometry.Point(longitude, latitude)
            filteredCollection = collection.filterBounds(point).filterDate(start_date, end_date)
            image = ee.Image(filteredCollection.sort('system:time_start').first())

            SAA = image.get('MEAN_SOLAR_AZIMUTH_ANGLE')
            SZA = image.get('MEAN_SOLAR_ZENITH_ANGLE')

            df_meta = pd.concat([df_meta, pd.DataFrame({id_col: [id_var], 'latitude': [latitude], 'longitude': [longitude],
                                            'SAA': [SAA.getInfo()], 'SZA': [SZA.getInfo()]},
                                            index=[len(df_meta)])],
                    ignore_index=True)

            for band in bands:
                if band == 'QA60':
                    continue
                azimuth = image.get(f'MEAN_INCIDENCE_AZIMUTH_ANGLE_{band}')
                zenith = image.get(f'MEAN_INCIDENCE_ZENITH_ANGLE_{band}')

                df_meta.at[len(df_meta) - 1, f'VAA_{band}'] = azimuth.getInfo()
                df_meta.at[len(df_meta) - 1, f'VZA_{band}'] = zenith.getInfo()
                
        merged_df = final_df.merge(df_meta, on = id_col)
        merged_df.to_csv(opf, index = False)
        return merged_df
        
    elif product == 'LANDSAT/LC08/C02/T1_TOA':
        final_df['SAA'] = final_df['SAA'] * 0.01
        final_df['SZA'] = final_df['SZA'] * 0.01 
        final_df['VAA'] = final_df['VAA'] * 0.01
        final_df['VZA'] = final_df['VZA'] * 0.01
        
        final_df.to_csv(opf, index = False)
        return final_df
    
    else:
        final_df.to_csv(opf, index = False)
        return final_df
