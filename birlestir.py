import xarray as xr
import pandas as pd
import glob

print("Dosyalar birleştiriliyor...")

# avgua = sıcaklık (t2m), avgad = yağış (tp) + buharlaşma (pev)
avgua_dosyalar = sorted(glob.glob('era5_veri/era5_*_avgua.nc'))
avgad_dosyalar = sorted(glob.glob('era5_veri/era5_*_avgad.nc'))

print(f"avgua (sıcaklık) dosyası: {len(avgua_dosyalar)}")
print(f"avgad (yağış) dosyası: {len(avgad_dosyalar)}")

# Birleştir
ds_ua = xr.open_mfdataset(avgua_dosyalar, combine='by_coords', engine='netcdf4')
ds_ad = xr.open_mfdataset(avgad_dosyalar, combine='by_coords', engine='netcdf4')

print("\nSıcaklık değişkenleri:", list(ds_ua.data_vars))
print("Yağış değişkenleri:", list(ds_ad.data_vars))

# Konya merkezi (37.87N, 32.49E) için en yakın nokta
lat, lon = 37.87, 32.49

df_ua = ds_ua.sel(latitude=lat, longitude=lon, method='nearest').to_dataframe().reset_index()
df_ad = ds_ad.sel(latitude=lat, longitude=lon, method='nearest').to_dataframe().reset_index()

# Tarih sütununu düzenle
df_ua['tarih'] = pd.to_datetime(df_ua['valid_time']).dt.to_period('M').dt.to_timestamp()
df_ad['tarih'] = pd.to_datetime(df_ad['valid_time']).dt.to_period('M').dt.to_timestamp()

# Birleştir
df_ua = df_ua[['tarih'] + [c for c in df_ua.columns if c not in ['tarih','valid_time','latitude','longitude','number','expver']]]
df_ad = df_ad[['tarih'] + [c for c in df_ad.columns if c not in ['tarih','valid_time','latitude','longitude','number','expver']]]

df = pd.merge(df_ua, df_ad, on='tarih', how='outer').sort_values('tarih').reset_index(drop=True)

# Birim dönüşümleri
if 't2m' in df.columns:
    df['sicaklik_c'] = df['t2m'] - 273.15
if 'tp' in df.columns:
    df['yagis_mm'] = df['tp'] * 1000
if 'pev' in df.columns:
    df['buharlaşma_mm'] = df['pev'].abs() * 1000

# Temiz sütunlar
tutulacak = ['tarih', 'sicaklik_c', 'yagis_mm', 'buharlaşma_mm']
df_temiz = df[[c for c in tutulacak if c in df.columns]]

print(f"\nToplam kayıt: {len(df_temiz)}")
print(f"Tarih aralığı: {df_temiz['tarih'].min()} → {df_temiz['tarih'].max()}")
print("\nİlk 5 satır:")
print(df_temiz.head().to_string(index=False))
print("\nİstatistikler:")
print(df_temiz.describe().round(2).to_string())

df_temiz.to_csv('era5_veri/konya_era5_1940_2024.csv', index=False, encoding='utf-8-sig')
print("\nKaydedildi: era5_veri/konya_era5_1940_2024.csv")