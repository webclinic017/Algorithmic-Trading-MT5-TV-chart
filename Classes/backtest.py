from Classes.data_operations import *
from Classes.Strategies import *
import numpy as np
import concurrent.futures


DEFAULT_RANGE = lambda x:  range(100, 1200, 100) if x == "XAUUSD" else range(40, 100, 5)

# Test the startegy in tha past
def backtest_strategy(conn,n_periods,symbol,reverse,points,apply_volume_filter=False,candles_per_entry=10):
    """
        Backtest the strategy to detect entries in the past, the method will return a dictionary with the entry price and the operation type (BUY/SELL)
    """
    FINAL_EMA_OPEN = EMA_OPEN_XAUUSD if symbol == "XAUUSD" else EMA_OPEN_EURUSD
    FINAL_EMA_LH = EMA_LH_XAUUSD if symbol == "XAUUSD" else EMA_LH_EURUSD
    candles_lenght = n_periods * 4
    df_testing = conn.data_range(symbol,"M1",candles_lenght)
    df_testing[["Sell","Buy","SL","TP","SL1","TP1"]] = np.nan
    adjusted_points = points * mt5.symbol_info(symbol).point    
    operations = {}        
    open_prices = df_testing['open'].values
    # Emulate Live Trading 
    start = (n_periods * 3) - 1  
    index_to_continue = 0   
    trade_open = False
    for i in range(n_periods):        
        df_for_strategy = df_testing.iloc[start-100:start]                             
        
        # Simulate entries
        position, entry = EMA_CROSSING(df=df_for_strategy,offset= OFFSET, ema_open=FINAL_EMA_OPEN,ema_period= FINAL_EMA_LH,reverse=reverse,volume_filter=apply_volume_filter,show=False)                         
        if position and not trade_open:                                   
            index_to_continue = i + candles_per_entry
            trade_open = True                
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
            # Add SL and TP to the DF
            df_testing["SL"] = sl
            df_testing["TP"] = tp
            df_testing["SL1"] = sl1
            df_testing["TP1"] = tp1     
            # Strategy        
            df_for_strategy["SL"] = sl
            df_for_strategy["TP"] = tp
            df_for_strategy["SL1"] = sl1
            df_for_strategy["TP1"] = tp1             
            df_to_plot = df_testing.iloc[start:] 
            operations[open_prices[start]] = {
                "type": "SELL" if entry == 0 else "BUY",               
                "df": df_to_plot,
                "df_strategy": df_for_strategy,
                "reversed": reverse
                    }
            # Reset the values of the original dataframe to keep just one value per df
            df_testing[column] = np.nan  
            df_testing[["SL","TP"]] = np.nan              
        # When the loop iterate over candles_per_entry - 1 bars strategy will open new trades again
        elif i == index_to_continue - 1:
            trade_open = False
        start += 1
    return operations

# Analyze and modify entries to analyze later on
def analyze_results(backtest_dictionary,periods=100):
    """
        Analyze the entries to determine how profitable were the entries
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

# Helper fucntion to return only the win rate
def backtest_and_analyze(conn, n_periods, symbol, reverse, points, volume_filter):
    """
    Perform backtest and analyze results.
    Returns:
        The result metric (win rate) of the backtest.
    """
    backtest_results = backtest_strategy(conn, n_periods, symbol, reverse, points, volume_filter)
    counters, _ = analyze_results(backtest_results)
    if sum(counters.values()) > 0:
        win_rate = (counters["tp_counter"] + counters["tp1_counter"]) / sum(counters.values())
    else:
        win_rate = 0
    return win_rate

# Execute the method above to get the best parameters
def optimize_strategy(conn, n_periods, symbol):
    """
    Optimize the strategy by testing different points for SL and TP and evaluate both normal and reversed entries,
    with and without the volume filter.

    Args:
        conn: Database connection or data source.
        n_periods: Number of periods for backtesting.
        symbol: The trading symbol.

    Returns:
        A dictionary with the best SL and TP points, the best result, and whether reversing the entries and/or using
        the volume filter is better.
    """

    best_result = None
    best_points = None    
    points_range = DEFAULT_RANGE(symbol)
    results = []    
    for points in points_range:           
        win_rate = backtest_and_analyze(conn, n_periods, symbol, False, points, False)
        results.append((win_rate, points))
 
    for win_rate,points in results:
        if best_result is None or win_rate > best_result:
            best_result = win_rate
            best_points = points
    return {
        "best_points": best_points,
        "best_result": best_result,
        
    }