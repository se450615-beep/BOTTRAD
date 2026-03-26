import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import time

# --- الإعدادات (SMC Pure Setup) ---
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
LOTS = 0.01  # لوت ثابت كما طلبت
RR_RATIO = 2.0

def get_smc_data(n=300):
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, n)
    if rates is None: return None
    df = pd.DataFrame(rates)
    
    # 1. EMA 200 (الفلتر الرئيسي)
    df['ema200'] = ta.ema(df['close'], length=200)
    
    # 2. Ultimate RSI Logic (LuxAlgo Sim)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    # 3. SMC Logic: Order Blocks & Displacement
    # نحوسو على شمعة قوية (Institutional Candle) مع فوليوم عالي
    df['body_size'] = abs(df['close'] - df['open'])
    df['avg_body'] = df['body_size'].rolling(20).mean()
    
    # شرط الـ Bullish OB: شمعة هابطة يتبعها انفجار سعري (Displacement)
    df['bullish_ob'] = (df['close'].shift(1) < df['open'].shift(1)) & \
                       (df['close'] > df['open']) & \
                       (df['body_size'] > df['avg_body'] * 1.5)
    
    # شرط الـ Bearish OB: شمعة صاعدة يتبعها انفجار هابط
    df['bearish_ob'] = (df['close'].shift(1) > df['open'].shift(1)) & \
                        (df['close'] < df['open']) & \
                        (df['body_size'] > df['avg_body'] * 1.5)
    
    return df

def open_smc_trade(action, sl_points):
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None: return
    
    price = tick.ask if action == "BUY" else tick.bid
    sl = price - sl_points if action == "BUY" else price + sl_points
    tp = price + (sl_points * RR_RATIO) if action == "BUY" else price - (sl_points * RR_RATIO)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOTS,
        "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": round(sl, 3),
        "tp": round(tp, 3),
        "magic": 2026,
        "comment": "SMC BIGBELUGA LOGIC",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    res = mt5.order_send(request)
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"🎯 تم تنفيذ صفقة {action} (SMC Strategy)")
        print(f"📊 السعر: {price} | الستوب: {sl} | الهدف: {tp}")
    else:
        print(f"❌ فشل التنفيذ: {res.comment}")

def run_bot():
    if not mt5.initialize():
        print("❌ MT5 Error")
        return
    
    print("🚀 سكريبت الـ SMC المطور شغال... (التحليل جاري)")

    while True:
        df = get_smc_data()
        if df is not None:
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # --- منطق الدخول الذكي ---
            
            # 1. حالة الشراء (BUY):
            # السعر فوق EMA200 + RSI في حالة تشبع بيعي (تحت 45) + ظهور Bullish OB
            if last['close'] > last['ema200'] and last['rsi'] < 45:
                if last['bullish_ob']:
                    # الستوب لوس يكون تحت ذيل شمعة الـ OB بـ 20 نقطة
                    sl_dist = abs(last['close'] - last['low']) + 0.50 # 50 cent buffer for Gold
                    open_smc_trade("BUY", sl_dist)
                    time.sleep(3600) # بلوك لمدة ساعة باش ما يفتحش صفقات متكررة

            # 2. حالة البيع (SELL):
            # السعر تحت EMA200 + RSI في حالة تشبع شرائي (فوق 55) + ظهور Bearish OB
            elif last['close'] < last['ema200'] and last['rsi'] > 55:
                if last['bearish_ob']:
                    sl_dist = abs(last['high'] - last['close']) + 0.50
                    open_smc_trade("SELL", sl_dist)
                    time.sleep(3600)

        time.sleep(60) # فحص كل دقيقة

if __name__ == "__main__":
    run_bot()