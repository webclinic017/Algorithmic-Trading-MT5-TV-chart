import keyboard
import pandas as pd
from Classes.MT5 import MT5
from Classes.data_operations import *
from dotenv import load_dotenv
from os import environ
load_dotenv()

# Broker info
user = int(environ.get("USER_DEMO"))
password = environ.get("PASSWORD_DEMO")
server = environ.get("SERVER_DEMO")

# INITIALIZE CONNECTION & PARAMETERS
conn = MT5(user, password, server)
balance = conn.account()
MAX_LOSS = (balance * .005) * -1
MIN_GAIN = (balance * .005)
current_symbol = "EURUSD"
value =  0.01 if balance < 1000 else round((balance / 10_000 ) * .10,2)
lotaje = value
total_positions = 0
profit = 0
profit_last_position = 0
tickets = 0
negative = 0
positive = 0
total_limit = 6
limit_positive = 3
limit_negative = 2
result = 0
minutes = 60
type_ord = 2
n = 2

EMA_LENGHT = 10
SMA_LENGHT = 5
while total_positions <= total_limit:                    
    if keyboard.is_pressed("q"):
        break
    if not conn.get_positions(0).empty:
        TRAILLING_STOP(current_symbol, type_ord, tickets,conn)
        for ticket in tickets:
            try:
                deals = conn.get_deals(ticket, 0)
                commission = abs(deals["commission"].iloc[1]*2)
                profit += (deals["profit"].iloc[1] - commission)
                profit_last_position = (deals["profit"].iloc[1] - (deals["commission"].iloc[1]*2))
            except Exception as e:
                print(e)
        if profit_last_position <= 0:
            negative += 1            
        elif profit_last_position > 0:
            positive += 1
        profit_last_position = 0
    if profit >= MIN_GAIN or profit <= MAX_LOSS:
        print("The session was closed automatically!")
        break
    if positive == limit_positive or negative == limit_negative or negative + positive == limit_positive:
        print("Limit reached")
        break
    try:
        M1 = conn.data_range(current_symbol, "M1", 100)
    except Exception as e:
        print("Data range failed:", e)
        break
    M1_technical = Technical(M1)
    position, entry = EMA_CROSSING_ENTRIES(M1, current_symbol, SMA_LENGHT, EMA_LENGHT)        
    if position:            
        lotaje = value            
        tickets, type_ord, lotaje = SEND_REQUEST_OPEN(current_symbol, entry, lotaje, conn, n)
        total_positions += 1            
    sleep(1 / 2)
conn.close()
print("Positions opened in the session: ", total_positions)
print("Profit from the session: ", profit)