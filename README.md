# Model Carbon

Proyek ini berisi eksperimen data science untuk **monitoring dan prediksi fluks karbon** berbasis data sensor lingkungan dan tanah. Fokus utamanya adalah membangun model machine learning untuk memprediksi `carbon_flux` atau `NEE` menggunakan data **AmeriFlux** dan fitur tanah statis dari **WoSIS/ISRIC**.

## Ringkasan

- **Perangkat IoT**: `AGRISENSE-CC-001`
- **Target utama**: `carbon_flux` (`NEE / FC`)
- **Lokasi studi**: Mead, Nebraska, USA
- **Dataset dinamis**: AmeriFlux `US-Ne1`, `US-Ne2`, `US-Ne3`
- **Dataset statis**: WoSIS / kandidat pengganti berbasis spasial
- **Model utama**: `RandomForestRegressor`

## Alur Eksperimen

Repo ini disusun bertahap dari baseline sampai pipeline final:

- [skenario-a-baseline.ipynb](./skenario-a-baseline.ipynb)  
  Baseline single-site berbasis fitur dinamis time-series.

- [skenario-b.ipynb](./skenario-b.ipynb)  
  Menambahkan fitur tanah statis `soil_ph` dan `soil_organic_carbon` pada satu site.

- [skenario-c.ipynb](./skenario-c.ipynb)  
  Multi-site `US-Ne1`, `US-Ne2`, `US-Ne3` dengan fitur inti yang lebih stabil.

- [skenario-d-final.ipynb](./skenario-d-final.ipynb)  
  Pipeline final yang menyatukan dan menyempurnakan skenario sebelumnya.

Dokumentasi pendukung:

- [skenario-a-baseline_assets/skenario-a-baseline.md](./skenario-a-baseline_assets/skenario-a-baseline.md)
- [skenario-b/skenario-b.md](./skenario-b/skenario-b.md)
- [skenario-c/skenario-c.md](./skenario-c/skenario-c.md)
- [catatan/audit_skenario_abc.md](./catatan/audit_skenario_abc.md)

## Hasil Utama

Hasil penting yang sudah diperoleh:

- **Skenario A**: baseline terbaik awal dengan `R² = 0.613`
- **Skenario C**: pendekatan multi-site mencapai `R² = 0.8135`
- **Skenario D Final**: pipeline terbaik saat ini mencapai `R² = 0.8196`
- Skenario C menunjukkan bahwa:
  - dataset yang lebih besar sangat membantu,
  - fitur inti lebih efektif daripada memakai terlalu banyak kolom,
  - variasi antar-site membantu generalisasi model.

## Hasil Final Skenario D

Notebook final [skenario-d-final.ipynb](./skenario-d-final.ipynb) adalah sintesis dan penyempurnaan dari skenario A, B, dan C.

Ringkasan hasil:

- **Model terbaik**: `RandomForestRegressor`
- **Test R²**: `0.8196`
- **MAE**: `1.9923`
- **RMSE**: `4.5414`
- **Kenaikan vs baseline A**: `+0.2066`
- **Site**: `US-Ne1`, `US-Ne2`, `US-Ne3`
- **Jumlah fitur**: `16`

Pembanding model:

- **Random Forest**: `R² = 0.8196`
- **XGBoost**: `R² = 0.8143`

Catatan:

- `Random Forest` menjadi model terbaik pada test set.
- `XGBoost` sudah berhasil dijalankan dengan **GPU (CUDA)**.
- `Random Forest` tetap berjalan di CPU karena implementasi `scikit-learn` tidak mendukung GPU.

Evaluasi per site untuk model terbaik:

- `US-Ne1`: `R² = 0.8365`
- `US-Ne2`: `R² = 0.8156`
- `US-Ne3`: `R² = 0.8009`

Output yang dihasilkan notebook final:

- `output_skenario_d/carbon_flux_model_skenario_d.pkl`
- `output_skenario_d/carbon_flux_model_skenario_d_metadata.json`

## Struktur Folder

```text
.
├── catatan/
├── dataset/
│   ├── AmeriFlux/
│   └── WoSIS (ISRIC)/
├── skenario-a-baseline_assets/
├── skenario-b/
├── skenario-c/
├── skenario-a-baseline.ipynb
├── skenario-b.ipynb
├── skenario-c.ipynb
├── skenario-d-final.ipynb
├── requirements.txt
└── README.md
```

## Dataset

Dataset **tidak ikut di-push ke GitHub** karena:

- ukuran file AmeriFlux sangat besar dan melebihi limit GitHub,
- dataset tetap disimpan lokal di folder `dataset/`,
- `.gitignore` sudah dikonfigurasi untuk mengecualikan dataset.

Struktur dataset lokal yang diharapkan:

```text
dataset/
├── AmeriFlux/
│   ├── AMF_US-Ne1_FLUXNET_2001-2024_v1.3_r1/
│   ├── AMF_US-Ne2_FLUXNET_2001-2024_v1.3_r1/
│   └── AMF_US-Ne3_FLUXNET_2001-2024_v1.3_r1/
└── WoSIS (ISRIC)/
    ├── wosis_latest_PH.csv
    ├── wosis_latest_orgc.csv
    └── link.txt
```

## Setup Environment

Gunakan virtual environment Python lalu install dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Cara Menjalankan

Untuk membuka notebook:

```powershell
jupyter notebook
```

Urutan yang disarankan:

1. Jalankan `skenario-a-baseline.ipynb`
2. Lanjutkan ke `skenario-b.ipynb`
3. Evaluasi multi-site di `skenario-c.ipynb`
4. Gunakan `skenario-d-final.ipynb` sebagai pipeline final

Jika langsung ingin menjalankan pipeline final:

1. Pastikan dataset lokal sudah tersedia di folder `dataset/`
2. Jalankan `skenario-d-final.ipynb`
3. Cek hasil evaluasi, visualisasi, dan file output di `output_skenario_d/`

## Fitur Tanah Statis

Skenario C mendukung input manual fitur tanah per site melalui:

- [skenario-c/manual_site_soil_template.csv](./skenario-c/manual_site_soil_template.csv)
- [skenario-c/build_manual_site_soil.py](./skenario-c/build_manual_site_soil.py)

Catatan:

- file WoSIS lokal yang sekarang tersedia belum memiliki `latitude/longitude`,
- sehingga spatial join otomatis per site belum bisa dilakukan penuh dari file lokal saat ini,
- jika tersedia file WoSIS berkoordinat, script `build_manual_site_soil.py` bisa dipakai untuk membentuk `manual_site_soil.csv`.

## Catatan GitHub

Jika push ke GitHub gagal karena file dataset besar:

- pastikan folder `dataset/` tetap di-ignore,
- jangan commit file CSV AmeriFlux ke repository,
- bila perlu, simpan dataset di storage terpisah dan letakkan link referensinya di dokumentasi.

## Tech Stack

- Python
- Jupyter Notebook
- pandas
- numpy
- scikit-learn
- xgboost
- seaborn
- matplotlib
- joblib
