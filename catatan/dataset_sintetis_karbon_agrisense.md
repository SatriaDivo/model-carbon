# Dataset Sintetis Karbon AgriSense

## Tujuan

Dataset sintetis ini dibuat untuk membantu eksperimen project karbon AgriSense
ketika data sensor lokal belum memiliki label `carbon_flux`.

Dataset ini dapat digunakan untuk:

- uji coba pipeline machine learning karbon,
- integrasi dashboard Analitik Karbon,
- eksperimen model `SINK` dan `SOURCE`,
- simulasi data sensor AgriSense yang memiliki target karbon.

Dataset ini tidak boleh dianggap sebagai data observasi karbon lapangan yang
sudah tervalidasi.

## File yang Dihasilkan

Generator dataset:

```text
scripts/generate_synthetic_carbon_dataset.py
```

Output dataset:

```text
dataset/synthetic_carbon/synthetic_carbon_agrisense.csv
dataset/synthetic_carbon/synthetic_carbon_agrisense_metadata.json
```

Folder `dataset/synthetic_carbon/` sudah dimasukkan ke `.gitignore` karena
berisi data hasil generate lokal.

## Sumber Data

Dataset sintetis dibentuk dari dua sumber utama:

| Sumber | Fungsi |
|---|---|
| AmeriFlux `US-Ne1`, `US-Ne2`, `US-Ne3` | Sumber pola karbon dan target `carbon_flux` |
| Scraping AgriSense | Referensi format sensor, device ID, GPS, NPK, EC, baterai |

Target `carbon_flux` berasal dari data AmeriFlux `NEE_VUT_REF`, lalu diberi
jitter kecil agar menjadi data sintetis.

Kolom sensor AgriSense seperti `N`, `P`, `K`, `EC`, `CO2`, `TVOC`, dan baterai
disimulasikan dari rentang data AgriSense yang sudah di-scrape atau dari default
konservatif.

## Hasil Generate Saat Ini

Dataset yang sudah dibuat memiliki ringkasan:

```text
Jumlah baris    : 10.000
Jumlah kolom    : 37
Train split     : 7.000
Validation split: 1.500
Test split      : 1.500
SOURCE          : 6.243
SINK            : 3.757
Invalid values  : 0
```

Filter iklim AgriSense-like digunakan agar data tidak membawa kondisi musim
dingin Nebraska yang kurang sesuai untuk konteks AgriSense Indonesia.

Filter default:

```text
air_temperature_c  : 15 sampai 40
soil_temperature_c : 12 sampai 40
relative humidity  : 25 sampai 100
soil moisture      : 5 sampai 80
```

## Validasi Rentang Terbaru

Dataset sudah divalidasi ulang setelah proses jitter/noise. Pada versi terbaru,
semua kolom utama berada dalam rentang yang ditetapkan.

Hasil validasi:

```text
Invalid values total: 0
Rows                : 10.000
SOURCE              : 6.243
SINK                : 3.757
Train               : 7.000
Validation          : 1.500
Test                : 1.500
```

Rentang aktual kolom utama:

| Kolom | Rentang Aktual |
|---|---:|
| `air_temperature_c` | 15.00 - 38.48 |
| `soil_temperature_c` | 12.00 - 40.00 |
| `air_humidity_percent` | 25.00 - 100.00 |
| `soil_moisture_percent` | 12.62 - 53.78 |
| `solar_radiation_w_m2` | 0.00 - 1089.12 |
| `co2_ppm` | 350.00 - 570.39 |
| `tvoc_ppb` | 22.11 - 297.89 |
| `air_pressure_hpa` | 919.68 - 964.02 |
| `light_lux` | 0.00 - 130000.00 |
| `soil_ec_ms_cm` | 0.286 - 2.527 |
| `soil_ph` | 5.07 - 7.28 |
| `soil_organic_carbon_g_kg` | 12.78 - 26.91 |
| `soil_n_mg_kg` | 29 - 194 |
| `soil_p_mg_kg` | 20 - 46 |
| `soil_k_mg_kg` | 48 - 287 |
| `battery_voltage` | 11.72 - 14.44 |
| `battery_percent` | 23 - 100 |
| `rssi_dbm` | -101 - -53 |
| `carbon_flux` | -77.40 - 39.00 |

Catatan khusus:

```text
Kolom vpd_kpa pada mode default masih mengikuti skala fitur VPD_F
yang digunakan model Skenario D, bukan VPD fisik murni dalam kPa.
```

Jika ingin membuat VPD fisik dalam satuan kPa, gunakan:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_carbon_dataset.py --rows 10000 --vpd-unit kpa
```

## Kolom Penting

Kolom utama untuk project karbon:

| Kolom | Keterangan |
|---|---|
| `timestamp_local` | Waktu lokal Asia/Jakarta |
| `device_id` | Device AgriSense sintetis |
| `latitude`, `longitude`, `altitude_m` | Lokasi perangkat |
| `co2_ppm` | CO2 sintetis |
| `tvoc_ppb` | TVOC sintetis |
| `air_temperature_c` | Suhu udara |
| `air_humidity_percent` | Kelembapan udara |
| `air_pressure_hpa` | Tekanan udara |
| `light_lux` | Cahaya dalam lux |
| `solar_radiation_w_m2` | Radiasi surya sintetis |
| `vpd_kpa` | VPD sesuai mode generator |
| `soil_moisture_percent` | Kelembapan tanah |
| `soil_temperature_c` | Suhu tanah |
| `soil_ec_ms_cm` | Konduktivitas tanah |
| `soil_ph` | pH tanah |
| `soil_organic_carbon_g_kg` | Soil organic carbon sintetis |
| `soil_n_mg_kg` | Nitrogen |
| `soil_p_mg_kg` | Phosphorus |
| `soil_k_mg_kg` | Potassium |
| `carbon_flux` | Target prediksi karbon |
| `carbon_status` | `SINK` jika `carbon_flux < 0`, `SOURCE` jika `carbon_flux > 0` |
| `split` | `train`, `validation`, atau `test` |

## Cara Generate Ulang

Generate default 10.000 baris:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_carbon_dataset.py --rows 10000
```

Generate jumlah data berbeda:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_carbon_dataset.py --rows 50000
```

Generate tanpa filter iklim:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_carbon_dataset.py --rows 10000 --climate-filter none
```

Generate dengan VPD fisik dalam kPa:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic_carbon_dataset.py --rows 10000 --vpd-unit kpa
```

Catatan: mode default `--vpd-unit model` dipakai agar kompatibel dengan skala
fitur `VPD_F` yang digunakan pada Skenario D.

## Batasan

Dataset ini sintetis, sehingga tidak boleh digunakan untuk klaim karbon final.

Batasan utama:

- target `carbon_flux` berasal dari AmeriFlux, bukan pengukuran lokal AgriSense,
- hubungan antara NPK/EC dan `carbon_flux` masih simulatif,
- data cocok untuk eksperimen dan integrasi, bukan validasi karbon lapangan,
- model yang bagus pada dataset sintetis belum tentu bagus pada data nyata.

Pernyataan yang aman:

```text
Dataset ini adalah dataset sintetis berbasis AmeriFlux dan format AgriSense
untuk pengembangan prototype model karbon.
```
