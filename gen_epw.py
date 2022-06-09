""" 
Workflow for automated epw file generation.
data from KNMI dataset are all use UTC time, 
imported epw file (e.g. from PVlib read_epw) are in localized time.

@Author: Bowen Tian
@Contact: b.tian@tue.nl
@Time: 08/06/2022 15:40 PM
"""

import numpy as np
import pandas as pd
import pvlib
import argparse
import os
import sys
import copy
import re
import urllib.request
import zipfile

def get_open_access_knmi(knmi_url, knmi_zip_dir, knmi_dir):
    # get knmi zip file name
    knmi_url = knmi_url.replace('\\', '/')
    print(knmi_url)
    filename = knmi_url.split('/')[-1].lower()
    zipped_file_dir = os.path.join(knmi_zip_dir, filename)
    # print(file_dir)

    def download_progress(block_num, block_size, total_size):
        '''
        # block_num: downloaded datablock
        # block_size: datablock size
        # total_size: total szie of the file
        '''
        sys.stdout.write('\r>> Downloading %s %.1f%%' % (filename,
                        float(block_num * block_size) / float(total_size) * 100.0))
        sys.stdout.flush()
    
    # download knmi
    print('Downloading form {}'.format(knmi_url))
    urllib.request.urlretrieve('https:' + knmi_url, zipped_file_dir, download_progress)
    # unzip it
    print('Unzipping')
    with zipfile.ZipFile(zipped_file_dir, 'r') as zip:
        zip.extractall(knmi_dir)
    print('Done')
    unzip_file_dir = os.path.join(knmi_dir, filename[:-4] + '.txt')
    return unzip_file_dir

def read_knmi_data(knmi_dir, starttime=None, endtime=None, skiprows=31):
    knmi = pd.read_csv(knmi_dir, sep=',', skiprows=skiprows)
    columns = []
    for col in knmi.columns:
        columns.append(col.strip())
    knmi.columns = columns

    for col in ['YYYYMMDD', 'HH']:
        knmi[col] = knmi[col].astype(str)

    for i, elem in enumerate(knmi['YYYYMMDD']):
        year = elem[:4]
        if int(year) % 4 == 0:
            month_data_dict = {'01': '31', '02': '29', '03': '31', '04': '30', '05': '31', '06': '30', 
                               '07': '31', '08': '31', '09': '30', '10': '31', '11': '30', '12': '31'}
        else:
            month_data_dict = {'01': '31', '02': '28', '03': '31', '04': '30', '05': '31', '06': '30', 
                               '07': '31', '08': '31', '09': '30', '10': '31', '11': '30', '12': '31'}
        month = elem[4:6]
        day = elem[6:]
        if not knmi['HH'][i] == '24':
            knmi['YYYYMMDD'][i] = year + '-' + month + '-' + day + ' '
        else:
            if not month_data_dict[month] == day:
                knmi['YYYYMMDD'][i] = year + '-' + month + '-' + str(int(day) + 1) + ' '
            else:
                if not month == '12':
                    knmi['YYYYMMDD'][i] = year + '-' + str(int(month) + 1) + '-' + '01' + ' '
                else:
                    knmi['YYYYMMDD'][i] = str(int(year) + 1) + '-' + '01' + '-' + '01' + ' '

    for i, elem in enumerate(knmi['HH']):
        if elem == '24':
            knmi['HH'][i] = '00:00:00'
        else:
            knmi['HH'][i] = elem + ':00:00'

    knmi['Datetime'] = knmi['YYYYMMDD'].str.cat([knmi['HH']], sep=' ', na_rep='-')
    knmi.drop(list(knmi.columns[:3]), axis=1, inplace=True)
    knmi.set_index('Datetime', inplace=True)
    knmi.index = pd.DatetimeIndex(knmi.index)
    if starttime == None and endtime == None:
        return knmi
    else:
        return knmi[starttime, endtime]

def read_epw_data(epw_dir, skiprows=8, coerce_year=2022, get_metadata=False):
    epw_ghi = pvlib.iotools.read_epw(epw_dir, coerce_year=coerce_year)[0]['ghi']
    # metadata = pd.read_csv(epw_dir, sep='\s\s\s', header=None, nrows=skiprows)
    metadata = []
    with open(epw_dir,'r') as epw:
        line_idx = 0
        for line in epw:
            metadata.append(line)
            line_idx += 1
            if line_idx >= skiprows:
                break
    epw_df = pd.read_csv(epw_dir, header=None, sep=',', skiprows=skiprows)
    # epw_df.index = epw_ghi.index.tz_convert('UTC')
    epw_df.index = epw_ghi.index

    for col in [0, 1, 2, 3, 4]:
        epw_df[col] = epw_df[col].astype(int)
    print(metadata)
    if get_metadata:
        return epw_df, metadata
    else:
        return epw_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Point Cloud Semantic Segmentation')
    parser.add_argument('--epw_source', type=str, default='C:/Tue/weather-and-solar/prepare_data/NLD_Amsterdam.062400_IWEC.epw',
                        help='folder for irradiance modelling')
    parser.add_argument('--knmi_geo_data', type=str, default='C:/Tue/weather-and-solar/prepare_data/knmi_STN_infor.csv',
                        help='folder for irradiance modelling')
    parser.add_argument('--epw_dir', type=str, default='C:/Tue/weather-and-solar/Weather Files/EnergyPlus EPW',
                        help='folder for Radiance wea weather files')
    parser.add_argument('--knmi_dir', type=str, default='C:/Tue/weather-and-solar/knmi',
                        help='folder for Radiance wea weather files')
    parser.add_argument('--knmi_zip_dir', type=str, default='C:/Tue/weather-and-solar/knmi_zip',
                        help='folder for Radiance wea weather files')
    parser.add_argument('--local_time_shift', type=float, default=1.0,
                        help='end time of weather file')
    parser.add_argument('--download_year', type=int, default=2021,
                        help='end time of weather file')

    args = parser.parse_args()
    download_year = args.download_year
    epw_source = args.epw_source
    knmi_geo_data = args.knmi_geo_data
    epw_dir = args.epw_dir
    knmi_dir = args.knmi_dir
    knmi_zip_dir = args.knmi_zip_dir
    local_time_shift = args.local_time_shift
    
    starttime = pd.Timestamp(str(download_year) + '-01-01 00:00:00')
    endtime = pd.Timestamp(str(download_year) + '-12-31 23:00:00')
    time_index = pd.date_range(str(starttime), str(endtime), freq='H')

    if download_year % 4 == 0:
        time_index = time_index.to_list()
        del time_index[1416:1440]

    if not os.path.exists(epw_dir):
        os.mkdir(epw_dir)
    if not os.path.exists(knmi_dir):
        os.mkdir(knmi_dir)
    if not os.path.exists(knmi_zip_dir):
        os.mkdir(knmi_dir)

    fail_list = []
    knmi_data_dict = {}
    knmi_data_df = pd.read_csv(knmi_geo_data)
    for stn in knmi_data_df.columns:
        knmi_data_dict[stn] = {'location': knmi_data_df[stn][0],
                               'abv': knmi_data_df[stn][1],
                               'latitude': float(knmi_data_df[stn][2]),
                               'longitude': float(knmi_data_df[stn][3]),
                               'url': {}, 'local_dir': {}, 'epw_dir':{}}

    BASE_URL = 'https://www.knmi.nl/nederland-nu/klimatologie/uurgegevens'
    KNMI_LINK_PATTERN = "<a href='(.*zip)'>"

    req = urllib.request.Request(BASE_URL)
    html = urllib.request.urlopen(req)
    doc = html.read().decode('utf8')
    url_list = list(set(re.findall(KNMI_LINK_PATTERN, doc)))

    for idx, url_element in enumerate(url_list):
        url_list[idx] = url_element.split("'")
        
    for idx, url_element in enumerate(url_list):
        del_list = []
        for i, url in enumerate(url_element):
            if not '.zip' in url:
                del_list.append(i)
        url_list[idx] = [ele for j, ele in enumerate(url_element) if j not in del_list]

    for url_list_seg in url_list:
        for url in url_list_seg:
            file_name = url.split('/')[-1].lower()
            if file_name[:6] == 'uurgeg':
                station_idx = file_name[7: 10]
                year_str = url.split('/')[-1][11: 20]
                start_years = year_str.split('-')[0]
                end_years = year_str.split('-')[-1]
                years = list(range(int(start_years), int(end_years) + 1))
                for year in years:
                    knmi_data_dict[station_idx]['url'][year] = url
                    knmi_data_dict[station_idx]['local_dir'][year] = os.path.join(knmi_dir, file_name[:-4] + '.txt')

    for stn in knmi_data_df.columns:
        location_folder = os.path.join(epw_dir, knmi_data_dict[stn]['location'])
        if not os.path.exists(location_folder):
            os.mkdir(location_folder)
        try:
            knmi_url = knmi_data_dict[stn]['url'][download_year]
            knmi_data_dict[stn]['local_dir'][download_year] = get_open_access_knmi(knmi_url, knmi_zip_dir, knmi_dir)
            knmi_data_dict[stn]['epw_dir'][download_year] = os.path.join(location_folder, 'NLD_' + knmi_data_dict[stn]['abv'] + '_EPW_YR' + str(download_year) + '.epw')
        except KeyError:
            continue
    
    local_starttime = starttime + pd.DateOffset(hours=local_time_shift)
    local_endtime = endtime + pd.DateOffset(hours=local_time_shift)

    epw, meta = read_epw_data(epw_source, skiprows=8, coerce_year=2021, get_metadata=True)
    epw_ori_mon_cols = epw[1].to_list()
    epw_ori_day_cols = epw[2].to_list()
    epw_ori_hrs_cols = epw[3].to_list()

    epw_seg1 = epw.iloc[0: 2, :]
    epw_seg2 = epw.iloc[1:, :]
    epw = pd.concat([epw_seg2, epw_seg1]).iloc[:-1,:]
    epw.index = time_index

    for stn in knmi_data_df.columns:
        if not knmi_data_dict[stn]['local_dir'] == {}:
            try:
                print('converting {} to epw file'.format(knmi_data_dict[stn]['local_dir'][download_year]))
            except KeyError:
                fail_list.append(knmi_data_dict[stn]['location'])
                continue

            knmi_data = read_knmi_data(knmi_data_dict[stn]['local_dir'][download_year])
            knmi_ori_index = knmi_data.index.to_list()
            knmi_data.index = pd.to_datetime(knmi_ori_index)

            new_meta = copy.deepcopy(meta)
            new_epw = copy.deepcopy(epw)

            geo_data = new_meta[0].split(',')
            geo_data[1] = knmi_data_dict[stn]['location']

            if not np.isnan(knmi_data_dict[stn]['latitude']):
                geo_data[-4] = str(knmi_data_dict[stn]['latitude'])
                geo_data[-3] = str(knmi_data_dict[stn]['longitude'])
            new_meta[0] = ''.join(e + ',' for e in geo_data[:-1])
            new_meta[0] = new_meta[0] + geo_data[-1]

            # epw_slice = new_epw[local_starttime:local_endtime]
            epw_slice = new_epw
            knmi_slice = knmi_data[local_starttime:local_endtime]

            if download_year % 4 == 0:
                try:
                    drop_idx = pd.date_range(str(download_year)+'-02-29 00:00:00', str(download_year)+'-02-29 23:00:00', freq='H')
                    knmi_slice.drop(drop_idx.to_list(), axis=0, inplace=True)
                except KeyError:
                    fail_list.append(knmi_data_dict[stn]['location'])
                    continue

            times = knmi_slice.index
            solpos = pvlib.solarposition.get_solarposition(times, knmi_data_dict[stn]['latitude'], knmi_data_dict[stn]['longitude'])
            solar_zenith = solpos['apparent_zenith']

            wind_direction = knmi_slice['DD']
            wind_speed = knmi_slice['FH']
            dry_t = knmi_slice['T']
            drew_t = knmi_slice['TD']
            prec_hrs = knmi_slice['DR']
            prec_mm = knmi_slice['RH']
            pressure = knmi_slice['P']
            visibility = knmi_slice['VV']
            sky_cover = knmi_slice['N']
            rel_humi = knmi_slice['U']
            pre_wea_observe = knmi_slice['R']
            ghi = knmi_slice['Q']

            # knmi_data_df = pd.DataFrame([wind_direction, wind_speed, dry_t, drew_t, prec_hrs, prec_mm, pressure, visibility, sky_cover, rel_humi, ghi]).T
            knmi_data_df = pd.concat([wind_direction, wind_speed, dry_t, drew_t, prec_hrs, prec_mm, pressure, visibility, sky_cover, rel_humi, pre_wea_observe, solar_zenith, ghi], axis=1)
            knmi_data_df.columns = ['DD', 'FH', 'T', 'TD', 'DR', 'RH', 'P', 'VV', 'N', 'U', 'R', 'solar_zenith', 'ghi']

            unit_conversion_dict = {'ghi': 10000 / 3600, 'DD': 1, 'FH': 0.1, 'T': 0.1, 'TD': 0.1, 'DR': 0.1,
                                    'RH': 0.1, 'P': 10, 'VV': 0.1, 'N': 10 / 9, 'U': 1, 'R': 1, 'solar_zenith': 1}
            
            knmi_data_df.fillna(np.nan, inplace=True)
            knmi_data_df.replace("     ", np.nan, inplace=True)
            for col in knmi_data_df.columns:
                knmi_data_df[col] = pd.to_numeric(knmi_data_df[col], downcast='float')
                knmi_data_df[col] *= unit_conversion_dict[col]

            knmi_data_df['N'] = knmi_data_df['N'].round()
            knmi_data_df_slice1 = knmi_data_df[knmi_data_df['R'] == 0]
            knmi_data_df_slice2 = knmi_data_df[knmi_data_df['R'] == 1]
            knmi_data_df_slice1['R'] = 9
            knmi_data_df_slice2['R'] = 0
            knmi_data_df.update(knmi_data_df_slice1)
            knmi_data_df.update(knmi_data_df_slice2)

            knmi_data_df['DD'] = knmi_data_df['DD'].astype(float)
            knmi_data_df_slice3 = knmi_data_df[knmi_data_df['DD'] == 360]
            knmi_data_df_slice3['DD'] = 0.0
            knmi_data_df.update(knmi_data_df_slice3)

            try:
                knmi_data_df['dni'] = pvlib.irradiance.dirint(knmi_data_df['ghi'], knmi_data_df['solar_zenith'], times)
                knmi_data_df['dhi'] = knmi_data_df['ghi'] - knmi_data_df['dni'] * pvlib.tools.cosd(knmi_data_df['solar_zenith'])
                knmi_data_df.drop(['solar_zenith'], axis=1, inplace=True)
            except IndexError:
                fail_list.append(knmi_data_dict[stn]['location'])
                continue

            knmi_data_df['DD'].fillna(999, inplace=True)
            knmi_data_df['FH'].fillna(999, inplace=True)
            knmi_data_df['T'].fillna(99.9, inplace=True)
            knmi_data_df['TD'].fillna(99.9, inplace=True)
            knmi_data_df['DR'].fillna(0, inplace=True)
            knmi_data_df['RH'].fillna(0, inplace=True)
            knmi_data_df['P'].fillna(999999, inplace=True)
            knmi_data_df['VV'].fillna(9999, inplace=True)
            knmi_data_df['N'].fillna(99, inplace=True)
            knmi_data_df['U'].fillna(999, inplace=True)
            knmi_data_df['R'].fillna(9, inplace=True)
            knmi_data_df['dni'].fillna(0, inplace=True)
            knmi_data_df['dhi'].fillna(0, inplace=True)

            knmi_data_df.index = epw_slice.index
            epw_col_index_dict = {'ghi': 13, 'dni': 14, 'dhi': 15, 'DD': 20, 'FH': 21, 'T': 6, 'TD': 7, 'DR': 34,
                                  'RH': 33, 'P': 9, 'VV': 24, 'N': 23, 'U': 8, 'R': 26}
            
            for col in knmi_data_df.columns:
                epw_slice.iloc[:, epw_col_index_dict[col]] = knmi_data_df[col]
            
            epw_slice[1] = epw_ori_mon_cols   
            epw_slice[2] = epw_ori_day_cols   
            epw_slice[3] = epw_ori_hrs_cols   

            int_col = [0, 1, 2, 3, 4]
            int_col.extend(list(range(8, 21)))
            int_col.extend([22, 23, 25, 26, 27, 28, 30, 31])
            for col in int_col:
                epw_slice[col] = epw_slice[col].astype(int, errors='ignore')

            epw_slice.to_csv(knmi_data_dict[stn]['epw_dir'][download_year], sep=',', index=False, header=False)

            f = open(knmi_data_dict[stn]['epw_dir'][download_year], 'r+')
            lines = f.readlines() # read old content
            f.seek(0) # go back to the beginning of the file
            for line in new_meta: # write new content
                f.write(line)
            for line in lines: # write old content after new
                f.write(line)
            f.close()
    print('epw file for {} generated completely, station {} file generated fail due to data missing'.format(download_year, fail_list))
