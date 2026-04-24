# Audit & Perbandingan Kualitas Notebook Skenario A, B, C
**Proyek:** Sistem AI Monitoring & Prediksi Fluks Karbon Berbasis IoT  
**Perangkat IoT:** AGRISENSE-CC-001  
**Target variabel:** `carbon_flux` (NEE)  
**Tanggal audit:** April 2026

---

## Ringkasan Skor Kualitas

| Skenario | Nama | Skor | Status |
|---|---|---|---|
| **A** | Baseline Time-Series | 7 / 10 | ✅ Solid, perlu penyempurnaan |
| **B** | Fitur Statis Tunggal | 8 / 10 | ✅ Kode terbaik, logika spatial baik |
| **C** | Multi-Site + Fitur Statis | 7.5 / 10 | ⚠️ Pipeline matang, belum bisa dijalankan penuh |

---

## Skenario A — Baseline Time-Series

### Deskripsi
Melatih model murni menggunakan data time-series sensor dinamis (suhu udara, kelembapan, suhu tanah, kelembapan tanah) ditambah fitur waktu (hour, day, month). Hasil terbaik: **Random Forest R² = 0.613**.

### Yang Sudah Benar ✅

- Penggantian sentinel `-9999` → `NaN` dilakukan pada semua kolom sekaligus
- Penghapusan kolom `_QC` sudah ada dan diverifikasi di output — tidak ada data leakage
- Time-series split kronologis 80/20 — bukan `random_split`, sudah benar secara ilmiah
- Kedua model (RF + XGBoost) dibandingkan dengan metrik lengkap MAE, RMSE, R²
- Feature importance divisualisasikan setelah model terbaik dipilih

### Yang Perlu Diperbaiki ⚠️

| Tingkat | Masalah | Dampak | Solusi |
|---|---|---|---|
| 🔴 Tinggi | **SW_IN / radiasi tidak disertakan** | Model kehilangan fitur dengan korelasi tertinggi (r ≈ −0.80 hingga −0.90). R² 0.613 kemungkinan bisa naik signifikan | Tambahkan `SW_IN_F` atau `SW_IN` ke daftar fitur inti |
| 🔴 Tinggi | **Tidak ada overfitting check** | Tidak diketahui apakah train R² jauh lebih tinggi dari test R² | Tambahkan `r2_score(y_train, model.predict(X_train))` |
| 🔴 Tinggi | **Tidak ada cross-validation** | Single split rentan terhadap keberuntungan split | Gunakan `TimeSeriesSplit(n_splits=5)` dari scikit-learn |
| 🟡 Sedang | **Mapping kolom terlalu lebar** | Semua kolom `TS_` menjadi `soil_temperature_{suffix}` — bisa menghasilkan puluhan kolom | Seleksi hanya `TS_F_MDS_1` sebagai fitur inti |
| 🟡 Sedang | **Pakai `day` bukan `day_of_year`** | `day` (1–31) tidak informatif secara musiman. Skenario C sudah benar dengan `day_of_year` (1–365) | Ganti ke `df['day_of_year'] = df['reading_time'].dt.dayofyear` |
| 🟡 Sedang | **Hyperparameter default** | RF dengan `n_estimators=100` tanpa tuning — hasil belum optimal | Coba `RandomizedSearchCV` untuk tuning ringan |
| 🟢 Rendah | **Tidak ada residual plot** | Tidak bisa mendeteksi bias sistematis (mis. model selalu salah di malam hari) | Tambahkan scatter plot `y_test` vs `y_pred` dan histogram residual |

---

## Skenario B — Fitur Statis Tunggal (WoSIS)

### Deskripsi
Menambahkan `soil_ph` dan `soil_organic_carbon` dari WoSIS ke pipeline Skenario A untuk satu lokasi US-Ne1. Nilai statis di-broadcast ke seluruh baris time-series.

### Yang Sudah Benar ✅

- Fungsi `haversine_km` untuk spatial join sudah benar secara geografis — bukan euclidean biasa
- Fallback bertingkat (koordinat → country filter → global average) — pipeline tidak crash meski format file WoSIS berbeda
- Delta R² dihitung dan dicetak otomatis vs baseline Skenario A
- `n_estimators` ditingkatkan ke 200 — wajar untuk eksperimen lanjutan
- Fungsi `load_and_prepare_ameriflux` dipisah menjadi reusable function — desain kode bersih

### Yang Perlu Diperbaiki ⚠️

| Tingkat | Masalah | Dampak | Solusi |
|---|---|---|---|
| 🔴 Tinggi | **SW_IN dan VPD masih absen** | Tidak konsisten dengan Skenario C yang sudah lebih lengkap. Perbandingan A vs B vs C tidak apple-to-apple | Tambahkan `SW_IN_F` dan `VPD_F` ke `main_features` |
| 🟡 Sedang | **Risiko fallback ke rata-rata global WoSIS** | Jika file WoSIS tidak punya koordinat, nilai `soil_ph` bisa jadi rata-rata seluruh dunia — sangat berbeda dari Nebraska (pH ~6.1) | Tambahkan print dan validasi: `assert 5.0 < soil_ph < 8.0, "Nilai pH tidak wajar"` |
| 🟡 Sedang | **Tidak ada konfirmasi varians nol** | Tidak ada bukti eksplisit bahwa fitur statis memang tidak informatif | Tambahkan: `print(scenario_b_df[['soil_ph','soil_organic_carbon']].std())` |
| 🟡 Sedang | **Tidak ada overfitting check** | Sama dengan Skenario A | Cetak train R² selain test R² |
| 🟢 Rendah | **Tidak ada residual plot** | Tidak bisa membandingkan distribusi error vs Skenario A | Tambahkan histogram residual sederhana |

---

## Skenario C — Multi-Site + Fitur Statis

### Deskripsi
Menggabungkan US-Ne1, US-Ne2, US-Ne3 agar model belajar dari variasi antar lahan. Menggunakan fitur inti yang lebih selektif, cyclical encoding waktu, dan one-hot encoding `site_id`.

### Yang Sudah Benar ✅

- Fitur inti lebih selektif — tidak ekspansi semua kolom `TS_/SWC_` seperti Skenario A
- **Penambahan `solar_radiation` dan `vpd_kpa`** — koreksi terbesar dibanding Skenario A/B
- **Cyclical encoding waktu** (`hour_sin/cos`, `doy_sin/cos`) — jauh lebih baik dari raw integer. Model memahami bahwa jam 23 "dekat" dengan jam 0
- Split kronologis **per site** secara terpisah — mencegah data dari tahun yang sama di Ne3 bocor ke test Ne1
- One-hot encoding `site_id` via `pd.get_dummies` — model bisa belajar perbedaan karakteristik antar lahan
- `resolve_available_sites` memberi warning jelas jika file belum tersedia — pipeline defensive
- Dukungan `manual_site_soil.csv` sebagai input eksternal — desain deployment-ready

### Yang Perlu Diperbaiki ⚠️

| Tingkat | Masalah | Dampak | Solusi |
|---|---|---|---|
| 🔴 Tinggi | **`MANUAL_SITE_SOIL` kosong (di-comment semua)** | Semua site mendapat nilai fallback yang SAMA → `soil_ph` dan `soil_organic_carbon` tidak informatif. Skenario C belum benar-benar berbeda dari Skenario B | Isi manual atau jalankan spatial join WoSIS terlebih dulu, lalu isi `manual_site_soil.csv` |
| 🔴 Tinggi | **US-Ne2 dan US-Ne3 belum didownload** | Skenario C belum pernah dijalankan sebagai eksperimen multi-site sungguhan | Download dataset dari AmeriFlux (`10.17190/AMF/1246085` dan `10.17190/AMF/1246086`) |
| 🔴 Tinggi | **Kolom `soil_source` ikut masuk feature_cols** | String non-numerik ini akan menyebabkan error saat `rf_model_c.fit()` dipanggil | Tambahkan: `scenario_c_df = scenario_c_df.drop(columns=['soil_source'], errors='ignore')` sebelum merge ke model_df |
| 🔴 Tinggi | **Tidak ada overfitting check** | RF `n_estimators=400, max_depth=18` sangat kapasitas tinggi — potensi overfit besar | Cetak train R² dan bandingkan dengan test R² |
| 🟡 Sedang | **Training time tidak diestimasi** | n_estimators=400 + data 3 site (~300k+ baris) bisa sangat lambat | Tambahkan `time.time()` untuk mengukur durasi training, atau mulai dengan n_estimators=100 |
| 🟡 Sedang | **Tidak ada per-site evaluation** | Evaluasi hanya gabungan — tidak diketahui apakah model bagus di Ne1 tapi buruk di Ne3 | Tambahkan loop evaluasi per `site_id` di test set |
| 🟢 Rendah | **Tidak ada residual plot per site** | Tidak bisa membandingkan pola error antar lahan | Plot residual dengan warna berbeda per `site_id` |

---

## Gap Kritis yang Sama di Semua Skenario

### 1. SW_IN / Radiasi Tidak Ada di Skenario A dan B
**Dampak:** SW_IN adalah fitur dengan korelasi tertinggi terhadap carbon_flux (r ≈ −0.80 hingga −0.90 di siang hari). Model Skenario A/B kehilangan sinyal terpenting. R² = 0.613 kemungkinan bisa naik hanya dengan satu fitur ini.

```python
# Tambahkan ke seleksi kolom di load_and_prepare_ameriflux()
'solar_radiation': detect_first_available(df.columns, ['SW_IN_F', 'SW_IN_F_MDS', 'SW_IN']),
```

### 2. Tidak Ada Overfitting Check di Semua Skenario
**Dampak:** Tanpa membandingkan train R² vs test R², tidak bisa diketahui apakah model menghafal data (overfit) atau benar-benar belajar pola.

```python
# Tambahkan setelah evaluasi test set
train_r2 = r2_score(y_train, model.predict(X_train))
test_r2  = r2_score(y_test,  model.predict(X_test))
print(f"Train R²: {train_r2:.4f} | Test R²: {test_r2:.4f} | Gap: {train_r2 - test_r2:.4f}")
```

### 3. `day` vs `day_of_year` — Tidak Konsisten Antar Skenario
**Dampak:** Skenario A/B pakai `day` (1–31, hari dalam bulan) yang tidak informatif musiman. Skenario C sudah benar dengan `doy_sin/cos`.

```python
# Ganti di Skenario A dan B
df['day_of_year'] = df['reading_time'].dt.dayofyear  # bukan dt.day
```

### 4. Tidak Ada Residual Analysis
**Dampak:** Tidak bisa mendeteksi apakah error sistematis pada jam malam hari, bulan musim dingin, atau kondisi kelembapan ekstrem.

```python
# Plot sederhana untuk deteksi bias
residuals = y_test - y_pred
plt.figure(figsize=(10, 4))
plt.subplot(1, 2, 1)
plt.scatter(y_pred, residuals, alpha=0.3, s=5)
plt.axhline(0, color='red', linewidth=1)
plt.xlabel('Predicted carbon_flux'); plt.ylabel('Residual')
plt.title('Residual vs Predicted')
plt.subplot(1, 2, 2)
plt.hist(residuals, bins=50)
plt.title('Distribusi Residual')
plt.tight_layout(); plt.show()
```

---

## Perbandingan Fitur yang Digunakan

| Fitur | Skenario A | Skenario B | Skenario C |
|---|:---:|:---:|:---:|
| `air_temperature` | ✅ | ✅ | ✅ |
| `relative_humidity` | ✅ | ✅ | ✅ |
| `soil_temperature` | ✅ (semua kolom) | ✅ (semua kolom) | ✅ (kolom inti saja) |
| `soil_water_content` | ✅ (semua kolom) | ✅ (semua kolom) | ✅ (kolom inti saja) |
| `solar_radiation (SW_IN)` | ❌ | ❌ | ✅ |
| `vpd_kpa` | ❌ | ❌ | ✅ |
| `hour` | raw integer | raw integer | sin/cos cyclical |
| `day` | raw integer (1–31) | raw integer (1–31) | `doy` sin/cos cyclical |
| `month` | raw integer | raw integer | raw integer |
| `soil_ph` | ❌ | ✅ (broadcast) | ✅ (per site) |
| `soil_organic_carbon` | ❌ | ✅ (broadcast) | ✅ (per site) |
| `site_id` | ❌ | ❌ | ✅ one-hot |

---

## Perbandingan Konfigurasi Model

| Aspek | Skenario A | Skenario B | Skenario C |
|---|---|---|---|
| Model utama | RF + XGBoost | RF saja | RF saja |
| n_estimators | 100 | 200 | 400 |
| max_depth | default | default | 18 |
| min_samples_leaf | default | default | 2 |
| Baseline R² target | — | 0.613 (Skenario A) | 0.613 (Skenario A) |
| Split method | kronologis global | kronologis global | kronologis per site |
| Cross-validation | ❌ | ❌ | ❌ |
| Overfitting check | ❌ | ❌ | ❌ |

---

## Urutan Perbaikan yang Disarankan

### Jangka Pendek (sebelum eksperimen berikutnya)

1. **Tambahkan SW_IN ke Skenario A dan B** — kemungkinan peningkatan R² terbesar
2. **Cetak train R² di semua skenario** — satu baris kode, dampak diagnostik besar
3. **Drop kolom `soil_source` di Skenario C** — mencegah error saat runtime
4. **Ganti `day` → `day_of_year` di Skenario A dan B** — selaraskan dengan Skenario C

### Jangka Menengah (setelah dataset lengkap)

5. **Download US-Ne2 dan US-Ne3**, jalankan Skenario C sebagai multi-site sungguhan
6. **Isi `MANUAL_SITE_SOIL` dengan hasil spatial join WoSIS per site** — aktifkan variasi fitur statis
7. **Tambahkan TimeSeriesSplit CV** minimal 3 fold di Skenario A sebagai referensi robustness
8. **Tambahkan residual plot** di semua skenario

### Jangka Panjang (menuju deployment)

9. **Tuning hyperparameter** dengan RandomizedSearchCV untuk model final
10. **Evaluasi per-site** di Skenario C untuk memastikan model tidak hanya bagus di Ne1
11. **Export model dengan metadata lengkap** — simpan daftar fitur, versi data, dan metrik evaluasi bersama file `.pkl`
12. **Uji prediksi pada payload IoT simulasi** sebelum integrasi ke backend Laravel

---

## Kesimpulan

Ketiga skenario sudah memiliki fondasi yang benar:
- Data leakage sudah diantisipasi (penghapusan `_QC`)
- Time-series split kronologis sudah diterapkan
- Pipeline modular dan dapat direproduksi

**Skenario B memiliki kode terbersih** secara teknis dengan desain fungsi yang paling reusable.

**Skenario C memiliki arsitektur paling maju** dengan cyclical encoding, fitur radiasi, dan split per site — namun belum bisa divalidasi karena dataset belum lengkap dan nilai soil statis masih homogen.

**Perbaikan terpenting dan tercepat** adalah menambahkan `SW_IN` ke Skenario A, karena fitur ini memiliki korelasi ilmiah tertinggi (r ≈ −0.90) dan hampir pasti akan meningkatkan R² secara signifikan di atas 0.613 hanya dengan satu penambahan kolom.

---

*Dokumen ini dibuat berdasarkan analisis kode sumber notebook skenario-a-baseline.ipynb, skenario-b.ipynb, dan skenario-c.ipynb | Proyek AGRISENSE-CC-001*
