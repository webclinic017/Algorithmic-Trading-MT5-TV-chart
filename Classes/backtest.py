from Classes.data_operations import *
from Classes.model_operations import *
from Classes.Strategies import *
import numpy as np
import matplotlib.pyplot as plt

def backtest_strategy(conn,n_periods,symbol,reverse,points):
    """
        Backtest the strategy to detect entries in the past, the method will return a dictionary with the entry price and the operation type (BUY/SELL)
    """
    FINAL_EMA_OPEN = EMA_OPEN_XAUUSD if symbol == "XAUUSD" else EMA_OPEN_EURUSD
    FINAL_EMA_LH = EMA_LH_XAUUSD if symbol == "XAUUSD" else EMA_LH_EURUSD
    candles_lenght = n_periods * 2
    df_testing = conn.data_range(symbol,"M1",candles_lenght)
    df_testing[["Sell","Buy","SL","TP","SL1","TP1"]] = np.nan
    adjusted_points = points * mt5.symbol_info(symbol).point    
    operations = {}        
    open_prices = df_testing['open'].values
    close_prices = df_testing['close'].values
    low_prices = df_testing['low'].values
    high_prices = df_testing['high'].values
    decimal_places = len(str(open_prices[0]).split(".")[-1])

    # Emulate Live Trading 
    start = (n_periods - 1) 
    for i in range(n_periods):        
        df_for_strategy = df_testing.iloc[i:start]                         
        # Simulate entries
        position, entry = EMA_CROSSING(df=df_for_strategy,offset= OFFSET, ema_open=FINAL_EMA_OPEN,ema_period= FINAL_EMA_LH,reverse=reverse,show=False)                         
        if position:                       
            # Update the value where signal is generated 
            if entry == 0:
                column = "Sell"
            else:
                column = "Buy"
            # Entry price
            prices = df_testing[column].values  
            prices[start] = open_prices[start]
            df_testing[column] = prices
            # SL and TP
            sl = df_testing["SL"].values              
            tp  = df_testing["TP"].values         
            sl1 = df_testing["SL1"].values              
            tp1  = df_testing["TP1"].values      
            sl = open_prices[start] - adjusted_points if entry == 1 else open_prices[start] + adjusted_points
            tp = open_prices[start] + adjusted_points if entry == 1 else open_prices[start] - adjusted_points
            sl1 = open_prices[start] - adjusted_points/3 if entry == 1 else open_prices[start] + adjusted_points/3
            tp1 = open_prices[start] + adjusted_points/3 if entry == 1 else open_prices[start] - adjusted_points/3
            df_testing["SL"] = sl
            df_testing["TP"] = tp
            df_testing["SL1"] = sl1
            df_testing["TP1"] = tp1             
            df_to_plot = df_testing.iloc[start:] 
            operations[open_prices[start]] = {
                "type": "SELL" if entry == 0 else "BUY",               
                "df": df_to_plot,
                "df_strategy": df_for_strategy
                    }
            # Reset the values of the original dataframe to keep just one value per df
            df_testing[column] = np.nan  
            df_testing[["SL","TP"]] = np.nan  
        start += 1
    return operations

def analyze_results(backtest_dictionary,periods=100):
    """
        Analyze the entries to determine if the entries should be reversed or not
    """
    counters = {
        "sl1_counter": 0,
        "sl_counter": 0,
        "tp1_counter": 0,
        "tp_counter":0
    }         
    trades = {}
    for key in backtest_dictionary.keys():
        df = backtest_dictionary[key]["df"]           
        sl1_flag = False
        sl_flag = False
        tp1_flag = False
        tp_flag = False
        for index, row in df.reset_index().iterrows():                    
            sl = row["SL"]
            sl1 = row["SL1"]
            tp = row["TP"]
            tp1 = row["TP1"]
            # Check SL
            if backtest_dictionary[key]["type"] == "SELL":
                # Check if the price touch the SL
                if row["high"] >= sl1 and row["high"] <= sl and not sl1_flag:
                    counters["sl1_counter"] = counters["sl1_counter"] + 1
                    sl1_flag = True
                    trades[key] = {"result": "LOSS", "df":df[['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']].iloc[index:index+periods]}                                   
                elif row["high"] >= sl and not sl_flag:
                    counters["sl_counter"] = counters["sl_counter"] + 1
                    sl_flag = True
                    trades[key] = {"result": "LOSS", "df":df[['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']].iloc[index:index+periods]}                                   
                # Check if the price touch the TP
                elif row["low"] <= tp1 and row["low"] >= tp and not tp1_flag:
                    counters["tp1_counter"] = counters["tp1_counter"] + 1
                    tp1_flag = True
                    trades[key] = {"result": "WIN", "df":df[['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']].iloc[index:index+periods]}                                   
                elif row["low"] <= tp and not tp_flag:
                    counters["tp_counter"] = counters["tp_counter"] + 1
                    tp_flag = True
                    trades[key] = {"result": "WIN", "df":df[['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']].iloc[index:index+periods]}                                   
            else:
                # Check if the price touch the SL
                if row["low"] <= sl1 and row["low"] >= sl and not sl1_flag:
                    counters["sl1_counter"] = counters["sl1_counter"] + 1
                    sl1_flag = True
                    trades[key] = {"result": "LOSS", "df":df[['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']].iloc[index:index+periods]}                                   
                elif row["low"] <= sl and not sl_flag:
                    counters["sl_counter"] = counters["sl_counter"] + 1
                    sl_flag = True
                    trades[key] = {"result": "LOSS", "df":df[['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']].iloc[index:index+periods]}                                   
                # Check if the price touch the TP
                elif row["high"] >= tp1 and row["high"] <= tp and not tp1_flag:
                    counters["tp1_counter"] = counters["tp1_counter"] + 1
                    tp1_flag = True
                    trades[key] = {"result": "WIN", "df":df[['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']].iloc[index:index+periods]}                                   
                elif row["low"] >= tp and not tp_flag:
                    counters["tp_counter"] = counters["tp_counter"] + 1
                    tp_flag = True
                    trades[key] = {"result": "WIN", "df":df[['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']].iloc[index:index+periods]}                                               
    return counters,trades   