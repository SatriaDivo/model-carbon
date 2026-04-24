# Skenario C

Sumber: `skenario-c.ipynb`

# Skenario C: Multi-Site AmeriFlux + Fitur Tanah Statis

Dokumen ini menjelaskan eksperimen **Skenario C** secara rinci, yaitu perluasan model prediksi `carbon_flux` dari pendekatan single-site menjadi **multi-site** dengan menggabungkan tiga site AmeriFlux di Mead, Nebraska:

- `US-Ne1`
- `US-Ne2`
- `US-Ne3`

Tujuan utama Skenario C adalah meningkatkan performa prediksi dengan:

- memperbesar jumlah data latih,
- mempertahankan hanya fitur inti yang relevan,
- menangkap variasi antar lahan melalui `site_id`,
- dan membuka peluang agar fitur tanah statis seperti `soil_ph` dan `soil_organic_carbon` benar-benar bermanfaat.

---

## 1. Latar Belakang

Pada Skenario A, model baseline memakai data time-series dari satu site dan menghasilkan:

- `R2 = 0.613`

Pada Skenario B, fitur tanah statis ditambahkan ke satu site, tetapi kontribusinya kecil karena:

- nilainya konstan pada seluruh baris,
- tidak ada variasi antar lokasi,
- sehingga model hampir tidak mendapat informasi baru dari fitur statis tersebut.

Skenario C dirancang untuk mengatasi keterbatasan itu dengan menggabungkan beberapa lahan yang berdekatan namun memiliki karakteristik manajemen dan kondisi biofisik yang sedikit berbeda.

---

## 2. Tujuan Eksperimen

Tujuan teknis dan ilmiah dari Skenario C adalah:

1. Meningkatkan akurasi prediksi `carbon_flux`.
2. Menguji apakah pembelajaran lintas site dapat meningkatkan generalisasi model.
3. Menguji pengaruh variasi waktu, iklim mikro, dan identitas lahan terhadap `NEE`.
4. Menyiapkan pondasi agar fitur tanah statis WoSIS dapat digunakan secara lebih bermakna.

---

## 3. Dataset yang Digunakan

### 3.1 Site AmeriFlux

Tiga site yang digunakan:

| Site | Deskripsi |
| --- | --- |
| `US-Ne1` | Irrigated Continuous Maize |
| `US-Ne2` | Irrigated Maize-Soybean Rotation |
| `US-Ne3` | Rainfed Maize-Soybean Rotation |

Masing-masing site menggunakan target yang sama:

- `NEE_VUT_REF`

Target tersebut kemudian diharmonisasi menjadi:

- `carbon_flux`

### 3.2 Fitur inti yang dipakai

Fitur yang dipilih adalah fitur yang kuat secara ilmiah dan tersedia relatif konsisten pada tiga site:

- `air_temperature_c`
- `relative_humidity`
- `soil_temperature_c`
- `soil_water_content`
- `solar_radiation`
- `vpd_kpa`
- `hour_sin`
- `hour_cos`
- `doy_sin`
- `doy_cos`
- `month`
- `soil_ph`
- `soil_organic_carbon`
- dummy `site_id`

---

## 4. Dasar Ilmiah Variabel dan Target

### 4.1 Definisi target carbon flux

Dalam eksperimen ini, target `carbon_flux` merepresentasikan **Net Ecosystem Exchange** atau `NEE`.

Secara konseptual:

```text
NEE = Ra + Rh - GPP
```

dengan:

- `Ra` = respirasi autotrofik tanaman
- `Rh` = respirasi heterotrofik mikroba tanah
- `GPP` = gross primary production atau penyerapan karbon melalui fotosintesis

Interpretasi tanda:

- `NEE < 0` berarti ekosistem menyerap karbon dari atmosfer, yaitu **carbon sink**
- `NEE > 0` berarti ekosistem melepas karbon ke atmosfer, yaitu **carbon source**

### 4.2 Alasan ilmiah pemilihan fitur

#### a. `solar_radiation`

Radiasi surya berkaitan langsung dengan fotosintesis. Semakin tinggi energi cahaya yang tersedia, semakin besar potensi `GPP`, sehingga `NEE` cenderung makin negatif di siang hari.

#### b. `soil_temperature_c`

Suhu tanah memengaruhi respirasi mikroba dan dekomposisi bahan organik tanah. Ketika suhu tanah naik, laju pelepasan karbon dari tanah juga cenderung meningkat.

#### c. `soil_water_content`

Kelembapan tanah memengaruhi aktivitas mikroba, respirasi tanah, dan stres air tanaman.

#### d. `vpd_kpa` dan `relative_humidity`

Kedua variabel ini berkaitan dengan status uap air atmosfer dan pembukaan stomata tanaman. VPD tinggi biasanya menekan fotosintesis.

#### e. `site_id`

Dummy `site_id` dipakai untuk membantu model mengenali karakter tetap antar lahan, misalnya perbedaan irigasi, rotasi tanaman, dan kondisi agroekologis.

---

## 5. Tahapan Preprocessing

### 5.1 Pembersihan missing value

Pada dataset AmeriFlux, nilai hilang disandikan sebagai:

```text
-9999
```

Nilai tersebut diganti menjadi:

```text
NaN
```

### 5.2 Harmonisasi kolom

Kolom asli AmeriFlux dipetakan ke nama fitur yang lebih konsisten:

| Kolom asli | Nama harmonisasi |
| --- | --- |
| `TA_F` | `air_temperature_c` |
| `RH` | `relative_humidity` |
| `TS_F_MDS_1` | `soil_temperature_c` |
| `SWC_F_MDS_1` | `soil_water_content` |
| `SW_IN_F` | `solar_radiation` |
| `VPD_F` | `vpd_kpa` |
| `NEE_VUT_REF` | `carbon_flux` |

### 5.3 Ekstraksi fitur waktu

Dari `TIMESTAMP_START`, dibuat beberapa fitur waktu:

- `hour`
- `day_of_year`
- `month`

Lalu fitur waktu periodik diubah ke bentuk siklik agar model dapat memahami sifat melingkar dari waktu.

#### Rumus encoding jam

Untuk jam ke-`h`:

```text
hour_sin = sin(2πh / 24)
hour_cos = cos(2πh / 24)
```

#### Rumus encoding hari ke-n dalam tahun

Untuk `d = day_of_year`:

```text
doy_sin = sin(2πd / 365.25)
doy_cos = cos(2πd / 365.25)
```

Encoding ini penting karena:

- jam `23` dan `0` sebenarnya berdekatan,
- hari `365` dan `1` juga berdekatan,
- tetapi jika dipakai sebagai angka biasa, model akan menganggapnya berjauhan.

### 5.4 Seleksi fitur inti

Salah satu perubahan paling penting dari Skenario C adalah hanya memakai fitur inti, bukan seluruh kolom sensor turunan.

Akibatnya, jumlah data bersih tetap sangat besar dan tidak runtuh seperti pada Skenario B.

---

## 6. Hasil Loading dan Preprocessing

Ringkasan hasil preprocessing:

| Site | Raw shape | Clean shape | Target | Fitur inti yang terdeteksi |
| --- | --- | --- | --- | --- |
| `US-Ne1` | `(210384, 241)` | `(206242, 16)` | `NEE_VUT_REF` | `TA_F`, `RH`, `TS_F_MDS_1`, `SWC_F_MDS_1`, `SW_IN_F`, `VPD_F` |
| `US-Ne2` | `(210384, 241)` | `(195141, 16)` | `NEE_VUT_REF` | `TA_F`, `RH`, `TS_F_MDS_1`, `SWC_F_MDS_1`, `SW_IN_F`, `VPD_F` |
| `US-Ne3` | `(210384, 243)` | `(201509, 16)` | `NEE_VUT_REF` | `TA_F`, `RH`, `TS_F_MDS_1`, `SWC_F_MDS_1`, `SW_IN_F`, `VPD_F` |

Temuan penting:

- ketiga site berhasil dimuat dengan baik,
- jumlah data bersih tetap sangat besar,
- target antar site konsisten,
- pipeline ini jauh lebih sehat daripada pipeline yang menjatuhkan data bersih menjadi sangat kecil.

---

## 7. Integrasi Fitur Tanah Statis

Pada run ini, nilai tanah statis masih memakai fallback WoSIS yang sama untuk ketiga site:

| Site | soil_ph | soil_organic_carbon | Sumber |
| --- | ---: | ---: | --- |
| `US-Ne1` | `5.992126` | `19.63971` | fallback WoSIS |
| `US-Ne2` | `5.992126` | `19.63971` | fallback WoSIS |
| `US-Ne3` | `5.992126` | `19.63971` | fallback WoSIS |

Artinya, pada run ini:

- fitur tanah statis **sudah masuk ke model**,
- tetapi **belum bervariasi antar site**,
- sehingga model belum bisa belajar hubungan statis tanah secara nyata.

### Rumus integrasi statis

Jika `x_i(t)` adalah data dinamis untuk site `i` pada waktu `t`, dan `s_i` adalah fitur tanah statis site `i`, maka vektor fitur akhir dapat dinyatakan sebagai:

```text
X_i(t) = [x_i(t), s_i]
```

Dalam implementasi saat ini:

```text
s_1 = s_2 = s_3
```

Karena nilai statis sama untuk semua site, kontribusinya ke model menjadi sangat kecil.

### 7.1 Cara mengisi nilai manual per site

File WoSIS lokal yang tersedia saat ini hanya berisi:

- `profile_id`
- `layer_id`
- `upper_depth`
- `lower_depth`
- `value_avg`
- `country_name`

File tersebut **tidak memiliki koordinat `latitude/longitude`**, sehingga spatial join otomatis yang valid belum bisa dilakukan langsung dari file lokal saat ini.

Untuk itu, notebook sekarang mendukung dua sumber nilai manual:

1. Dictionary `MANUAL_SITE_SOIL` di dalam notebook.
2. File CSV manual di:

`skenario-c/manual_site_soil.csv`

Saya juga sudah menyiapkan template di:

`skenario-c/manual_site_soil_template.csv`

Struktur file yang harus diisi adalah:

| site_id | soil_ph | soil_organic_carbon | source_notes |
| --- | ---: | ---: | --- |
| `US-Ne1` | nilai pH hasil join | nilai SOC hasil join | catatan sumber |
| `US-Ne2` | nilai pH hasil join | nilai SOC hasil join | catatan sumber |
| `US-Ne3` | nilai pH hasil join | nilai SOC hasil join | catatan sumber |

Contoh jika hasil spatial join Anda sudah tersedia:

```csv
site_id,soil_ph,soil_organic_carbon,source_notes
US-Ne1,6.12,18.40,WoSIS nearest profiles 0-30 cm
US-Ne2,6.28,20.10,WoSIS nearest profiles 0-30 cm
US-Ne3,5.87,16.90,WoSIS nearest profiles 0-30 cm
```

Jika file tersebut sudah diisi dan disimpan sebagai `manual_site_soil.csv`, notebook akan membacanya otomatis dan memakai nilainya menggantikan fallback.

### 7.2 Aturan pengisian yang benar

- `site_id` harus persis sama dengan `US-Ne1`, `US-Ne2`, `US-Ne3`.
- `soil_ph` harus berupa angka pH.
- `soil_organic_carbon` harus berupa angka SOC, konsisten dengan satuan yang Anda pilih.
- Nilai antar site sebaiknya berbeda bila memang hasil join menunjukkan perbedaan.
- Jangan mengisi ketiga site dengan angka yang sama jika tujuan Anda adalah memberi variasi spasial ke model.

### 7.3 Script pembentuk manual_site_soil.csv

Saya juga menambahkan script:

`skenario-c/build_manual_site_soil.py`

Script ini dipakai jika Anda sudah memiliki file WoSIS yang **memuat koordinat** `latitude/longitude`. Alurnya:

1. Membaca file pH dan organic carbon.
2. Memfilter wilayah Nebraska.
3. Memfilter horizon tanah pada kedalaman `0–30 cm`.
4. Menghitung jarak ke `US-Ne1`, `US-Ne2`, dan `US-Ne3`.
5. Mengambil `top-k` profil terdekat per site.
6. Menghasilkan `manual_site_soil.csv` yang langsung bisa dibaca notebook.

Contoh penggunaan:

```powershell
python .\skenario-c\build_manual_site_soil.py `
  --ph "D:\path\to\wosis_ph_with_coords.csv" `
  --orgc "D:\path\to\wosis_orgc_with_coords.csv" `
  --output "D:\Tugas Kuliah\Semester 6\MBKM - Magang\carbon\code-dataset-3\skenario-c\manual_site_soil.csv" `
  --top-k 5 `
  --radius-km 50 `
  --depth-max-cm 30
```

Catatan:

- Script ini **tidak bisa dipakai** pada file WoSIS lokal yang sekarang ada di workspace, karena file tersebut belum memiliki koordinat.
- Begitu Anda punya file snapshot WoSIS yang lengkap, script ini bisa langsung dipakai.

---

## 8. Split Train-Test Kronologis

Split dilakukan per site secara kronologis dengan rasio:

```text
train = 80%
test  = 20%
```

Jika jumlah data suatu site adalah `N`, maka:

```text
N_train = floor(0.8 × N)
N_test  = N - N_train
```

Hasil split:

| Site | Train rows | Test rows |
| --- | ---: | ---: |
| `US-Ne1` | `164993` | `41249` |
| `US-Ne2` | `156112` | `39029` |
| `US-Ne3` | `161207` | `40302` |

Keuntungan pendekatan ini:

- tidak ada kebocoran informasi masa depan,
- evaluasi lebih realistis,
- dan model diuji pada bagian waktu yang benar-benar lebih baru.

---

## 9. Model yang Digunakan

Model utama pada Skenario C adalah:

```text
RandomForestRegressor
```

### 9.1 Prinsip dasar Random Forest

Random Forest adalah kumpulan banyak decision tree. Untuk masalah regresi, prediksi akhir adalah rata-rata prediksi dari seluruh tree:

```text
ŷ(x) = (1 / M) × Σ T_m(x)
```

dengan:

- `ŷ(x)` = prediksi akhir untuk sampel `x`
- `M` = jumlah tree
- `T_m(x)` = prediksi dari tree ke-`m`

### 9.2 Mengapa cocok untuk kasus ini

Random Forest cocok karena:

- mampu menangkap hubungan non-linear,
- cukup tahan terhadap interaksi fitur yang kompleks,
- tidak membutuhkan normalisasi ketat,
- dan bekerja baik pada kombinasi fitur cuaca, tanah, dan waktu.

---

## 10. Rumus Evaluasi

Evaluasi dilakukan menggunakan `MAE`, `RMSE`, dan `R2`.

Misalkan:

- `y_i` = nilai aktual
- `ŷ_i` = nilai prediksi
- `n` = jumlah sampel

### 10.1 Mean Absolute Error

```text
MAE = (1/n) × Σ |y_i - ŷ_i|
```

MAE mengukur rata-rata besar kesalahan absolut.

### 10.2 Root Mean Squared Error

```text
RMSE = sqrt((1/n) × Σ (y_i - ŷ_i)^2)
```

RMSE memberi penalti lebih besar pada error yang besar.

### 10.3 Coefficient of Determination

```text
R2 = 1 - (Σ (y_i - ŷ_i)^2 / Σ (y_i - ȳ)^2)
```

dengan `ȳ` adalah rata-rata nilai aktual.

Interpretasi umum:

- `R2 = 1` berarti prediksi sempurna
- `R2 = 0` berarti model tidak lebih baik dari rata-rata
- `R2 < 0` berarti model lebih buruk dari baseline rata-rata

---

## 11. Hasil Evaluasi Model

Model `RandomForestRegressor` multi-site menghasilkan:

- `MAE = 2.0263`
- `RMSE = 4.6170`
- `R2 = 0.8135`

### Perbandingan dengan baseline Skenario A

- `R2 Baseline A = 0.613`
- `R2 Skenario C = 0.8135`
- `Delta R2 = +0.2005`

Rumus selisih performa:

```text
Delta R2 = R2_skenario_C - R2_baseline
```

sehingga:

```text
Delta R2 = 0.8135 - 0.613 = 0.2005
```

Kesimpulan:

**Strategi multi-site meningkatkan performa model secara signifikan terhadap baseline.**

---

## 12. Feature Importance

Hasil feature importance:

| Rank | Feature | Importance |
| --- | --- | ---: |
| 1 | `solar_radiation` | `0.339812` |
| 2 | `doy_sin` | `0.270547` |
| 3 | `doy_cos` | `0.213833` |
| 4 | `soil_temperature_c` | `0.084090` |
| 5 | `soil_water_content` | `0.025893` |
| 6 | `relative_humidity` | `0.018847` |
| 7 | `air_temperature_c` | `0.010083` |
| 8 | `site_US-Ne3` | `0.008586` |
| 9 | `vpd_kpa` | `0.006774` |
| 10 | `hour_cos` | `0.006689` |
| 11 | `hour_sin` | `0.005242` |
| 12 | `month` | `0.004439` |
| 13 | `site_US-Ne1` | `0.003428` |
| 14 | `site_US-Ne2` | `0.001738` |
| 15 | `soil_ph` | `0.000000` |
| 16 | `soil_organic_carbon` | `0.000000` |

### 12.1 Interpretasi feature importance

#### a. `solar_radiation` paling dominan

Ini sesuai teori bahwa radiasi merupakan penggerak utama fotosintesis dan sangat menentukan perubahan `NEE`.

#### b. `doy_sin` dan `doy_cos` sangat besar

Ini menunjukkan bahwa pola musiman tahunan adalah komponen yang sangat kuat dalam fluks karbon.

#### c. `soil_temperature_c` tetap penting

Suhu tanah memegang peran besar dalam respirasi tanah dan pelepasan karbon.

#### d. Dummy `site_id` punya kontribusi nyata

Walaupun kecil, dummy site membantu model membedakan karakter lahan.

#### e. `soil_ph` dan `soil_organic_carbon` nol

Hal ini terjadi karena nilai statis ketiga site masih sama, sehingga tidak ada informasi tambahan yang bisa dipelajari model dari dua fitur tersebut.

---

## 13. Rumus Intuitif untuk Feature Importance

Pada Random Forest, feature importance umumnya dihitung dari total penurunan impurity yang diberikan suatu fitur di seluruh split tree.

Secara intuitif:

```text
FI_j ∝ Σ penurunan error akibat fitur j
```

Lalu dinormalisasi sehingga:

```text
Σ FI_j = 1
```

Karena itu, semakin sering suatu fitur menghasilkan split yang sangat membantu mengurangi error prediksi, semakin besar nilai importance-nya.

---

## 14. Analisis Hasil

### 14.1 Mengapa performa naik tajam

Ada tiga penyebab utama:

1. Jumlah data latih jauh lebih besar.
2. Fitur yang dipakai lebih relevan dan tidak terlalu banyak.
3. Informasi antar-site membantu model memahami variasi ekosistem dan manajemen lahan.

### 14.2 Mengapa hasil ini lebih baik dari Skenario B

Skenario B menambahkan fitur statis ke satu site, tetapi:

- data efektif terlalu sedikit,
- nilai statis tidak bervariasi,
- dan kombinasi fitur terlalu agresif dalam `dropna`.

Skenario C memperbaiki ketiga hal itu sekaligus.

### 14.3 Apa arti `R2 = 0.8135`

Secara praktis, angka ini menunjukkan bahwa model mampu menjelaskan sekitar:

```text
81.35%
```

variasi target `carbon_flux` pada data uji.

Ini berarti target performa di atas `70%` telah terlampaui dengan margin yang cukup besar.

---

## 15. Keterbatasan Eksperimen

Walaupun hasilnya sangat baik, masih ada beberapa keterbatasan:

1. `soil_ph` dan `soil_organic_carbon` belum memakai nilai per-site yang benar-benar berbeda.
2. Belum ada pembanding langsung dengan `XGBoostRegressor` pada pipeline yang sama.
3. Belum ada analisis error terpisah untuk masing-masing site.
4. Belum ada validasi tambahan seperti cross-year validation atau holdout year khusus.

---

## 16. Kesimpulan Akhir

Skenario C merupakan eksperimen terbaik sejauh ini.

Poin-poin utamanya:

- target `R2 > 0.70` berhasil dicapai,
- model mencapai `R2 = 0.8135`,
- terjadi peningkatan `+0.2005` dibanding baseline,
- fitur paling dominan adalah `solar_radiation`, pola musiman tahunan, dan `soil_temperature_c`,
- strategi multi-site terbukti jauh lebih efektif daripada eksperimen single-site dengan fitur statis konstan.

---

## 17. Rekomendasi Lanjutan

1. Isi `MANUAL_SITE_SOIL` dengan hasil spatial join WoSIS yang berbeda untuk `US-Ne1`, `US-Ne2`, dan `US-Ne3`.
2. Jalankan `XGBoostRegressor` sebagai pembanding langsung.
3. Ekspor model terbaik ke `.pkl` untuk integrasi backend Laravel.
4. Tambahkan analisis residual per site dan per musim.
5. Uji robustness model pada subset tahun tertentu untuk melihat kestabilan generalisasi.
