# 📊 Sell Strategy System - Complete Analysis

## 🎯 Overview
Bot menggunakan **Advanced Sell Strategy System** yang otomatis mengelola penjualan setelah buy order berhasil dieksekusi. Sistem ini memiliki 4 mekanisme utama: **Take Profit**, **Partial Take Profit**, **Trailing Stop Loss**, dan **Stop Loss**.

## ⚙️ Default Configuration
```
PROFIT_TARGET_PERCENTAGE = 20%      # Target profit untuk Take Profit
TP_SELL_PERCENTAGE = 100%           # Persentase yang dijual saat TP tercapai
STOP_LOSS_PERCENTAGE = 10%          # Stop loss di bawah harga beli
TRAILING_STOP_PERCENTAGE = 5%       # Trailing stop persentase
TSL_MIN_ACTIVATION_PERCENTAGE = 20% # Minimum kenaikan untuk aktifkan TSL
```

## 🔄 Cara Kerja Step-by-Step

### 1. **Trigger Awal (Setelah Buy Order)**
```
Ketika buy order FILLED:
├── Order Executor mendeteksi order completed
├── Ambil data: symbol, buy_price, executed_quantity
├── SellStrategyManager.add_strategy() dipanggil
└── Mulai monitoring harga real-time
```

### 2. **Calculation Setup**
```python
# Contoh: Buy 100 PULSE @ 0.09 USDT
buy_price = 0.09
quantity = 1111.11 PULSE (100 USDT / 0.09)

# Hitung target harga
take_profit_price = 0.09 * (1 + 20/100) = 0.108 USDT    # +20%
stop_loss_price = 0.09 * (1 - 10/100) = 0.081 USDT      # -10%
tsl_activation_price = 0.09 * (1 + 20/100) = 0.108 USDT # Sama dengan TP
```

### 3. **Real-time Price Monitoring**
```
Setiap 1 detik:
├── Ambil current_price dari MEXC API
├── Update highest_price tracking
├── Cek kondisi sell berdasarkan prioritas:
│   ├── 1. STOP LOSS (prioritas tertinggi)
│   ├── 2. TRAILING STOP (jika aktif)
│   ├── 3. TAKE PROFIT
│   └── 4. TIME BASED (jika ada)
└── Execute sell jika kondisi terpenuhi
```

## 🎯 Sell Mechanisms Detail

### **1. Take Profit (TP) - Partial/Full**
```
Trigger: current_price >= take_profit_price
Action: Jual sesuai TP_SELL_PERCENTAGE

Contoh dengan TP_SELL_PERCENTAGE = 50%:
- Harga beli: 0.09 USDT
- Target TP: 0.108 USDT (+20%)
- Quantity awal: 1111.11 PULSE
- Saat harga = 0.108: Jual 555.55 PULSE (50%)
- Sisa posisi: 555.56 PULSE (50%)
- Status: PARTIAL_EXECUTED
- Monitoring berlanjut untuk sisa posisi
```

### **2. Trailing Stop Loss (TSL)**
```
Aktivasi: current_price >= tsl_activation_price (default +20%)
Cara kerja:
├── Harga naik → TSL ikut naik
├── Harga turun → TSL tetap
└── Trigger: current_price <= trailing_stop_price

Contoh:
- Buy: 0.09 USDT
- TSL Activation: 0.108 USDT (+20%)
- TSL Percentage: 5%

Timeline:
├── Price = 0.108 → TSL activated at 0.1026 (0.108 - 5%)
├── Price = 0.12 → TSL updated to 0.114 (0.12 - 5%)
├── Price = 0.15 → TSL updated to 0.1425 (0.15 - 5%)
└── Price drops to 0.1425 → SELL triggered
```

### **3. Stop Loss (SL)**
```
Trigger: current_price <= stop_loss_price
Action: Jual SEMUA posisi (100%)
Priority: TERTINGGI (override TSL dan TP)

Contoh:
- Buy: 0.09 USDT
- Stop Loss: 0.081 USDT (-10%)
- Jika harga turun ke 0.081 → Jual semua posisi
```

### **4. Time-based Sell**
```
Trigger: Waktu tertentu setelah buy
Default: Biasanya disabled (TIME_BASED_SELL_MINUTES = 0)
Action: Jual semua posisi setelah waktu expired
```

## 📈 Quantity Management

### **Full Position Tracking**
```python
strategy = {
    'original_quantity': 1111.11,    # Quantity awal
    'quantity': 1111.11,             # Quantity yang masih ada
    'tp_executed': False,            # Status TP sudah dieksekusi?
    'tsl_activated': False,          # Status TSL sudah aktif?
    'status': 'ACTIVE'               # ACTIVE/PARTIAL_EXECUTED/EXECUTED
}
```

### **Partial Sell Logic**
```
Saat TP dengan TP_SELL_PERCENTAGE = 50%:
├── Calculate sell_qty = quantity * (50/100) = 555.55
├── Execute sell order untuk 555.55 PULSE
├── Update quantity = 1111.11 - 555.55 = 555.56
├── Set tp_executed = True
├── Set status = 'PARTIAL_EXECUTED'
└── Continue monitoring untuk sisa 555.56 PULSE
```

## 🔄 Progress Monitoring

### **Strategy Status**
- **ACTIVE**: Monitoring aktif, belum ada eksekusi
- **PARTIAL_EXECUTED**: Sudah partial sell (TP), masih monitoring sisa
- **EXECUTED**: Sudah sell semua, monitoring stop

### **Price Tracking**
```python
{
    'highest_price': 0.09,          # Track harga tertinggi
    'trailing_stop_price': None,    # Harga TSL (jika aktif)
    'tsl_activated': False,         # Status TSL
    'tp_executed': False            # Status TP
}
```

## 📊 Example Scenario

### **Complete Trading Cycle**
```
1. BUY ORDER:
   ├── Buy 100 USDT worth of PULSE @ 0.09
   ├── Quantity: 1111.11 PULSE
   └── Strategy activated

2. PRICE MOVEMENTS:
   ├── 0.09 → 0.105 (monitoring, update highest_price)
   ├── 0.105 → 0.108 (TP triggered!)
   │   ├── Sell 50% = 555.55 PULSE @ 0.108
   │   ├── Profit: 555.55 * (0.108-0.09) = ~10 USDT
   │   ├── Remaining: 555.56 PULSE
   │   └── TSL activated (price >= 0.108)
   ├── 0.108 → 0.120 (TSL update to 0.114)
   ├── 0.120 → 0.150 (TSL update to 0.1425)
   └── 0.150 → 0.142 (TSL triggered!)
       ├── Sell remaining 555.56 PULSE @ 0.142
       ├── Profit: 555.56 * (0.142-0.09) = ~29 USDT
       └── Total profit: ~39 USDT dari 100 USDT

3. FINAL RESULT:
   ├── Total invested: 100 USDT
   ├── Total received: ~139 USDT
   ├── Total profit: ~39 USDT (39%)
   └── Strategy: EXECUTED
```

## 🛠️ Configuration Commands

```bash
# Lihat konfigurasi saat ini
/config list

# Set Take Profit ke 30%
/config set PROFIT_TARGET_PERCENTAGE 30

# Set Partial TP ke 70% (jual 70% saat TP)
/config set TP_SELL_PERCENTAGE 70

# Set Stop Loss ke 15%
/config set STOP_LOSS_PERCENTAGE 15

# Set Trailing Stop ke 8%
/config set TRAILING_STOP_PERCENTAGE 8

# Set TSL Activation ke 25%
/config set TSL_MIN_ACTIVATION_PERCENTAGE 25
```

## 🎯 Key Features

### **Smart Profit Taking**
- **Partial TP**: Ambil profit sebagian, biarkan sisa "ride the wave"
- **TSL Protection**: Lindungi profit yang sudah terbentuk
- **Adaptive**: Menyesuaikan dengan kondisi market

### **Risk Management**
- **Stop Loss**: Batasi kerugian maksimal
- **Real-time Monitoring**: Respon cepat terhadap perubahan harga
- **Multiple Exit Points**: Tidak bergantung pada satu strategi saja

### **Automated Operation**
- **Zero Manual Intervention**: Semua otomatis setelah buy
- **24/7 Monitoring**: Bekerja terus menerus
- **Callback System**: Notifikasi real-time saat sell terjadi

---

## 🎉 Summary

**Sell Strategy System** adalah mesin otomatis yang mengelola penjualan dengan cerdas:

1. ✅ **Otomatis aktif** setelah setiap buy order
2. ✅ **Multi-layered protection** (TP, TSL, SL)
3. ✅ **Partial profit taking** untuk optimasi return
4. ✅ **Real-time monitoring** dengan response cepat
5. ✅ **Configurable parameters** sesuai risk appetite
6. ✅ **Smart quantity management** untuk partial sells

Sistem ini memungkinkan trading yang profitable sambil meminimalkan risiko melalui automation yang sophisticated! 🚀
