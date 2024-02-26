from Classes.technical import Technical
import MetaTrader5 as mt5
from time import sleep
from threading import Timer
import numpy as np


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
        pips = 40
        while len(MT5.get_positions(0)) != n:
            # SEND REQUEST 
            s, ticket = MT5.open_position(s, order, lotaje, pips)
            if ticket != 0:
                tickets.append(ticket)
    else:
        lotaje = round(lotaje * 2, 2)
        pips = 18
        while len(MT5.get_positions(0)) != n:
            # SEND REQUEST 
            s, ticket = MT5.open_position(s, order, lotaje, pips)
            if ticket != 0:
                tickets.append(ticket)
    return tickets, order, lotaje


# Close all positions
def CLOSE_ALL(df, MT5, lotaje):
    """"
        Close all positions, it is used if the program crashed and we need to close all of them
    """
    print("Closing all positions!")
    for i in range(df.shape[0]):
        ticket = df["ticket"].iloc[i]
        sym = df["symbol"].iloc[i]
        type_ord = df["type"].iloc[i]
        MT5.close_position(sym, ticket, type_ord, lotaje)
    # Close position


def SEND_REQUEST_CLOSE(s, tickets, order, MT5):
    df = MT5.get_positions(0)
    vol = df["volume"]
    print("**********Closing position************* ")
    for ticket in tickets:
        MT5.close_position(s, ticket, order, vol)
    # Close positions by CHOP Index


def TRAILLING_STOP(s, order, tickets, conn):    
    # Initialize variables
    df = conn.get_positions(0)     
    sl = df["sl"].iloc[0]
    tp = df["tp"].iloc[0]    
    volumen = df["volume"].iloc[0]
    # Helper Function to send request
    def modify(ticket, sl_, tp_):
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
            print(f'Order failed, retcode: {result.retcode}')
            boolean = False
        return boolean
    limit_flag = False
    points = mt5.symbol_info(s).point * 5          
    price_limit = tp - (points * 15) if order == 1 else tp + (points * 15)
    trend_condition = lambda price,order: price >= price_limit if order == 1 else price <= price_limit
    while not conn.get_positions(0).empty:
        current_price =  conn.data_range(s, "M1", 1)["close"].iloc[0]        
        if not limit_flag and trend_condition(current_price,order):            
            print("Positions inside the limit")
            limit_flag = True
            sleep(5)
        elif limit_flag:            
            if (order == 1 and current_price < price_limit) or (order == 0 and current_price > price_limit):
                print("Position will be closed")             
                for ticket in tickets:
                    conn.close_position(s, ticket, order, volumen, comment="Closed by Limit price")
    print("Positions Closed")


# Check for Crossing
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

def STRONG_TREND(df,sma=6,bars=30,threshold=.85):
    M1_technical = Technical(df)
    SMA_CLOSE = M1_technical.SMA(entry="close", period=sma)    
    above = len(np.where( SMA_CLOSE[-bars:] < df["close"].iloc[-bars:])[0])
    under = len(np.where( SMA_CLOSE[-bars:] > df["close"].iloc[-bars:])[0])    
    return (above / bars) > threshold or (under/ bars) > threshold
# Signals by Crossing EMAS
def EMA_CROSSING_ENTRIES(df, s,offset=3, sma_period=15, ema_period=3, factor=.5):
    """
        Check for crossing signals based on the parameters passed
    """
    operation = False
    trend_for_operation = 2
    M1_technical = Technical(df)
    ATR_LENGHT = 5 if s == "EURUSD" else 1
    # Set PARAMETERS         
    EMA_LOW = M1_technical.EMA(entry="low", period=ema_period, deviation=offset)
    EMA_HIGH = M1_technical.EMA(entry="high", period=ema_period, deviation=offset)
    EMA_OPEN = M1_technical.EMA(entry="open", period=sma_period, deviation=-1)
    supertrend = M1_technical.SUPER_TREND(ATR_LENGHT, factor)  
    # SELL Under
    if (CROSSING(EMA_OPEN, EMA_HIGH, 0)) and supertrend == 1:
        print("Sell under")
        operation = True
        trend_for_operation = 0
    # BUY Over
    elif (CROSSING(EMA_OPEN, EMA_LOW, 1)) and supertrend == 0:
        print("Buy over")
        operation = True
        trend_for_operation = 1
    return operation, trend_for_operation

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