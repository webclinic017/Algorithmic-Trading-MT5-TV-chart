import pickle
import pandas as pd

# Load the model 
with open("Classes/Models/random_forest_95_model-2024-06-14.pkl", 'rb') as file:
    loaded_model = pickle.load(file)

def inputs_for_random_forest(df,order,symbol,points):
    """
        Add the features to the DataFrame and converts to a numpy array to use as input for the model
    """
    symbols_encoding = {"XAUUSD": 1, "EURUSD": 0}
    new_df = df.reset_index()
    # Add features to the DataFrame
    new_df["signal"] = order
    new_df["symbol"] = symbols_encoding[symbol]
    new_df["points"] = points
    columns = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread','real_volume', 'points', 'symbol', "signal"]    
    # Convert time to seconds   
    new_df["time"] = new_df["time"].apply(lambda x: (pd.to_datetime(x).hour * 60) + pd.to_datetime(x).minute)    
    return new_df[columns].to_numpy()

def get_prediction(input_model):    
    """
        use the pre loaded model to predict the entry
    """            
    return loaded_model.predict(input_model.reshape(1,-1))[0]