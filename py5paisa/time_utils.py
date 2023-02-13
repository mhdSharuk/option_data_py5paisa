import datetime

month_list = ['Jan','Feb','Mar',
              'Apr','May','Jun',
              'Jul','Aug','Sep',
              'Oct','Nov','Dec'] 
MONTH = {m:str(i+1).zfill(2) for i,m in enumerate(month_list)}

def getEpochTime(date_input, sep='-'):
    date_input = date_input.split(sep)
    try:
      year = int(date_input[0])
      month = int(date_input[1])
      day = int(date_input[2])
    except:
      day = int(date_input[0])
      month = int(MONTH[date_input[1]])
      year = int(date_input[2])

    epoch = datetime.datetime(year, month, day, 9, 0, 0).strftime('%s')
    return int(epoch)*1000

def convertTimeString(date, 
      from_format="%Y-%m-%d", 
      to_format='%d %b %Y'):

      return datetime.datetime.strptime(date, from_format).strftime(to_format)
