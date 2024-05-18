from Classes.technical import Technical
import MetaTrader5 as mt5
from time import sleep,time
import numpy as np
from collections import Counter
from random import choice
# Function to analyze and return the total points and trend
def TREND_DIRECTION(df_M1, index=0):
    """
        Determine in which direction should open a trend
    """
    # Create the objects to analyze
    M1_technical = Technical(df_M1.iloc[index:])

    # BUY COUNTER
    BUY = 1 if M1_technical.TREND_BY_TRENDLINE() == 1 else 0
    BUY += 1 if M1_technical.TREND_BY_BARS_DIRECTION() == 1 else 0
    BUY += 1 if M1_technical.PREVIOUS_BAR() == 1 else 0

    # SELL COUNTER
    SELL = 1 if M1_technical.TREND_BY_TRENDLINE() == 0 else 0
    SELL += 1 if M1_technical.TREND_BY_BARS_DIRECTION() == 0 else 0
    SELL += 1 if M1_technical.PREVIOUS_BAR() == 0 else 0

    if SELL or BUY >= 3:
        if SELL > BUY:
            return 0
        else:
            return 1
    return None

# Send the request to execute the order based on point values
def SEND_REQUEST_OPEN(s, order, lotaje=0.5, MT5=0, n=5):
    """"
        Send request to open postion with the proper size
    """
    
    tickets = []
    print("****************** BUY ******************") if order == 1 else print(
        "****************** SELL ******************")
    if s == "XAUUSD":
        lotaje = round(lotaje * 1.5, 2)
        points = 40
        while len(MT5.get_positions(0)) < n:
            # SEND REQUEST 
            s, ticket = MT5.open_position(s, order, lotaje, points)
            if ticket != 0:
                tickets.append(ticket)
    else:
        lotaje = round(lotaje * 2, 2)
        points = 65
        while len(MT5.get_positions(0)) < n:
            # SEND REQUEST 
            ticket = MT5.open_position(s, order, lotaje, points)
            if ticket != 0:
                tickets.append(ticket)
    return tickets, order, lotaje

# Close all positions
def CLOSE_ALL(df, MT5):
    """"
        Close all positions, it is used if the program crashed and we need to close all of them
    """
    if df.shape[0] == 0:
        print("No open trades")
    else:
        print("Closing all positions!")
        for i in range(df.shape[0]):
            ticket = df["ticket"].iloc[i]
            sym = df["symbol"].iloc[i]
            type_ord = df["type"].iloc[i]
            volume = df["volume"].iloc[i]
            MT5.close_position(sym, ticket, type_ord, volume)

# Adjust the SL every time the price moves certain points 
def TRAILLING_STOP(s,order,tickets,conn, points,profit,risk,pnl,apply_both_directions=False,flag_to_stop=False,limit=2,partial_close=False,second_trailling=False,dynamic_sl=True):
    """
        Adjust the SL every time the prices moves n points
    """
    # Internal use
    def modify(ticket, sl_, tp_,show=False):
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(ticket),
            "sl": sl_,
            "tp": tp_
        }
        boolean = False
        result = mt5.order_send(request)
        try:
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                # print(f'New {comment}: {sl_ if comment == "SL" else tp_}')
                boolean = True
            else:
                if show:
                    print(f'Order failed, retcode: {result.retcode}')
                boolean = False
        except Exception as e:
            pass
        return boolean    
    point = mt5.symbol_info(s).point  
    symbol_points = (points * point)
    df = conn.get_positions(0,s=s)
    if df.shape[0] > 0:    
        volume = df["volume"].iloc[0]       
        tp = df["tp"].iloc[0]       
        decimal_places = len(str(tp).split(".")[1])
        price_open = df["price_open"].iloc[0]                     
    counter = 0    
    counter_sl = 0
    tickets_pop = []    
    while not flag_to_stop.is_set() and df.shape[0] > 0:
        current_price =  conn.data_range(s, "M1", 1)["close"].iloc[0]      
        current_pl = conn.account_details().profit + pnl
        sl = df["sl"].iloc[0]   
        difference = (current_price - price_open) if order == 1 else (price_open - current_price)        
        if apply_both_directions:
            difference = abs(difference)
        # Every 3 min randomly choose if update or not in case the difference is not positive 
        elif counter_sl == 180:           
            difference = choice([difference,abs(difference)])
            counter_sl = 0
        # Move the SL by n points        
        if symbol_points < difference and counter < limit:
            new_sl = round(current_price - symbol_points,decimal_places) if order == 1 else round(current_price + symbol_points,decimal_places)
            price_open = price_open + symbol_points if order == 1 else price_open - symbol_points
            counter += 1
            try:
                # Close partial trades when positions are greater than 1 otherwise update SL
                if len(tickets) > 1 and (price_open < current_price if order == 1 else price_open > current_price) and partial_close:
                    ticket_to_pop = tickets.pop()
                    conn.close_position(s, ticket_to_pop, order, volume, comment="Partial Close")                
                    tickets_pop.append(ticket_to_pop)
                    print("Partial Close")
                if dynamic_sl:
                    # Always update in the trend direction
                    if (order == 1 and new_sl > sl) or (order == 0 and new_sl < sl):                                            
                        # Update SL
                        for ticket in tickets:
                            modify(ticket,new_sl,tp)                
            except Exception as e:
                pass       
        # Check if the risk/profit is reached in active order close trades and close session
        if current_pl >= profit or current_pl <= risk:
            flag_to_stop.set()
        # Update Trailling Stop with half of current porints in both directions
        if counter >= limit and not second_trailling:                  
            print("SECOND TRAILLING STOP")
            TRAILLING_STOP(s,order,tickets,conn, points / 2,profit=profit,risk=risk,pnl=pnl,apply_both_directions=True,limit=len(tickets),flag_to_stop=flag_to_stop,second_trailling=True)
        counter_sl += 1
        if conn.get_positions(0,s).empty:
            print("Position Closed")
            break
        sleep(1)    
                      
# Monitor the entries to close if needed    
def POSITIONS_MONITORING(s, order, tickets, conn,points,percentage_distance):    
    """
        Monitor the open trade to close the position if needed.
        When the price reach a distance to the TP but start moving in opposite side the positions will be closed to prevent loss and keep profit        
    """
     # Internal use
    def modify(ticket, sl_, tp_,show=False):
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(ticket),
            "sl": sl_,
            "tp": tp_
        }
        boolean = False
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            # print(f'New {comment}: {sl_ if comment == "SL" else tp_}')
            boolean = True
        else:
            if show:
                print(f'Order failed, retcode: {result.retcode}')
            boolean = False
        return boolean
    
    # Initialize variables
    df = conn.get_positions(0,s=s)         
    tp = df["tp"].iloc[0]  
    volume = df["volume"].iloc[0]
    decimal_places = len(str(tp).split(".")[1])      
    price_open = df["price_open"].iloc[0]   
    limit_flag = False
    point = mt5.symbol_info(s).point          
    points = points * point 
    price_limit = price_open + (points * percentage_distance) if order == 1 else tp + (points * percentage_distance)
    trend_condition = lambda price,order: price >= price_limit if order == 1 else price <= price_limit    
    while not conn.get_positions(0,s=s).empty:       
        current_price =  conn.data_range(s, "M1", 1)["close"].iloc[0]         
        if not limit_flag and trend_condition(current_price,order):            
            print("Positions inside the zone SL will be adjusted")
            limit_flag = True
            new_sl = round(current_price - (points * (percentage_distance * .25)),decimal_places) if order == 1 else round(current_price + (points * (percentage_distance * .25)),decimal_places)
            for ticket in tickets:
                request_done = False
                while not request_done and not conn.get_positions(0,s=s).empty:                                
                    request_done = modify(ticket,new_sl,tp,True)
            print("SL Asjusted")                    
        sleep(1)        

# Check for Crossing betewen the 2 MA provided
def CROSSING(first_series, second_series, crossing):
    """"
        Check for crossing in the series passed where the type stands for over/under
        1 -> Crossover
        0 -> Cross under
        The first series is used as reference to look for the cross
    """
    # Crossover
    if crossing == 1:
        bool_values = np.greater(first_series[-1], second_series[-1])
        prev_bool_values = np.less_equal(first_series[-2], second_series[-2])
        crossing_values = np.logical_and(bool_values, prev_bool_values)
    # Cross under
    else:
        bool_values = np.less(first_series[-1], second_series[-1])
        prev_bool_values = np.greater_equal(first_series[-2], second_series[-2])
        crossing_values = np.logical_and(bool_values, prev_bool_values)
    return crossing_values

# Count ocurrencies in the passed series 
def bar_trend_ocurrencies(series):
    counts = Counter(series)
    counters = {}
    for value, count in counts.items():
        counters[value] = count
    return counters
    
def STRONG_TREND(df,sma=6,bars=30,threshold=.85):
    M1_technical = Technical(df)
    SMA_CLOSE = M1_technical.SMA(entry="close", period=sma)    
    above = len(np.where( SMA_CLOSE[-bars:] < df["close"].iloc[-bars:])[0])
    under = len(np.where( SMA_CLOSE[-bars:] > df["close"].iloc[-bars:])[0])    
    return (above / bars) > threshold or (under/ bars) > threshold

def parameters(s):
    if s == "EURUSD":
        EMA_LENGHT = 3
        SMA_LENGHT = 6
        CHOP_LENGHT = 8
        OFFSET = 3
        CHOP_LIMIT = 100
        FACTOR = .5
    else:
        EMA_LENGHT = 3
        SMA_LENGHT = 6
        CHOP_LENGHT = 8
        OFFSET = 2
        CHOP_LIMIT = 50
        FACTOR = .5
    return CHOP_LENGHT, CHOP_LIMIT, SMA_LENGHT, EMA_LENGHT, OFFSET, FACTOR