import datetime
import numpy as np
import pandas as pd
import talib
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import CustomFactor, Latest
from quantopian.pipeline.data.quandl import cboe_vix, cboe_vxv, cboe_vxd, cboe_vvix

class GetVIX(CustomFactor):
    window_length = 1
    def compute(self, today, assets, out, vix):
        out[:] = vix[-1]

    
def initialize(context):
       # Robinhood only allows long positions, use this trading
    # guard in case
    set_long_only()

    # Since we are trading with Robinhood we can set this to $0!
    set_commission(commission.PerTrade(cost=0))
    
    # Declaring XIV, UPRO, and VXX as the three ETFs to be used
    context.xiv = sid(40516)
    context.ziv = sid(40513)
    context.upro = sid(38533)
    context.vxx = sid(38054)
    
    set_benchmark(context.xiv)
    # set the current maximum value and drawdown
    context.max_val = context.portfolio.portfolio_value 
    context.drawdown = 0 

        
    pipe = Pipeline()
    attach_pipeline(pipe, 'my_pipeline')
    
    pipe.add(GetVIX(inputs=[cboe_vix.vix_close]), 'VixClose')
    pipe.add(GetVIX(inputs=[cboe_vxv.close]), 'VxvClose')
    pipe.add(GetVIX(inputs=[cboe_vxd.close]), 'VxdClose')
    pipe.add(GetVIX(inputs=[cboe_vvix.vvix]), 'VvixClose')

    # Scheduling the order function to occur everyday at open
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(hours = 0, minutes = 1))
    
    # For every minute available (max is 6 hours and 30 minutes)
    total_minutes = 6*60 + 30

    for i in range(1, total_minutes):
    # Every 30 minutes run schedule
        if i % 5 == 0:
            # This will start at 9:31AM and will run every 5 minutes
            schedule_function(log_stats, date_rules.every_day(), time_rules.market_open(minutes=i), True)

def before_trading_start(context,data):
    context.output = pipeline_output('my_pipeline')
    context.vix = context.output["VixClose"].iloc[0]
    context.vxv = context.output["VxvClose"].iloc[0]
    context.vxd = context.output["VxdClose"].iloc[0]
    context.vvix = context.output["VvixClose"].iloc[0]

def adjust_portfolio(context, SID):
    order_target_percent(context.upro,0)
    #order_target_percent(context.vxx,0)
    order_target_percent(context.xiv,0)
    order_target_percent(context.ziv,0)
    if SID =="XIV":
        order_target_percent(context.xiv,0.70)
        order_target_percent(context.ziv,0.20)
    elif SID == "VXX":
        order_target_percent(context.vxx,0)
    elif SID == "UPRO":
        order_target_percent(context.upro, 0)
    
def my_rebalance(context, data):

    # Calculate max value
    if context.max_val < context.portfolio.portfolio_value:
        context.max_val = context.portfolio.portfolio_value
    
    # Calculate drawdown
    last_drawdown = context.portfolio.portfolio_value/context.max_val - 1 ;
    if last_drawdown < context.drawdown:
        context.drawdown = last_drawdown
    

    # Calculating the contango ratio of the front and second month VIX Futures 
    last_ratio_v1_v2 = context.vix/context.vxv
    print(last_ratio_v1_v2)

    
    threshold_xiv= 0.95
    threshold_vxx = 1.08
    
    #buy xiv if contango is high
    if last_ratio_v1_v2 < threshold_xiv:
        if context.xiv not in context.portfolio.positions:
            # If we are not holding XIV then sell everything in portfolio then move to XIV
            adjust_portfolio(context,"XIV")
    #if backwardation is high, sell everything
    elif last_ratio_v1_v2 > threshold_vxx:
        if context.vxx not in context.portfolio.positions:
            adjust_portfolio(context,"VXX")
    #if neither contango nor backwardation, sell everything
    else:
        if context.upro not in context.portfolio.positions:
            # If we are not holding UPRO then sell everything in portfolio then move to UPRO
            adjust_portfolio(context,"UPRO")

    
    current_price = context.vix 
    
    too_much_vol_threshold = 35
    upper_threshold_vix = 20
    lower_threshold_vix = 12
    # buy xiv if vix > 20 --> expecting that vix will reverse to mean
    if (current_price > upper_threshold_vix) and (current_price < too_much_vol_threshold):
        if context.xiv not in context.portfolio.positions:
            adjust_portfolio(context,"XIV")
    # if vol too high, sell everything
    if (current_price > too_much_vol_threshold):
            adjust_portfolio(context,"VXX")
            
            
    # buy vxx if vix < 12 --> expecting that vix will reverse to mean
    #elif (current_price < lower_threshold_vix):
    #    if context.vxx not in context.portfolio.positions:   
    #        adjust_portfolio(context,"VXX")
           
                    
    record(drawdown=context.drawdown)
    record(ratio=last_ratio_v1_v2)
    record(VIX=context.vix)
    record(value=context.portfolio.portfolio_value)
    
def log_stats(context, data):
    # Calculate max value
    if context.max_val < context.portfolio.portfolio_value:
        context.max_val = context.portfolio.portfolio_value
    
    # Calculate drawdown
    last_drawdown = context.portfolio.portfolio_value/context.max_val - 1 ;
    if last_drawdown < context.drawdown:
        context.drawdown = last_drawdown
    
    last_ratio_v1_v2 = context.vix/context.vxv
    print(last_ratio_v1_v2)
    
    record(drawdown=context.drawdown)
    record(ratio=last_ratio_v1_v2)
    record(VIX=context.vix)
    record(value=context.portfolio.portfolio_value)
