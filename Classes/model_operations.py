import numpy as np
import talib as ta
from Classes.technical import Technical
import joblib

thresholds_price_open_both = {
    "std": 0.038705405917811235,
    "var": 0.0014981084472625369,
}

thresholds_price_open_BUY = {
    "std": 0.03875943579380298,
    "var": 0.0015022938630539356,
}

thresholds_price_open_SELL = {
    "std": 0.03865120229905197,
    "var": 0.0014939154391622404,
}


# Define a dictionary with the encoder of the symbol
encoder = {    
    "XAUUSD": 1,
    "EURUSD": 2,
    "NZDUSD": 3,
    "AUDUSD": 4,
    "EURGBP": 5,
    "GBPUSD": 6,
    "EURJPY": 7
}

# Calculate the mean of the ADX and RSI
def calculate_mean(df):
    array = np.array(df[["open","high","low","close"]]).T
    # Insert ADX and RSI Value
    adx = ta.ADX(array[1],array[2],array[3],5)[-1]
    rsi = ta.RSI(array[3],5)[-1]
    bars = np.mean([adx,rsi])
    
    return bars
# Calculate the distance beetween the EMA HIGH and LOW
def distance_emas(df,s,period=9):
    M1 = Technical(df)
    ema_high = M1.EMA("high",period,-1)
    ema_low = M1.EMA("low",period,-1)
    if encoder[s] == "XAUUSD":
        res = (ema_high-ema_low)*5
    else:
        res = (ema_high-ema_low)*10000
    return res
# Insert Data into the csv file
def send_data(df,tickets,data,conn):
    """
        This method retrieve the data from the operation and insert it to a Excel file to analyze later
    """
    tech = Technical(data)
    for ticket in tickets:
        try:
            if ticket != 0:            
                # Get a DataFrame with data from the trade
                a = conn.get_deals(ticket,0)
                # Get last 15 bars when the operation was opened
                data_model = data
                # Prepare data to insert in DatFrame
                time = np.array([a["time"].iloc[0],a["time"].iloc[1]])
                id = a["position_id"].iloc[0]
                type = "SELL" if a["type"].iloc[0] == 1 else "BUY"
                volume = a["volume"].iloc[0]
                price = np.array([a["price"].iloc[0],a["price"].iloc[1]])
                profit = a["profit"].iloc[1]
                symbol = a["symbol"].iloc[0]
                comment = a["comment"].iloc[1]                
                # Insert ADX and RSI Value
                bars = calculate_mean(data_model)                                
                # EMA
                EMA_LOW = tech.EMA(entry="low",period=3,deviation=-3)[-2:].values
                EMA_HIGH = tech.EMA(entry="high",period=3,deviation=-3)[-2:].values                       
                EMA_CLOSE = tech.EMA(entry="open",period=15,deviation=-1)[-2:].values                       
                # Insert the bars
                canddles = np.array(data_model[["open","high","low","close"]]).T                 
                # Insert new row
                df.loc[len(df)+1] = [time,id,type,volume,price,profit,symbol,comment,bars,EMA_LOW,EMA_HIGH,EMA_CLOSE,canddles]    
        except Exception as e:
                print(e)            
    return df
# Method to clean the main code and select the version of the classifier models
def load_model(version):
    if version == 1:        
        classifier = joblib.load("tree_classifier.joblib")
    elif version == 2:
        classifier = joblib.load("tree_classifier.joblib")
    elif version == 4:
        classifier = joblib.load(r"csv/models/KNN.joblib")
    return classifier
# Return prediction fro each model depending the version
def predict_model(version,df,trend,s,model):
    # First model
    if version == 1:    
        mean = calculate_mean(df)
        parameters = np.array([trend,mean]).reshape(1,-1)           
        res = model.predict(parameters)[0] 
    # Second model
    elif version == 2:        
        mean = calculate_mean(df)
        emas = distance_emas(df,s)
        parameters = np.array([trend,mean,emas,encoder[s]]).reshape(1,-1)                          
        res = model.predict(parameters)[0]   
    # Third Model
    elif version == 3:                               
        mean = calculate_mean(df)
        emas = distance_emas(df,s,3)
        M1 = Technical(df)
        ema_close = M1.EMA("close",20)
        parameters = np.array([trend,mean,emas,ema_close,encoder[s]]).reshape(1,-1)                          
        res = model.predict(parameters)[0]   
    elif version == 4:
        tech = Technical(df)
        # Use KNN as classifier
        price_open = df["open"].iloc[-1]
        # EMA
        EMA_LOW = tech.EMA(entry="low", period=3, deviation=-3).iloc[-1]
        EMA_HIGH = tech.EMA(entry="high", period=3, deviation=-3).iloc[-1]
        EMA_OPEN = tech.EMA(entry="open", period=6, deviation=-1).iloc[-1]
        parameters = np.array([trend,EMA_HIGH,EMA_LOW,EMA_OPEN,price_open]).reshape(1,-1)
        res = model.predict(parameters)[0]           
    return res

def validate_metrics(model_prediction, df, trend):
    points = 0
    # Verify that minimun are beetween the thresholds
    std = df["open"].std()
    var = df["open"].var()
    # Open position
    if model_prediction == 1:        
        # Buy
        if trend == 1:                     
            points += 1 if  max(thresholds_price_open_both["std"],thresholds_price_open_BUY["std"]) >= std <= min(thresholds_price_open_both["std"],thresholds_price_open_BUY["std"])               else 0
            points += 1 if  max(thresholds_price_open_both["var"],thresholds_price_open_BUY["var"]) >= var <= min(thresholds_price_open_both["var"],thresholds_price_open_BUY["var"]) else 0
        # Sell
        else:
            points += 1 if  max(thresholds_price_open_both["std"],thresholds_price_open_SELL["std"]) >= std <= min(thresholds_price_open_both["std"],thresholds_price_open_SELL["std"])               else 0
            points += 1 if  max(thresholds_price_open_both["var"],thresholds_price_open_SELL["var"]) >= var <= min(thresholds_price_open_both["var"],thresholds_price_open_SELL["var"]) else 0
    return points == 2 