
import cdsapi
import xarray as xr
import pandas as pd
import numpy as np
import os

# ─────────────────────────────────────────────
# KONYA KAPALI HAVZASI koordinatları
# Kuzey, Batı, Güney, Doğu
# ─────────────────────────────────────────────
BBOX = [39.5, 31.5, 37.0, 34.5]  # [N, W, S, E]

CIKTI_KLASOR = "era5_veri"
os.makedirs(CIKTI_KLASOR, exist_ok=True)


# ─────────────────────────────────────────────
# 1. ERA5 İNDİRME — yıllık gruplar halinde
#    (tek seferde 1940-2024 istemek zaman aşımına uğrayabilir)
# ─────────────────────────────────────────────

def era5_indir(yil_baslangic=1940, yil_bitis=2024):
    c = cdsapi.Client()

    # 10'ar yıllık gruplar halinde indir
    gruplar = list(range(yil_baslangic, yil_bitis + 1, 10))
    if gruplar[-1] != yil_bitis:
        gruplar.append(yil_bitis + 1)

    dosyalar = []

    for i in range(len(gruplar) - 1):
        baslangic = gruplar[i]
        bitis = gruplar[i + 1] - 1
        yillar = [str(y) for y in range(baslangic, bitis + 1)]

        dosya_adi = f"{CIKTI_KLASOR}/era5_{baslangic}_{bitis}.nc"

        if os.path.exists(dosya_adi):
            print(f"  [{baslangic}-{bitis}] zaten mevcut, atlanıyor...")
            dosyalar.append(dosya_adi)
            continue

        print(f"  [{baslangic}-{bitis}] indiriliyor... (birkaç dakika sürebilir)")

        c.retrieve(
            "reanalysis-era5-single-levels-monthly-means",
            {
                "product_type": "monthly_averaged_reanalysis",
                "variable": [
                    "2m_temperature",           # Hava sıcaklığı
                    "total_precipitation",       # Toplam yağış
                    "2m_dewpoint_temperature",   # Çiğ noktası (nem için)
                    "potential_evaporation",     # Potansiyel buharlaşma
                    "soil_temperature_level_1",  # Toprak sıcaklığı
                ],
                "year": yillar,
                "month": [f"{m:02d}" for m in range(1, 13)],
                "time": "00:00",
                "area": BBOX,
                "format": "netcdf",
            },
            dosya_adi,
        )
        dosyalar.append(dosya_adi)
        print(f"  [{baslangic}-{bitis}] indirildi ✓")

    return dosyalar


# ─────────────────────────────────────────────
# 2. NetCDF → Pandas DataFrame dönüşümü
# ─────────────────────────────────────────────

def netcdf_isle(dosyalar):
    print("\nDosyalar işleniyor...")
    datasets = []

    for dosya in dosyalar:
        ds = xr.open_dataset(dosya, engine='netcdf4')

        # Konya merkezi için en yakın grid noktası (37.87°N, 32.49°E)
        ds_konya = ds.sel(
            latitude=37.87,
            longitude=32.49,
            method="nearest"
        )

        df = ds_konya.to_dataframe().reset_index()
        datasets.append(df)

    df_full = pd.concat(datasets, ignore_index=True)

    # Sütun isimlerini düzenle
    kolon_map = {
        "t2m": "sicaklik_k",          # Kelvin
        "tp": "yagis_m",              # Metre (aylık toplam)
        "d2m": "cignoktasi_k",        # Kelvin
        "pev": "buharlaşma_m",        # Metre
        "stl1": "toprak_sicaklik_k",  # Kelvin
    }
    df_full = df_full.rename(columns={k: v for k, v in kolon_map.items() if k in df_full.columns})

    # Kelvin → Celsius
    for col in ["sicaklik_k", "cignoktasi_k", "toprak_sicaklik_k"]:
        if col in df_full.columns:
            yeni_col = col.replace("_k", "_c")
            df_full[yeni_col] = df_full[col] - 273.15

    # Yağış: metre → mm
    if "yagis_m" in df_full.columns:
        df_full["yagis_mm"] = df_full["yagis_m"] * 1000

    # Tarih sütunu
    if "time" in df_full.columns:
        df_full["tarih"] = pd.to_datetime(df_full["time"])
        df_full = df_full.sort_values("tarih").reset_index(drop=True)

    # Kullanılacak sütunları seç
    tutulacak = ["tarih", "sicaklik_c", "yagis_mm", "cignoktasi_c",
                 "toprak_sicaklik_c", "buharlaşma_m"]
    mevcut = [c for c in tutulacak if c in df_full.columns]
    df_temiz = df_full[mevcut].copy()

    return df_temiz


# ─────────────────────────────────────────────
# 3. KAYDET ve ÖN BAKILAR
# ─────────────────────────────────────────────

def kaydet_ve_ozet(df):
    csv_yolu = f"{CIKTI_KLASOR}/konya_era5_1940_2024.csv"
    df.to_csv(csv_yolu, index=False, encoding="utf-8-sig")
    print(f"\nKaydedildi: {csv_yolu}")

    print("\n─── Veri Özeti ───")
    print(f"Toplam kayıt  : {len(df)}")
    print(f"Tarih aralığı : {df['tarih'].min()} → {df['tarih'].max()}")
    print(f"\nİlk 5 satır:")
    print(df.head().to_string(index=False))

    print("\n─── İstatistikler ───")
    print(df.describe().round(2).to_string())

    return csv_yolu


# ─────────────────────────────────────────────
# 4. ANA AKIŞ
# ─────────────────────────────────────────────

def main():
    print("=" * 50)
    print("AgriCast — ERA5 Veri İndirme")
    print("Konya Kapalı Havzası · 1940–2024")
    print("=" * 50)

    print("\n[1/3] ERA5'ten indiriliyor...")
    dosyalar = era5_indir(yil_baslangic=1940, yil_bitis=2024)

    print("\n[2/3] Veriler işleniyor...")
    df = netcdf_isle(dosyalar)

    print("\n[3/3] Kaydediliyor...")
    csv_yolu = kaydet_ve_ozet(df)

    print("\n" + "=" * 50)
    print(f"Tamamlandı! Veri hazır: {csv_yolu}")
    print("Sonraki adım: bu veriyi agricast_layer1.py'ye bağlayın")
    print("=" * 50)


if __name__ == "__main__":
    main()