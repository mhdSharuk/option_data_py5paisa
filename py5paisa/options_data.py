import time
import warnings
import traceback
import datetime
import numpy as np
import pandas as pd
import multiprocessing

from IPython.display import clear_output, display, HTML
from .py5paisa import FivePaisaClient
from .custom_exceptions import InvalidLoginCredentialsException
from .custom_exceptions import InvalidFutureExpiryDateException
from .custom_exceptions import InvalidLoginException
from .custom_exceptions import FetchExpiryException, InvalidOptionExpiryDateException
from .custom_exceptions import FuturesFetchException, SpotFetchException, OptionChainFetchException
from .time_utils import getEpochTime

warnings.filterwarnings('ignore')
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

month_list = ['Jan','Feb','Mar',
              'Apr','May','Jun',
              'Jul','Aug','Sep',
              'Oct','Nov','Dec']
MONTH = {m:str(i+1).zfill(2) for i,m in enumerate(month_list)}

NIFTY_SCRIP_CODE = '999920000'
BANK_SCRIP_CODE = '999920005'
FINNIFTY_SCRIP_CODE = '999920041'

class CustomMultiProcess(multiprocessing.Process):
    def __init__(self, *args, **kwargs):
        multiprocessing.Process.__init__(self, *args, **kwargs)
        self._pconn, self._cconn = multiprocessing.Pipe()
        self._exception = None

    def run(self):
        try:
            multiprocessing.Process.run(self)
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))

    @property
    def exception(self):
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception

class FetchOptionData:
  def __init__(self, creds, email, 
               pwd, dob, 
               NF_BNF_OPT_EXPIRY_EPOCH_TIME,
               FIN_OPT_EXPIRY_EPOCH_TIME,
               INCLUDE_NIFTY, 
               INCLUDE_BANKNIFTY, 
               INCLUDE_FINNIFTY,
               BNF_NIFTY_FUT_EXPIRY,
               FINNIFTY_FUT_EXPIRY,
               INCLUDE_ONE_SECOND_DELAY
               ):
    self.INCLUDE_NIFTY = INCLUDE_NIFTY
    self.INCLUDE_BANKNIFTY = INCLUDE_BANKNIFTY
    self.INCLUDE_FINNIFTY = INCLUDE_FINNIFTY

    self.INCLUDE_ONE_SECOND_DELAY = INCLUDE_ONE_SECOND_DELAY

    self.BNF_NIFTY_FUT_EXPIRY = BNF_NIFTY_FUT_EXPIRY
    self.FINNIFTY_FUT_EXPIRY = FINNIFTY_FUT_EXPIRY

    self.NF_BNF_OPT_EXPIRY_EPOCH_TIME = NF_BNF_OPT_EXPIRY_EPOCH_TIME
    self.FIN_OPT_EXPIRY_EPOCH_TIME = FIN_OPT_EXPIRY_EPOCH_TIME

    self.is_bnf_nifty_fut_date_valid = None
    self.is_finnifty_fut_date_valid = None
    self.is_bnf_nifty_opt_date_valid = None
    self.is_finnifty_opt_date_valid = None

    self.is_parallel_run = True if INCLUDE_NIFTY + INCLUDE_BANKNIFTY + INCLUDE_FINNIFTY > 1 else False

    self.creds = creds
    self.email = email
    self.pwd = pwd
    self.dob = dob
    
    try:
      self.client = FivePaisaClient(email = self.email, passwd = self.pwd, dob = self.dob, cred = self.creds)
      self.client.login()
      
      if self.client.login_response_message is not None or not self.client.is_logged_in:
        raise InvalidLoginException
      else:
        display(HTML("<h2 style='color: #00D100'>Logged In...!!</h2>"))

    except InvalidLoginException:
      if self.client.login_response_message is not None:
        display(HTML(f"<h2 style='color: #FF4500'>Error during Sign in : {self.client.login_response_message}</h2>"))
      else:
        display(HTML(f"<h2 style='color: #FF4500'>Error during Sign in : Invalid Credentials</h2>"))
      raise InvalidLoginException

    try:
      display(HTML("<h2 style='color: #FD7F20'>Checking Futures and Options Expiry date</h2>"))
      self.check_expiry_dates('NIFTY')
      self.check_expiry_dates('FINNIFTY')

      if (not self.is_bnf_nifty_fut_date_valid) or (not self.is_finnifty_fut_date_valid):
        raise InvalidFutureExpiryDateException
      else:
        display(HTML("<h2 style='color: #00D100'>Futures date Valid</h2>"))

      if (not self.is_bnf_nifty_opt_date_valid) or (not self.is_finnifty_opt_date_valid):
        raise InvalidOptionExpiryDateException
      else:
        display(HTML("<h2 style='color: #00D100'>Option Expiry date Valid</h2>"))

    except InvalidFutureExpiryDateException:
      if not self.is_bnf_nifty_fut_date_valid:
        display(HTML(f"<h2 style='color: #FF4500'>NIFTY/BANKNIFTY Futures Date Invalid</h2>"))
      if not self.is_finnifty_fut_date_valid:
        display(HTML(f"<h2 style='color: #FF4500'>FINNIFTY Futures Date Invalid</h2>"))
      raise InvalidFutureExpiryDateException

    except InvalidOptionExpiryDateException:
      if not self.is_bnf_nifty_opt_date_valid:
        display(HTML(f"<h2 style='color: #FF4500'>NIFTY/BANKNIFTY Option Expiry Date Invalid</h2>"))
      if not self.is_finnifty_opt_date_valid:
        display(HTML(f"<h2 style='color: #FF4500'>FINNIFTY Option Expiry Date Invalid</h2>"))
      raise InvalidOptionExpiryDateException

    except Exception as err:
      display(HTML(f"<h2 style='color: #FF4500'>Unable to fetch expiry dates : {err}</h2>"))
      raise FetchExpiryException

  def check_expiry_dates(self, index):
    expiry_dates = self.client.get_expiry('N', index)
    if expiry_dates is None:
      print(f'Error here check_futures_date()')
      raise TypeError
    else:
      expiry_dates = [int(x['ExpiryDate'][6:][:-7]) for x in expiry_dates['Expiry']]
      if (index == 'BANKNIFTY' or index == 'NIFTY'):
        exp = getEpochTime(self.BNF_NIFTY_FUT_EXPIRY, ' ')
        if exp in expiry_dates:
          self.is_bnf_nifty_fut_date_valid = True
        else:
          self.is_bnf_nifty_fut_date_valid = False

        if self.NF_BNF_OPT_EXPIRY_EPOCH_TIME in expiry_dates:
          self.is_bnf_nifty_opt_date_valid = True
        else:
          self.is_bnf_nifty_opt_date_valid = False

      elif index == 'FINNIFTY':
        exp = getEpochTime(self.FINNIFTY_FUT_EXPIRY, ' ')
        if exp in expiry_dates:
          self.is_finnifty_fut_date_valid = True
        else:
          self.is_finnifty_fut_date_valid = False

        if self.FIN_OPT_EXPIRY_EPOCH_TIME in expiry_dates:
          self.is_finnifty_opt_date_valid = True
        else:
          self.is_finnifty_opt_date_valid = False

  def getStrikes(self, index, spot):
    step = 11
    spot_diff = 1000 if index == 'BANKNIFTY' else 500
    rem = spot%100
    #refined_spot = None
    if index == 'BANKNIFTY': 
      spot = spot-rem if rem < 50 else spot+(100-rem)
    else:
      if rem <= 24:
        spot = spot-rem
      elif rem >= 25 and rem <= 74:
        if rem <= 50:
          spot = spot + (50 - rem)
        else:
          spot = spot - (rem - 50)
      elif rem >= 75:
        spot = spot+(100-rem)

    call_strikes = np.linspace(spot-spot_diff, spot, step)
    put_strikes = np.linspace(spot, spot+spot_diff, step)

    if index == 'BANKNIFTY':
      call_strikes = np.append(call_strikes, [call_strikes[-1]+100])
      put_strikes = np.insert(put_strikes, 0, put_strikes[0]-100)
    else:
      call_strikes = np.append(call_strikes, [call_strikes[-1]+50])
      put_strikes = np.insert(put_strikes, 0, put_strikes[0]-50)

    return spot, call_strikes, put_strikes   

  def getSpot(self, result, index):
    response = self.client.get_expiry('N', index)
    result.update({'SPOT' : response})

  def getFutures(self, result, index, expiry):
    fut_value_request_payload = [{
      "Exchange": "N",
      "ExchangeType": "D",
      "Symbol": index + ' ' + expiry
    }]
    response = self.client.fetch_market_depth_by_symbol(fut_value_request_payload)
    result.update({'FUTURES' : response})

  def get_option_chain(self, result, index, time_code):
    response = self.client.get_option_chain("N", index, time_code)
    result.update({'OPTION_CHAIN':response})

  def run(self, index, spot, futures, option_chain):
    try:
      if spot is not None:
        if len(spot['lastrate']) == 0:
          raise SpotFetchException
      else:
        raise SpotFetchException

      if futures is not None:
        if futures['Data'] is None:
          display(HTML(f"<h2 style='color: #FF4500'>Error Fetching {index} Futures Value</h2>"))
          raise FuturesFetchException
      else:
        raise FuturesFetchException

      if option_chain is not None:
        if len(option_chain['Options']) == 0:
          display(HTML(f"<h2 style='color: #FF4500'>Error Fetching {index} Option Chain</h2>"))
          raise OptionChainFetchException
      else:
        raise OptionChainFetchException
      
      spot_value = spot['lastrate'][0]['LTP']
      futures_value = futures['Data'][0]['LastTradedPrice']
      option_chain = option_chain['Options']

      refined_spot, call_strikes, put_strikes = self.getStrikes(index, spot_value)
      call_strike_ltp_map = {'Strikes':[], 'CE LTP':[]}
      put_strike_ltp_map = {'Strikes':[], 'PE LTP':[]}

      for oc in option_chain:
        if oc['CPType'] == 'CE' and oc['StrikeRate'] in call_strikes:
          call_strike_ltp_map['Strikes'].append(oc['StrikeRate'])
          call_strike_ltp_map['CE LTP'].append(oc['LastRate'])
        if oc['CPType'] == 'PE' and oc['StrikeRate'] in put_strikes:
          put_strike_ltp_map['Strikes'].append(oc['StrikeRate'])
          put_strike_ltp_map['PE LTP'].append(oc['LastRate'])

      call_df = pd.DataFrame(call_strike_ltp_map)
      call_df['CE IV'] = spot_value - call_df['Strikes']
      call_df['CE Premium'] = np.where(call_df['CE IV'] <= 0, call_df['CE LTP'], call_df['CE LTP']-call_df['CE IV'])
      call_df['CE Premium'] = np.where(call_df['CE LTP'] == 0, 0, call_df['CE Premium'])

      put_df = pd.DataFrame(put_strike_ltp_map)
      put_df['PE IV'] = put_df['Strikes'] - spot_value
      put_df['PE Premium'] = np.where(put_df['PE IV'] <= 0, put_df['PE LTP'], put_df['PE LTP']-put_df['PE IV'])
      put_df['PE Premium'] = np.where(put_df['PE LTP'] == 0, 0, put_df['PE Premium'])

      df = pd.merge(call_df, put_df, on='Strikes', how='outer')

      if df.shape[0] > 0 and df.shape[1] > 0: 
        call_premium = float(df.iloc[10][3])
        put_premium = float(df.iloc[10][-1])
      else:
        raise Exception

      if call_premium < put_premium:
        cheap_premium = 'CE'
        row = 4
      elif put_premium < call_premium:
        cheap_premium = 'PE'
        row = 5

      if index == 'NIFTY':
        class_name = 'nifty'
        color = 'red'
      elif index == 'BANKNIFTY':
        class_name = 'banknifty'
        color = 'yellow'
      else:
        class_name = 'finnifty'
        color = 'blue'

      premium_style = '{background-color:#32CD32;color: black;}'
      cheap_style = f""".{class_name} tr:nth-child({row}) td:nth-child(12){premium_style}"""

      max_value = max(call_premium, put_premium)
      min_value = min(call_premium, put_premium)
      percentage_diff = round(((max_value - min_value)/max_value)*100, 2)

      df['Discount'] = np.where(((df['CE LTP'] < df['CE IV']) | (df['PE LTP'] < df['PE IV'])) & (df['CE Premium'] != 0) & (df['PE Premium'] != 0), 'Discount', ' ')
      df['Discount'] = np.where(df['Strikes'] == refined_spot, str(round(abs(call_premium - put_premium),2)) + f'<br>({percentage_diff}%)', df['Discount'])

      df.fillna(' ', inplace=True)
      df = df[['Strikes','CE LTP', 'PE LTP', 'CE Premium', 'PE Premium', 'Discount']]
      
      return index, self.convert_df_to_html(index, spot_value, futures_value, percentage_diff, cheap_style, class_name, df)
    
    except (SpotFetchException, FuturesFetchException, OptionChainFetchException, Exception) as e:
      return index, None
  
  def fetch_values(self, index, fut_expiry, time_code, result):
    try:
      child_jobs = []
      spot_process = CustomMultiProcess(target=self.getSpot, args=(result, index))
      child_jobs.append(spot_process)

      fut_process = CustomMultiProcess(target=self.getFutures, args=(result, index, fut_expiry))
      child_jobs.append(fut_process)

      option_chain_process = CustomMultiProcess(target=self.get_option_chain, args=(result, index, time_code))
      child_jobs.append(option_chain_process)

      for j in child_jobs:
        j.start()

      for j in child_jobs:
        j.join()

      for j in child_jobs:
        j.kill()

    except KeyboardInterrupt:
      for j in child_jobs:
        j.kill()
      raise KeyboardInterrupt

  def fetchNifty(self):
    try:
      index = 'NIFTY'
      fut_expiry = self.BNF_NIFTY_FUT_EXPIRY
      time_code = self.NF_BNF_OPT_EXPIRY_EPOCH_TIME

      manager = multiprocessing.Manager()
      value_result = manager.dict()

      self.fetch_values(index, fut_expiry, time_code, value_result)

      spot = value_result['SPOT']
      futures = value_result['FUTURES']
      option_chain = value_result['OPTION_CHAIN']    

      index, option = self.run(index, spot, futures, option_chain)

      return 'NIFTY', option

    except Exception as e:
      return 'NIFTY', None

  def fetchBankNifty(self):
    try:
      index = 'BANKNIFTY'
      fut_expiry = self.BNF_NIFTY_FUT_EXPIRY
      time_code = self.NF_BNF_OPT_EXPIRY_EPOCH_TIME

      manager = multiprocessing.Manager()
      value_result = manager.dict()
      
      self.fetch_values(index, fut_expiry, time_code, value_result)

      spot = value_result['SPOT']
      futures = value_result['FUTURES']
      option_chain = value_result['OPTION_CHAIN']      
      index, option = self.run(index, spot, futures, option_chain)

      return 'BANKNIFTY', option

    except Exception as e:
      return 'BANKNIFTY', None

  def fetchFinNifty(self):
    try:
      index = 'FINNIFTY'
      fut_expiry = self.FINNIFTY_FUT_EXPIRY
      time_code =  self.FIN_OPT_EXPIRY_EPOCH_TIME

      manager = multiprocessing.Manager()
      value_result = manager.dict()
      
      self.fetch_values(index, fut_expiry, time_code, value_result)

      spot = value_result['SPOT']
      futures = value_result['FUTURES']
      option_chain = value_result['OPTION_CHAIN']      
      index, option = self.run(index, spot, futures, option_chain)

      return 'FINNIFTY', option

    except Exception as e:
      return 'FINNIFTY', None

  def smap_parallel(self, f, result):
    try:
      idx, opt = f()
      result.update({idx : opt})

    except Exception as e:
      raise OptionChainFetchException

  def smap(self, f):
    try:
      return f()

    except Exception as e:
      raise OptionChainFetchException

  def stream(self):
    functions = self.fetch_required_function()
    while True:
      if self.is_parallel_run:
        try:
          jobs = []
          manager = multiprocessing.Manager()
          result = manager.dict()
          
          for i in range(len(functions)):
            process = CustomMultiProcess(target=self.smap_parallel, args=(functions[i], result))
            jobs.append(process)

          for j in jobs:
            j.start()

          for j in jobs:
            j.join()
          
          for j in jobs:
            j.kill()

          self.index_stack(result)
          if self.INCLUDE_ONE_SECOND_DELAY:
            time.sleep(1)
          clear_output(wait=True)

        except KeyboardInterrupt:
          for j in jobs:
            j.kill()
          raise KeyboardInterrupt

      else:
        try:
          result = [self.smap(f) for f in functions]
          self.index_stack(result)
          if self.INCLUDE_ONE_SECOND_DELAY:
            time.sleep(1)
          clear_output(wait=True)

        except KeyboardInterrupt:
          raise KeyboardInterrupt

  def fetch_required_function(self):
    functions = []
    if self.INCLUDE_NIFTY:
      functions.append(self.fetchNifty)
    if self.INCLUDE_BANKNIFTY:
      functions.append(self.fetchBankNifty)
    if self.INCLUDE_FINNIFTY:
      functions.append(self.fetchFinNifty)

    return functions

  def convert_df_to_html(self, index, spot_value, fut_value, percentage_diff, cheap_style, class_name, *dfs):
    value_diff = round(fut_value - spot_value,2)
    html = f"""<style>{cheap_style}"""
    html += """
        tr{
          line-height:30px;
        }

        tbody tr th:nth-child(1){
          width:5000px;
        }

        table tr td:nth-child(12){
          background-color: #C5C5C5;
          color: black;
          text-align:center;
          font-weight:bold;
          font-size:16px;
        }

        table tr:nth-child(1){
          font-weight:bold;
        }

        table tr td:nth-child(0){text-align:center; font-size:16px;}
        table tr td:nth-child(1){text-align:center; font-size:16px;}
        table tr td:nth-child(2){text-align:center; font-size:16px;}
        table tr td:nth-child(3){text-align:center; font-size:16px;}
        table tr td:nth-child(4){text-align:center; font-size:16px;}
        table tr td:nth-child(5){text-align:center; font-size:16px;}
        table tr td:nth-child(6){text-align:center; font-size:16px;}
        table tr td:nth-child(7){text-align:center; font-size:16px;}
        table tr td:nth-child(8){text-align:center; font-size:16px;}
        table tr td:nth-child(9){text-align:center; font-size:16px;}
        table tr td:nth-child(10){text-align:center; font-size:16px;}
        table tr td:nth-child(11){text-align:center; font-size:16px;}
        table tr td:nth-child(13){text-align:center; font-size:16px;}
        table tr td:nth-child(14){text-align:center; font-size:16px;}
        table tr td:nth-child(15){text-align:center; font-size:16px;}
        table tr td:nth-child(16){text-align:center; font-size:16px;}
        table tr td:nth-child(17){text-align:center; font-size:16px;}
        table tr td:nth-child(18){text-align:center; font-size:16px;}
        table tr td:nth-child(19){text-align:center; font-size:16px;}
        table tr td:nth-child(20){text-align:center; font-size:16px;}
        table tr td:nth-child(21){text-align:center; font-size:16px;}
        table tr td:nth-child(22){text-align:center; font-size:16px;}

        .set{
          border-bottom: 5px double white;
          padding: 10px;
        }

        #discount {
          text-align: center;
          background-color: lightgreen;
          color: black;
          font-weight: bold;
          font-size: 12px;
        }

        caption{
          font-size: 14px;
          font-weight: bold;
          padding: 5px;
        }

        #dataframe{
          margin-top : 30px;
          width : 100%;
        }

        .atm{
          background-color: #C5C5C5; 
          color: black; 
          text-align: center;
        }

        .calls{
          background-color: #32CD32; 
          color: black; 
          text-align: center;
        }
        .puts{
          background-color: #FF5C5C; 
          color: black; 
          text-align: center;
        }
        content{
          margin-left:10px;
        }
      </style>
    """

    html += '<div style="padding-left:30px; padding-right:30px">'
    for df in dfs:
        html += df.T.to_html()
    html += '</div>'
    html = html.replace("""<table border="1" class="dataframe">""", f"""<table border="1" class="dataframe {class_name}" id="dataframe">""")
    html = html.replace("""<td>Discount</td>""",'<td id="discount">Discount</td>')
    html = html.replace("""<th>10</th>""",'<th class="atm">ATM</th>')
    html = html.replace("""<th>0</th>\n      <th>1</th>\n      <th>2</th>\n      <th>3</th>\n      <th>4</th>\n      <th>5</th>\n      <th>6</th>\n      <th>7</th>\n      <th>8</th>\n      <th>9</th>\n      """,'<th colspan=10 class="calls">Calls</th>')
    html = html.replace("""<th>11</th>\n      <th>12</th>\n      <th>13</th>\n      <th>14</th>\n      <th>15</th>\n      <th>16</th>\n      <th>17</th>\n      <th>18</th>\n      <th>19</th>\n      <th>20</th>\n    """,'<th colspan=10 class="puts">Puts</th>')
    html = html.replace(
        f"""<table border="1" class="dataframe {class_name}" id="dataframe">""", 
        f"""
        <table border="1" class="dataframe {class_name}" id="dataframe">
          <colgroup>
            <col style="width:6%">
          </colgroup>  
          <caption>{index} Spot : {spot_value}</caption>
          <caption>{index} Fut : {fut_value} <span style='color:{'#FF5C5C' if value_diff<0 else '#32CD32'}'>({value_diff})</span></caption>
        """)

    html = html.replace("&lt;br&gt;",  "<br>")
    return html

  def index_stack(self, dfs):
    html = '<div style="width: 100%;">'
    if isinstance(dfs, list):
      for idx, df in dfs:
        if df is not None:
          html += df
        else:
          html += f'<h3><i>Fetching {idx} Option data.....</i></h3>'
    else:
      for idx in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
        if idx in dfs:
          if dfs[idx] is not None:
            html += dfs[idx]
          else:
            html += f'<h3><i>Fetching {idx} Option data.....</i></h3>'
    html += '</div>'
    display(HTML(html))
