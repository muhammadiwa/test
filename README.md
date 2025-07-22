# Sniper Bot - Ultra-Fast Token Listing Bot

## 🧠 **Tujuan Utama**
Mengembangkan bot sniper ultra-cepat yang secara otomatis mendeteksi listing token baru di MEXC, lalu mengeksekusi pembelian di harga paling bawah dan menjual sesuai target profit \\— dengan toleransi waktu super rendah (1ms – 50ms).

---

## 📦 **Deskripsi Singkat Aplikasi**
Sniper Bot adalah aplikasi terotomatisasi yang terhubung ke MEXC (melalui API WebSocket/REST atau integrasi tidak resmi bila perlu), yang mendeteksi event listing token baru dan melakukan:

- Spam transaksi beli segera setelah market pair aktif atau dari 30 detik sebelum aktif supaya tidak tertinggal.
- Mengatur take profit dan/atau trailing stop.
- Opsi auto-sell saat harga turun drastis (stop loss).

---

## 🔧 **Fitur Utama (Modular)**

### 1. **Buy Order Engine (Sniper Engine)**
- Spam buy order sebelum dan saat token listing aktif (jika belum ada harga maka lihat dari orderbook sell yang aktif dan ketebalannya untuk patokan harga belinya).
- Adjustable frequency: 1ms – 100ms.
- Multi-threading / async untuk efisiensi.
- Retry logic & fallback.

### 2. **Order Executor & Manager**
- Full kontrol order: Market.
- Auto-retry order gagal sampai filled.

### 3. **Sell Strategy Manager**
- Take Profit dengan % target (contoh: +20%).
- Stop Loss dengan % batas bawah (contoh: -10%).
- Trailing Take Profit (contoh: naik 30%, turun 5%, auto-sell).
- Time-based selling (sell after X minutes).

### 4. **Logging & Monitoring Dashboard**
- Menampilkan performa per token (Buy price, Sell price, P&L).
- Auto-notify via Telegram.
- Semua pengaturan bisa di setting di bot telegram dan start bot-nya dari Telegram.

---

## 🛠️ **Teknologi yang Direkomendasikan**

### **Bahasa Pemrograman**
- Python (karena ekosistemnya yang kaya untuk API, async, dan multi-threading).

### **Library Utama**
- **WebSocket**: `websockets` atau `websocket-client`.
- **HTTP Client**: `httpx` (untuk performa async).
- **Multi-threading/Async**: `asyncio`, `concurrent.futures`.
- **Telegram Bot**: `python-telegram-bot`.
- **Logging**: `loguru`.

### **Database**
- SQLite atau Redis (untuk menyimpan konfigurasi dan log transaksi).

---

## 📂 **Struktur Proyek**
```
tradebot/
├── core/                # Logika inti (Sniper Engine, Order Executor, Sell Strategy Manager)
├── api/                 # Integrasi API MEXC (WebSocket/REST)
├── utils/               # Fungsi pendukung (logging, konfigurasi, retry logic)
├── dashboard/           # Monitoring dan logging (web/CLI)
├── telegram/            # Modul untuk integrasi Telegram bot
├── main.py              # Entry point aplikasi
└── requirements.txt     # Dependensi proyek
```

---

## 🚀 **Langkah Awal Pengembangan**

### **1. Setup Proyek**
1. Buat struktur direktori seperti di atas.
2. Tambahkan file `requirements.txt` untuk dependensi:
   ```plaintext
   websockets
   httpx
   python-telegram-bot
   loguru
   asyncio
   ```

### **2. Modul Sniper Engine**
- **Fungsi Utama**:
  - Spam buy untuk pairs yang dari hasil input contoh PUMPUSDT maka akan spam buy pair ini dengan nominal berapa usdt yang akan di tradingkan.
  - Spam buy order dengan adjustable frequency.
  - Retry logic untuk order yang gagal.

### **3. Modul Order Executor**
- **Fungsi Utama**:
  - Eksekusi order (market order).
  - Auto-retry hingga order terisi penuh.

### **4. Modul Sell Strategy Manager**
- **Fungsi Utama**:
  - Mengatur strategi take profit, stop loss, dan trailing stop.
  - Time-based selling.

### **5. Logging & Monitoring**
- **Fungsi Utama**:
  - Menampilkan performa transaksi.
  - Mengirim notifikasi ke Telegram.

---

## 📈 **Langkah Selanjutnya**
1. **Implementasi Modul API MEXC**:
   - Buat koneksi WebSocket untuk mendeteksi listing token baru.
   - Implementasikan REST API untuk eksekusi order.
2. **Pengembangan Sniper Engine**:
   - Buat loop async untuk spam buy order.
   - Tambahkan retry logic.
3. **Integrasi Telegram Bot**:
   - Buat command untuk memulai/menyetel bot.
   - Kirim notifikasi transaksi ke Telegram.
4. **Testing & Optimasi**:
   - Uji performa bot dengan simulasi listing token.
   - Optimalkan latensi (target 1ms – 50ms).
