# Panduan untuk Pengguna Bot di Indonesia

Karena API MEXC tidak dapat diakses dari Indonesia, kami telah menyediakan solusi VPN terintegrasi dalam setup Docker agar bot dapat berfungsi dengan baik.

## Cara Menggunakan VPN Otomatis

1. Pastikan `USE_VPN=true` dalam file `.env` Anda.

2. Bot akan secara otomatis:
   - Terhubung ke server VPN Singapore gratis dari VPN Gate
   - Merutekan semua koneksi API melalui VPN
   - Memastikan konektivitas ke API MEXC

## Memeriksa Status VPN

Untuk memeriksa apakah VPN berfungsi, jalankan script berikut:

```bash
bash vpn-status.sh
```

Output akan menunjukkan:

- Status antarmuka VPN (tun0)
- Alamat IP publik saat ini (seharusnya menunjukkan IP Singapura)
- Log VPN terkini
- Hasil test koneksi ke MEXC

## Menggunakan Layanan VPN Sendiri

Jika Anda memiliki langganan VPN premium:

1. Ekspor file konfigurasi OpenVPN (.ovpn) dari penyedia VPN Anda
2. Letakkan file konfigurasi tersebut di folder `./vpn` dengan nama `custom.ovpn`
3. Restart bot dengan perintah:

   ```bash
   docker-compose restart tradebot
   ```

## Troubleshooting

### VPN Tidak Terhubung

Jika bot tidak berhasil terhubung ke VPN:

1. Cek log dengan perintah:

   ```bash
   docker-compose logs -f
   ```

2. Pastikan container memiliki izin yang diperlukan:
   - `NET_ADMIN` dan `SYS_ADMIN` diaktifkan di docker-compose.yml

3. Coba gunakan file konfigurasi VPN alternatif:
   - Kunjungi [VPN Gate](https://www.vpngate.net/en/)
   - Download file .ovpn dari server Singapore yang berbeda
   - Letakkan file tersebut sebagai `./vpn/custom.ovpn`

4. Restart container:

   ```bash
   docker-compose restart tradebot
   ```

### Koneksi VPN Terputus

Jika koneksi VPN terputus saat bot berjalan:

1. Bot akan tetap mencoba mengirim permintaan API, tapi kemungkinan akan gagal
2. Lihat log untuk mengetahui masalah:

   ```bash
   docker-compose logs -f
   ```

3. Restart container untuk mencoba menghubungkan kembali ke VPN:

   ```bash
   docker-compose restart tradebot
   ```

## Alternatif Lain

Jika VPN tidak berfungsi untuk Anda, pertimbangkan opsi berikut:

1. **Menjalankan Bot di VPS Luar Negeri**:
   - Sewa VPS di Singapura, Jepang, atau negara lain dengan akses ke MEXC API
   - Deploy bot ke VPS tersebut menggunakan instruksi di [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

2. **Menggunakan Layanan Proxy HTTP**:
   - Konfigurasi proxy HTTP dalam file konfigurasi bot (memerlukan modifikasi kode)
   - Beberapa penyedia proxy yang dapat dipertimbangkan: Luminati, Oxylabs, Bright Data

## Catatan Penting

- Kecepatan internet melalui VPN gratis mungkin lebih lambat dari koneksi langsung
- Untuk perdagangan serius atau time-sensitive trading, disarankan untuk menggunakan VPN premium atau VPS luar negeri
