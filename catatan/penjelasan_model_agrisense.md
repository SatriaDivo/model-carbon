# Penjelasan Penggunaan Model Skenario D untuk Project Karbon AgriSense

## Ringkasan

Model yang dibuat pada `skenario-d-final.ipynb` sudah bisa digunakan sebagai
model awal untuk project karbon AgriSense. Model ini dapat menerima data sensor
AgriSense yang sudah di-scrape, melakukan preprocessing, lalu menghasilkan
prediksi `carbon_flux`.

Namun, model ini belum dapat disebut sebagai model karbon lokal yang sudah
tervalidasi penuh untuk AgriSense Indonesia. Hal ini karena model dilatih
menggunakan data AmeriFlux dari Nebraska, Amerika Serikat, sedangkan data
AgriSense berasal dari perangkat IoT lokal dan sebagian besar data scraping
masih berstatus simulasi.

Kesimpulan utama:

```text
Model Skenario D sudah layak digunakan sebagai prototype / MVP
untuk fitur Analitik Karbon AgriSense.
```

Untuk penggunaan ilmiah atau produksi, model sebaiknya disebut sebagai:

```text
Model estimasi carbon_flux berbasis transfer dari dataset AmeriFlux.
```

## Fungsi Model Skenario D

Model pada Skenario D adalah model machine learning berbasis
`RandomForestRegressor` yang dilatih untuk memprediksi:

```text
carbon_flux / NEE
```

Output model menunjukkan apakah lahan sedang menyerap atau melepas karbon:

```text
carbon_flux < 0  -> SINK, lahan menyerap CO2
carbon_flux > 0  -> SOURCE, lahan melepas CO2
```

Model ini bukan model untuk memprediksi N, P, K, pH, kelembapan tanah, atau
nilai sensor lainnya. Nilai-nilai sensor tersebut digunakan sebagai input,
sedangkan output model adalah estimasi `carbon_flux`.

## Alur Penggunaan pada AgriSense

Secara teknis, model dapat digunakan dalam alur berikut:

```text
Data sensor AgriSense
-> scraping dari API AgriSense
-> preprocessing dan mapping fitur
-> model Skenario D
-> prediksi carbon_flux
-> status SINK / SOURCE
-> ditampilkan pada dashboard Analitik Karbon
```

Dengan alur tersebut, data sensor real-time dari AgriSense dapat diubah menjadi
indikator karbon lahan.

## Kesesuaian Fitur AgriSense dengan Model

Model Skenario D membutuhkan fitur berikut:

| Fitur Model | Sumber dari AgriSense | Status |
|---|---|---|
| `air_temperature_c` | `environment.air_temperature_c` | Ada |
| `relative_humidity` | `environment.air_humidity_percent` | Ada, perlu rename |
| `soil_temperature_c` | `soil_7in1.soil_temperature_c` | Ada |
| `soil_water_content` | `soil_7in1.soil_moisture_percent` | Ada, perlu rename |
| `solar_radiation` | `environment.light_lux` | Ada sebagai proxy |
| `vpd_kpa` | Dihitung dari suhu dan kelembapan | Bisa dihitung |
| `hour_sin`, `hour_cos` | Dari timestamp | Bisa dibuat |
| `doy_sin`, `doy_cos` | Dari timestamp | Bisa dibuat |
| `month` | Dari timestamp | Bisa dibuat |
| `soil_ph` | `soil_7in1.soil_ph` | Ada |
| `soil_organic_carbon` | Tidak ada di sensor | Harus diisi manual/proxy |
| `site_US-Ne1`, `site_US-Ne2`, `site_US-Ne3` | Tidak cocok langsung | Perlu strategi pengganti |

Sebagian besar fitur utama sudah tersedia dari AgriSense, tetapi ada beberapa
fitur yang perlu pendekatan tambahan.

## Hasil Uji Teknis dengan Data Scraping

Model sudah diuji menggunakan data hasil scraping dari AgriSense.

Hasil uji:

```text
Total data scraping       : 48 baris
Data lolos validasi input : 45 baris
Model berhasil dipakai    : Ya
Output yang dihasilkan    : predicted_carbon_flux
```

Ringkasan hasil prediksi:

```text
Rentang prediksi carbon_flux : 1.43 sampai 4.17
Status prediksi              : Semua SOURCE
```

Artinya, pada data yang diuji, model memperkirakan bahwa kondisi lahan sedang
lebih dominan melepas CO2 daripada menyerap CO2.

## Keterbatasan Model untuk AgriSense

Walaupun model sudah bisa digunakan secara teknis, ada beberapa keterbatasan
penting.

### 1. Model Dilatih dari Data AmeriFlux

Model dilatih menggunakan data AmeriFlux dari site:

```text
US-Ne1
US-Ne2
US-Ne3
```

Lokasi tersebut berada di Nebraska, Amerika Serikat. Kondisi iklim, tanah,
tanaman, dan sistem pertanian berbeda dengan lokasi AgriSense di Indonesia.

Karena itu, performa `R2 = 0.8196` pada Skenario D hanya berlaku untuk data uji
AmeriFlux, bukan otomatis berlaku untuk AgriSense.

### 2. Data AgriSense Belum Memiliki Target carbon_flux

Data AgriSense memiliki sensor seperti:

```text
CO2 ppm
TVOC
suhu udara
kelembapan udara
tekanan udara
cahaya
kelembapan tanah
suhu tanah
pH tanah
N
P
K
EC
baterai
```

Namun data tersebut belum memiliki label:

```text
carbon_flux / NEE
```

Karena tidak ada target `carbon_flux`, model tidak bisa dievaluasi secara lokal
dengan metrik seperti MAE, RMSE, atau R2 pada data AgriSense.

### 3. Cahaya Lux Hanya Proxy untuk Solar Radiation

Model Skenario D menggunakan `solar_radiation` dari AmeriFlux. Pada AgriSense,
data yang tersedia adalah `light_lux`.

Dalam scraping, `light_lux` dapat dikonversi menjadi proxy:

```text
solar_radiation_proxy_w_m2 = light_lux / 120
```

Konversi ini hanya pendekatan kasar. Untuk hasil yang lebih baik, perangkat
AgriSense sebaiknya memiliki sensor radiasi matahari atau PAR yang lebih sesuai
dengan data training.

### 4. Soil Organic Carbon Tidak Ada di Sensor

Model membutuhkan fitur:

```text
soil_organic_carbon
```

Namun sensor AgriSense tidak membaca nilai tersebut. Untuk sementara, nilai ini
bisa diisi dengan:

```text
rata-rata dari lookup Skenario D
nilai manual dari pengukuran tanah
nilai dari dataset tanah eksternal
```

Pilihan terbaik adalah menggunakan data pengukuran laboratorium atau data tanah
lokal.

### 5. Site ID Tidak Sama

Model dilatih dengan site:

```text
US-Ne1
US-Ne2
US-Ne3
```

Sedangkan AgriSense memiliki device:

```text
AGRISENSE-CC-001
AGRISENSE-CC-002
B-01
```

Karena site berbeda, fitur one-hot site pada model tidak cocok secara langsung.
Pada uji teknis, semua fitur site AmeriFlux diisi `0` sebagai tanda lokasi
AgriSense tidak termasuk site training.

Ini bisa berjalan secara teknis, tetapi secara ilmiah masih perlu validasi.

### 6. Mayoritas Data Scraping Masih Simulasi

Data scraping AgriSense saat diuji memiliki status:

```text
dummy_simulated : 43 baris
normal          : 4 baris
dummy           : 1 baris
```

Artinya, sebagian besar data belum benar-benar mewakili pembacaan sensor lapangan
yang stabil. Untuk training atau validasi model lokal, data simulasi sebaiknya
dipisahkan dari data sensor nyata.

## Posisi Model dalam Project

Posisi model Skenario D paling tepat adalah sebagai:

```text
carbon inference engine awal
```

Model ini dapat digunakan untuk:

- menguji integrasi data sensor AgriSense dengan model karbon,
- membuat fitur Analitik Karbon pada dashboard,
- menampilkan estimasi `carbon_flux`,
- menampilkan status `SINK` atau `SOURCE`,
- membangun MVP project karbon.

Model ini belum tepat digunakan untuk:

- klaim akurasi karbon lokal Indonesia,
- validasi ilmiah final,
- rekomendasi kebijakan karbon,
- laporan produksi tanpa catatan keterbatasan,
- menggantikan pengukuran flux tower atau chamber.

## Rekomendasi Lanjutan

Agar model semakin kuat untuk project AgriSense, langkah berikut disarankan:

1. Kumpulkan data sensor AgriSense yang benar-benar `normal` dalam jumlah lebih
   besar.
2. Pisahkan data `dummy`, `dummy_simulated`, dan data sensor nyata.
3. Tambahkan validasi range sensor sebelum data masuk ke model.
4. Tambahkan sumber `soil_organic_carbon` lokal.
5. Gunakan sensor radiasi matahari atau PAR jika memungkinkan.
6. Jika tersedia data `carbon_flux` lokal, lakukan fine-tuning atau training
   ulang model.
7. Buat endpoint inference agar dashboard AgriSense bisa memanggil model secara
   otomatis.

## Kesimpulan

Model yang sudah dibuat pada `skenario-d-final.ipynb` sudah bisa digunakan untuk
project karbon AgriSense sebagai model awal.

Secara teknis:

```text
Model bisa menerima data scraping AgriSense dan menghasilkan prediksi carbon_flux.
```

Secara ilmiah:

```text
Model masih perlu validasi lokal karena dilatih dari data AmeriFlux,
bukan dari data carbon_flux AgriSense.
```

Dengan demikian, pernyataan yang paling adil adalah:

```text
Model Skenario D layak digunakan sebagai prototype Analitik Karbon AgriSense,
tetapi belum cukup untuk disebut sebagai model karbon lokal final.
```
