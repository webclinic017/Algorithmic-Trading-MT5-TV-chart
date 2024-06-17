import customtkinter
from Classes.components import *
from Classes.MT5 import MT5
from Classes.Strategies import main_loop
from Classes.backtest import optimize_strategy
import threading
import requests
import tkinter as tk
from tkinter import messagebox

customtkinter.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("assets/themes/red.json")
#customtkinter.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"
from dotenv import load_dotenv
from os import environ
load_dotenv()

class App(customtkinter.CTk):
    admin = "Moises"
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("ATLAS")
        self.geometry(f"{680}x{600}")

        # Configure grid layout (2x2)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        # Display Side Bar in the App
        side_bar(self)        
        set_up_main_frame(self)           
        help_screen(self)
        self.sidebar_button_2.configure(state="disabled")    
        self.authentication = False   
        self.stop_thread_flag = threading.Event()
        # Connect the closing event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        # This function will be called when the user tries to close the window    
        if not self.stop_thread_flag.is_set() and "active_connection" in globals():
            self.stop_session()
        # Destroy the window
        self.destroy()
   
        
    # API Request
    def validate_active_license(self):
        # Simulate response from API    
        # url = 'http://127.0.0.1:8000/api/'
        # try:
        #     response = requests.get(url)
        #     if response.status_code == 200:
        #         data = response.json()         
        #     else:
        #         tk.messagebox.showerror("Error", "Failed to retrieve data")
        # except requests.exceptions.RequestException as e:
        #     tk.messagebox.showerror("Error", f"Request failed: {e}")
           
        # if self.main_frame.user_input.get() == self.admin and self.main_frame.password.get() == "1234":
        #     self.main_frame.grid_forget()
        print("Login Sucess")
        connection_mt5_screen(self)
        self.authentication = True
        # else:
        #     print("Auntenthication failed")           
    
    # Stop Startegy thread
    def stop_session(self): 
        if positions_open(self.connection):
            self.close_postions_flag.set()
            tk.messagebox.showinfo("Information","Active trades will be closed before end the session!")
            sleep(2)                                       
        self.stop_thread_flag.set()
        try:
            self.main_frame.profit_or_loss.grid_forget()
            self.main_frame.stop_thread.grid_forget()    
            self.main_frame.close_trades.grid_forget()  
            # Return button
            self.sidebar_button_2.configure(state="enabled")
            self.main_frame.stop_thread = customtkinter.CTkButton(self.main_frame, text="Return Strategy Screen",command= self.start_connection)
            self.main_frame.stop_thread.grid(row=7, column=0,columnspan=2, padx=40, pady=0,sticky="ew")            
        except:
            pass
    # Close trades manually
    def close_entry(self):
        if positions_open(self.connection,self.symbol):
            self.close_postions_flag.set()
        else:
            tk.messagebox.showinfo("Information","There's no active trades :(")
    # Show/Hide button
    def display_buttons(self):
        self.main_frame.grid_columnconfigure((0, 1), weight=1, uniform="column")                 
        # Position Open
        if positions_open(self.connection,self.symbol):
            self.main_frame.close_position = customtkinter.CTkButton(self.main_frame, text="Close Position",command= self.start_connection)
            self.main_frame.close_position.grid(row=4, column=1,pady=10)                 
    # Screen Triggers
    def sidebar_button_login_event(self):
        self.sidebar_button_1.configure(state="disabled")
        set_up_main_frame(self)        
        self.main_frame.grid_forget()     
        if not self.authentication:   
            login_for_license_screen(self) 
        else:
            connection_mt5_screen(self)
        self.sidebar_button_2.configure(state="enabled")       

    def back_main_screen_event(self):
        self.main_frame.grid_forget()
        self.sidebar_button_1.configure(state="enabled")
        help_screen(self)
        self.sidebar_button_2.configure(state="disabled")
        
    def sidebar_button_event(self):
        self.sidebar_button_2.configure(state="disabled")
        help_screen(self)
        self.sidebar_button_1.configure(state="enabled")
        
    # MT5 Triggers
    def start_connection(self):
        if "active_connection" in globals():
            start_strategy_mt5_screen(self)
            # fine_tunning_strategy(self)
        else:
            # Uncomment once you deploy
            # self.user_mt5 = int(self.main_frame.account_number.get())
            # self.password_mt5 = self.main_frame.password_mt5.get()
            # self.server_mt5 = self.main_frame.server.get()
            self.user_mt5 = int(environ.get("USER_DEMO"))
            self.password_mt5 = environ.get("PASSWORD_DEMO")
            self.server_mt5 = environ.get("SERVER_DEMO")
            try:
                self.connection = MT5(user=self.user_mt5,password=self.password_mt5,server=self.server_mt5)
                if self.connection.connection_state: 
                    global active_connection
                    active_connection = True      
                    start_strategy_mt5_screen(self)
                    # fine_tunning_strategy(self)                
                    
            except Exception as e:
                # Display screen error with a message
                set_up_main_frame(self)
                error_screen(self,
                            title="Connection Failed",
                            message_1="Please verify next things before trying to connect again:",
                            message_2=f"-Make sure you have installed MT5 in your computer.\n-Valid credentials from a MT5 account.\n-Internet connection.\n-If your problem persist please contact us for assistance.\n{e}",
                            command_to_trigger=self.back_main_screen_event)
    
    def start_optimization(self):
        self.main_frame.start_strategy.grid_forget()
        self.main_frame.symbols_options.configure(state="disabled")
        # Show the progress bar        
        self.main_frame.progress_bar = customtkinter.CTkProgressBar(self.main_frame)
        self.main_frame.progress_bar.configure(mode="indeterminate")
        self.main_frame.progress_bar.grid(row=3, column=0, columnspan=2, padx=(20, 20), pady=(10, 10), sticky="ew")
        self.main_frame.progress_bar.set(0)
        self.main_frame.progress_bar.start()
        # Run the optimization in a separate thread            
        self.optimization_thread = threading.Thread(target=self.optimize_and_update).start()
        

    def optimize_and_update(self):
        self.symbol = self.main_frame.symbols_options.get()
        self.bestparameters = optimize_strategy(self.connection, 100, self.symbol)
        self.points = round(int(self.bestparameters["best_points"]), 2)
        self.reverse = self.bestparameters["reverse"]        
        # Stop the progress bar and hide it
        self.main_frame.progress_bar.stop()
        self.main_frame.progress_bar.grid_forget()    
        # Call the next screen function
        # start_strategy_mt5_screen(self)
        
    def start_strategy(self):                
        self.symbol = self.main_frame.symbols_options.get()
        self.risk = float(self.main_frame.risk_entry.get())
        self.profit = float(self.main_frame.gain_entry.get())
        self.max_trades = int(self.main_frame.max_trades_entry.get())
        self.partial_close = self.main_frame.partial_close_options.get() == "Enable"
        self.dynamic_sl = self.main_frame.dynamic_SL_menu.get() == "Enable"
        self.reverse = False #self.main_frame.reverse_menu.get() == "Enable"
        # self.reverse = self.bestparameters["reverse"]
        self.positions_entry = int(self.main_frame.positions_entry.get())    
        self.points = round(int(self.main_frame.points_entry.get()),2)
        # self.points = round(int(self.bestparameters["best_points"]),2)            
        self.lots = float(self.main_frame.lots_entry.get())  
        self.fibonacci = self.main_frame.fibonacci_options.get() == "Enable"
        if self.stop_thread_flag.is_set():
            self.stop_thread_flag.clear()
        self.close_postions_flag = threading.Event()
        # Create new thread with the strategy        
        self.strategy_thread = threading.Thread(target=main_loop,
                                                args=(self,
                                                      self.connection,
                                                      self.symbol,
                                                      self.partial_close,
                                                      self.risk,self.profit,
                                                      self.positions_entry,
                                                      self.max_trades,
                                                      "M1",
                                                      self.stop_thread_flag,
                                                      self.close_postions_flag,
                                                      self.points,
                                                      self.lots,
                                                      True,
                                                      self.dynamic_sl,
                                                      self.reverse,
                                                      self.fibonacci                                                    
                                                      ))             
        
        strategy_running_screen(self)                
            
       
    

if __name__ == "__main__":
    app = App()    
    app.mainloop()