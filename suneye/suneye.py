import pandas as pd
import datetime
import numpy as np

def read_suneye_shade_file(file_path, year=2001):
    "Returns measured shading dataframe for the given year, with 15 minutes resolution. 1=SunVisible, 0=SunNotVisible"
    ## preprocess the text file
    timedelta = '15T'
    shading_file = open(file_path)
    sfl = shading_file.readlines()
    for line_count in range(len(sfl)):
        sfl[line_count] = sfl[line_count][:-1]
    hours = sfl[15].split(sep=',')    # make a list from the line with the hours
    del hours[0]    # get rid of begin data
    for h in range(len(hours)):
        hours[h] = datetime.time(int(hours[h].split(':')[0]), int(hours[h].split(':')[1]))
    ## Numbering months
    month_list = ['Jan ', 'Feb ', 'Mar ', 'Apr ', 'May ', 'Jun ', 'Jul ', 'Aug ', 'Sep ', 'Oct ', 'Nov ', 'Dec ']
    for line_count in range(16, len(sfl), 1):
        for month in month_list:
            sfl[line_count] = sfl[line_count].replace(month, str(month_list.index(month)+1)+',')
    sfl = sfl[16:]  # getting rid of unnecessary lines
    ## generate Timestamp
    year_time_index = pd.date_range(start=str(year)+'-01-01 00:00:00', end=str(year)+'-12-31 23:45:00', freq=timedelta)
    df_shading = pd.DataFrame(index=year_time_index)
    df_time_pos_lookup = pd.DataFrame(data=np.array(range(len(hours))), index=hours, columns=['idx'])
    ## make df_shading
    shade_lst = []
    for i in df_shading.index:
        if datetime.time(i.hour, i.minute) < hours[0] or datetime.time(i.hour, i.minute) > hours[-1]:
            shade_lst.append(np.nan)
        else:
            shade_lst.append(float(sfl[i.timetuple().tm_yday-1].split(',')[2:][df_time_pos_lookup.at[datetime.time(i.hour, i.minute), 'idx']].strip() or np.nan))
    df_shading['MeasuredShade'] = shade_lst
    return df_shading
