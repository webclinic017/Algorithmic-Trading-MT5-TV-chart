from Classes.data_operations import *
from Classes.Strategies import *
import numpy as np
from Classes.randomForest import *

DEFAULT_RANGE = lambda x:  range(100, 1200, 100) if x == "XAUUSD" else range(40, 100, 5)

def backtest_strategy(conn,n_periods,symbol,reverse,points,apply_volume_filter=False,candles_per_entry=10,fibonacci=False,model=False):
    """
        Backtest the strategy to detect entries in the past, the method will return a dictionary with the entry price and the operation type (BUY/SELL)
    """
    FINAL_EMA_OPEN = EMA_OPEN_XAUUSD if symbol == "XAUUSD" else EMA_OPEN_EURUSD
    FINAL_EMA_LH = EMA_LH_XAUUSD if symbol == "XAUUSD" else EMA_LH_EURUSD
    candles_lenght = n_periods * 4
    df_testing = conn.data_range(symbol,"M1",candles_lenght)
    df_testing[["Sell","Buy","SL","TP","SL1","TP1"]] = np.nan
    adjusted_points = points * mt5.symbol_info(symbol).point   
    final_points = points 
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
        # Use the moedel to check entries reversed
        if model:
            data = inputs_for_random_forest(df_for_strategy,entry,symbol,final_points)  
            prediction =  get_prediction(data)
            if prediction:
                entry = 0 if entry == 1 else 1        
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
        if fibonacci:
            lowest,highest = Technical(df_for_strategy).LOWEST_AND_HIGHEST(10) 
            decimal_places = len(str(lowest).split(".")[1])
            difference = abs(highest - lowest)
            fibonacci_levels = {
                38.2: .382 * difference,
                50: .5 * difference,
                61.8: .618 * difference
            }                                
            if entry == 1:                                                        
                sl = prices[start] - fibonacci_levels[38.2]
                tp1 = prices[start] + fibonacci_levels[50]
                tp = prices[start] + fibonacci_levels[61.8] 
                final_points = tp - prices[start]                                     
            else:                    
                sl = prices[start] + fibonacci_levels[38.2]
                tp1 = prices[start] - fibonacci_levels[50]
                tp = prices[start] - fibonacci_levels[61.8]
                final_points = prices[start] - tp
            final_points = round(final_points * (100 if symbol == "XAUUSD" else 100_000 ),decimal_places)
        else:
            sl = df_testing["SL"].values              
            tp  = df_testing["TP"].values         
            sl1 = df_testing["SL1"].values              
            tp1  = df_testing["TP1"].values      
            sl = open_prices[start] - adjusted_points if entry == 1 else open_prices[start] + adjusted_points
            tp = open_prices[start] + adjusted_points if entry == 1 else open_prices[start] - adjusted_points
            sl1 = open_prices[start] - adjusted_points/3 if entry == 1 else open_prices[start] + adjusted_points/3
            tp1 = open_prices[start] + adjusted_points/3 if entry == 1 else open_prices[start] - adjusted_points/3
            # Add the SL1 to the DF to plot it
            df_testing["SL1"] = sl1    
            df_for_strategy["SL1"] = sl1     
        if position and not trade_open:                                   
            index_to_continue = i + candles_per_entry
            trade_open = True                
                                    
            # Add SL and TP to the DF
            df_testing["SL"] = sl
            df_testing["TP"] = tp            
            df_testing["TP1"] = tp1     
            # Strategy        
            df_for_strategy["SL"] = sl
            df_for_strategy["TP"] = tp            
            df_for_strategy["TP1"] = tp1             
            df_to_plot = df_testing.iloc[start:] 
            operations[open_prices[start]] = {
                "type": "SELL" if entry == 0 else "BUY",               
                "df": df_to_plot,
                "df_strategy": df_for_strategy,
                "reversed": prediction if model else reverse,
                "points": int(final_points)
                    }
            # Reset the values of the original dataframe to keep just one value per df
            df_testing[column] = np.nan  
            df_testing[["SL","TP"]] = np.nan              
        # When the loop iterate over candles_per_entry - 1 bars strategy will open new trades again
        elif i == index_to_continue - 1:
            trade_open = False
        start += 1
    return operations,final_points

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
        sl1_appears = True
        for index, row in df.reset_index().iterrows():  
            # Add SL1 if apply
            if "SL1" in df.columns.to_list():
                sl1 = row["SL1"]    
                sl1_appears = False
            sl = row["SL"]            
            tp = row["TP"]
            tp1 = row["TP1"]            
            # Check SL
            if backtest_dictionary[key]["type"] == "SELL":
                # Check if the price touch the SL
                if sl1_appears and row["high"] >= sl1 and row["high"] <= sl and not sl1_flag:
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
                if sl1_appears and row["low"] <= sl1 and row["low"] >= sl and not sl1_flag:
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
def backtest_and_analyze(conn, n_periods, symbol, reverse, points, volume_filter,fibonnaci,random_forest):
    """
    Perform backtest and analyze results.
    Returns:
        The result metric (win rate) of the backtest.
    """
    final_points = points
    backtest_results,points_fibonacci = backtest_strategy(conn, n_periods, symbol, reverse, points, volume_filter,fibonacci=fibonnaci,model=random_forest)
    counters, _ = analyze_results(backtest_results)
    if sum(counters.values()) > 0:
        win_rate = (counters["tp_counter"] + counters["tp1_counter"]) / sum(counters.values())
    else:
        win_rate = 0
    if fibonnaci:
        final_points = points_fibonacci
    return win_rate, final_points

# Execute the method above to get the best parameters
def optimize_strategy(conn, n_periods, symbol):
    """
    Optimize the strategy by testing different points for SL and TP or by automatic Points using Fibonacci levels

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
    fibonnaci_is_best = False
    random_is_best = False
    for points in points_range:  
        # Original Strategy    
        win_rate,_ = backtest_and_analyze(conn, n_periods, symbol, reverse=False, points=points, volume_filter=False,fibonnaci=False, random_forest=False)
        results.append((win_rate, points,False,False))
        # Strategy with random forest
        win_rate,_ = backtest_and_analyze(conn, n_periods, symbol, reverse=False, points=points, volume_filter=False,fibonnaci=False, random_forest=True)
        results.append((win_rate, points,False,True))                                          
                
    # Add results using fibonacci levels
    win_rate, fibonnaci = backtest_and_analyze(conn, n_periods, symbol, reverse=False, points=points, volume_filter=False,fibonnaci=True, random_forest=False)
    results.append((win_rate,fibonnaci,True,False))
    # Add results using fibonacci levels and random forest
    win_rate, fibonnaci2 = backtest_and_analyze(conn, n_periods, symbol, reverse=False, points=points, volume_filter=False,fibonnaci=True, random_forest=False)
    results.append((win_rate,fibonnaci2,True,True))
    
    # Check best results
    for win_rate,points,fibonnaci_implemented,randomForest in results:
        if best_result is None or win_rate > best_result:
            best_result = win_rate
            best_points = points
            fibonnaci_is_best = fibonnaci_implemented
            random_is_best = randomForest
    return {
        "best_points": best_points,
        "best_result": best_result,
        "fibonnaci_used": fibonnaci_is_best,
        "randomForest": random_is_best
    }