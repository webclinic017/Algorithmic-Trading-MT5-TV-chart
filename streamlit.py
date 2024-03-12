from Classes.MT5 import MT5
import streamlit as st

# Account values
user = 3000047410
password = "21K77czadi"
server = "demoUK-mt5.darwinex.com"
# Initialize Connection
st.button("Connect", type="primary")
if st.button('Say hello'):
    conn = MT5(user, password, server)