def process_bitmask(dataframe):

    '''
    This function takes a dataframe with a column named 'QA_PIXEL' or 'QA60' and creates a new column named 'Cloud/Snow' 
    depending on the binary values of the QA_PIXEL or QA60 column. The function returns a dataframe with the new column.

    Parameters:
        dataframe (pandas dataframe): A dataframe with a column named 'QA_PIXEL' or 'QA60'

    Returns:
        updated_dataframe (pandas dataframe): A dataframe with a new column named 'Cloud/Snow'
    
    '''
    
    def convert_to_dictionary(qa_pixel):

        '''
        This function takes a QA_PIXEL value and converts it to a dictionary with the binary values of the QA_PIXEL as keys 
        and the binary values as values.

        Parameters:
            qa_pixel (int): A QA_PIXEL value

        Returns:
            binary_dict (dictionary): A dictionary with the binary values of the QA_PIXEL as keys and the binary values as values
        
        '''

        binary_str = bin(qa_pixel)[2:].zfill(16)  # Convert to binary string and pad with zeros to 16 bits
        binary_dict = {f'Bit {i}': bit for i, bit in enumerate(binary_str[::-1])}
        return binary_dict

    rows_with_bits = []
    headers = dataframe.columns.tolist()
    headers.append('Cloud/Snow')

    for index, row in dataframe.iterrows():
        if 'QA_PIXEL' in headers:
            mask = 'QA_PIXEL'
            qa_pixel = int(row['QA_PIXEL'])
            binary_dict = convert_to_dictionary(qa_pixel)
            cloud_snow = 'Cloud' if binary_dict['Bit 3'] == '1' else 'Snow' if binary_dict['Bit 5'] == '1' else ''
            
        elif 'QA60' in headers:
            mask = 'QA60'
            qa_60 = int(row['QA60'])
            binary_dict = convert_to_dictionary(qa_60)
            cloud_snow = 'Cloud' if binary_dict['Bit 10'] == '1' or binary_dict['Bit 11'] == '1' else ''
            
        else:
            cloud_snow = ''
        
        row['Cloud/Snow'] = cloud_snow
        rows_with_bits.append(row)
    
    updated_dataframe = pd.DataFrame(rows_with_bits, columns = headers)
    return updated_dataframe

def gee_point_extract(point_filename, sensor, start_date = '2020-12-01', end_date = '2020-12-31', id_col = 'FID', 
                      bands = ['B1', 'B2', 'B3', 'B4'], product = None, scale = 10):
    
    '''
    This function takes a point shapefile and extracts the pixel values for the specified bands from the specified sensor from 
    Google Earth Engine. The function returns a dataframe with the pixel values for each band and the latitude and longitude of
    the point. The function also returns a dataframe with the metadata [angle, QA_mask] for each point. 

    Parameters:
        point_filename (string): The filename of the point shapefile
        sensor (string): The name of the sensor. Valid options are 'Landsat 8' and 'Sentinel 2'. If other sensor name is used, a valid product ID must be specified. Sensor name could be set to anything. 
        start_date (string): The start date of the time period of interest. Default is '2020-12-01'
        end_date (string): The end date of the time period of interest. Default is '2020-12-31'
        id_col (string): The name of the column in the point shapefile that contains the unique ID for each point. Default is 'FID'
        bands (list): A list of the bands to extract from the sensor. Default is ['B1', 'B2', 'B3', 'B4']
        product (string): The product ID for the sensor. Default is None
        scale (int): The scale of the pixel values. Default is 10

    Returns:
        final_df (pandas dataframe): A dataframe with the pixel, angle, and QA_mask values for each band
    
    '''
    
    import ee
    import os, re
    from gee_subset import gee_subset
    import pandas as pd
    from datetime import datetime
    import geopandas as gpd
    
    if not ee.data._credentials:
        ee.Authenticate()

    if not ee.data._initialized:
        ee.Initialize()

    if sensor == 'Landsat 8':
        scale = 30
        product = 'LANDSAT/LC08/C02/T1_TOA'
        bands.append('SAA')
        bands.append('SZA')
        bands.append('VAA')
        bands.append('VZA') 
        bands.append('QA_PIXEL')
        
    elif sensor == 'Sentinel 2':
        scale = 10
        product = 'COPERNICUS/S2_HARMONIZED'
        bands.append('QA60')
        
    else:
        if product is None:
            print('Enter a valid product ID')
        
    points = gpd.read_file(point_filename)
    count = len(points)
    site = list(range(0, count, 1))
    
    values = []

    for i in site:
        
        df = gee_subset.gee_subset(product = product,
        bands = bands,
        start_date = start_date,
        end_date = end_date,
        latitude = points.iloc[i, 2],
        longitude = points.iloc[i, 1], 
        scale = scale)
    
        sid =  str(points.iloc[i, 0])
        df[id_col] = sid
        values.append(df)
        
    df1 = pd.concat(values, ignore_index = True)
    final_df = process_bitmask(df1)  
    
    if sensor == 'Sentinel 2':
        
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
        merged_df.to_csv(os.path.join(os.path.dirname(point_filename), f'{sensor}_{start_date}_{end_date}.csv'), index = False)
        return merged_df
        
    elif sensor == 'Landsat 8':
        final_df['SAA'] = final_df['SAA'] * 0.01
        final_df['SZA'] = final_df['SZA'] * 0.01 
        final_df['VAA'] = final_df['VAA'] * 0.01
        final_df['VZA'] = final_df['VZA'] * 0.01
        
        final_df.to_csv(os.path.join(os.path.dirname(point_filename), f'{sensor}_{start_date}_{end_date}.csv'), index = False)
        return final_df
    
    else:
        final_df.to_csv(os.path.join(os.path.dirname(point_filename), f'{sensor}_{start_date}_{end_date}.csv'), index = False)
        return final_df

# ------------------------------ Example ------------------------------------ #

point_filename = r'path\to\point\shapefile.shp'
out_df = gee_point_extract(point_filename, sensor = 'Sentinel 2', start_date = '2020-12-01', end_date = '2020-12-31', id_col = 'ID', 
                  bands = ['B1', 'B8A'], product = None, scale = 10)       
