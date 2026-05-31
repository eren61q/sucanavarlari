"""
AgriCast — GRACE-FO Yeraltı Su Anomalisi İndirme
Konya Kapalı Havzası · 2002–2024
NASA Earthdata · JPL Mascon RL06
"""

import requests
import netCDF4 as nc
import numpy as np
import pandas as pd
import os
from getpass import getpass

# ── AYARLAR ──
CIKTI_KLASOR = "grace_veri"
os.makedirs(CIKTI_KLASOR, exist_ok=True)

# Konya merkezi
LAT = 37.87
LON = 32.49

# ── NASA Earthdata GİRİŞ ──
print("=" * 50)
print("AgriCast — GRACE-FO Yeraltı Su Anomalisi")
print("=" * 50)
print("\nNASA Earthdata bilgilerinizi girin:")
kullanici = input("Kullanıcı adı: ")
sifre     = getpass("Şifre: ")

# ── GRACE MASCON VERİSİ ──
# JPL RL06.1 Mascon — aylık, 0.5° çözünürlük, 2002-2024
URL = (
    "https://opendap.earthdata.nasa.gov/providers/POCLOUD/collections/"
    "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.1_V3/granules/"
    "GRCTellus.JPL.200204_202401.GLO.RL06.1M.MSCNv03CRI"
)

print("\nGRACE-FO verisi indiriliyor...")
print("(Bu işlem birkaç dakika sürebilir)")

try:
    r = requests.get(
        URL + ".nc",
        auth=(kullanici, sifre),
        timeout=120,
        stream=True
    )

    if r.status_code == 200:
        dosya_yolu = f"{CIKTI_KLASOR}/grace_global.nc"
        with open(dosya_yolu, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"İndirildi: {dosya_yolu}")
    else:
        print(f"Hata: {r.status_code} — {r.text[:200]}")
        print("\nAlternatif yöntem deneniyor...")
        raise Exception("HTTP hata")

except Exception as e:
    print(f"\nDirekt indirme başarısız: {e}")
    print("Manuel indirme talimatları:")
    print("1. https://podaac.jpl.nasa.gov/dataset/TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.1_V3")
    print("2. 'Download' butonuna tıklayın")
    print("3. İndirilen .nc dosyasını grace_veri/ klasörüne koyun")
    print("4. Bu scripti tekrar çalıştırın")
    exit()

# ── VERİYİ İŞLE ──
print("\nVeri işleniyor...")

ds = nc.Dataset(dosya_yolu)
print("Değişkenler:", list(ds.variables.keys()))

# Koordinatlar
latlar = ds.variables['lat'][:]
lonlar = ds.variables['lon'][:]
zamanlar = ds.variables['time'][:]

# Konya'ya en yakın grid noktası
lat_idx = np.argmin(np.abs(latlar - LAT))
lon_idx = np.argmin(np.abs(lonlar - LON))
print(f"Konya grid noktası: {latlar[lat_idx]:.2f}°N, {lonlar[lon_idx]:.2f}°E")

# Yeraltı suyu eşdeğer su yüksekliği (cm)
lwe = ds.variables['lwe_thickness']  # liquid water equivalent
konya_lwe = lwe[:, lat_idx, lon_idx]

# Zaman → tarih
zaman_birimi = ds.variables['time'].units
zaman_takvim = getattr(ds.variables['time'], 'calendar', 'standard')
tarihler = nc.num2date(zamanlar, zaman_birimi, zaman_takvim)
tarihler_pd = pd.to_datetime([str(t) for t in tarihler])

# DataFrame oluştur
df = pd.DataFrame({
    'tarih': tarihler_pd,
    'yeraltisu_anomali_cm': np.array(konya_lwe),
})

# Eksik değerleri temizle (GRACE ölçüm boşlukları olabilir)
df = df[df['yeraltisu_anomali_cm'] < 1e10].copy()
df = df.sort_values('tarih').reset_index(drop=True)

# ── ÖZET ──
print(f"\nToplam kayıt  : {len(df)}")
print(f"Tarih aralığı : {df['tarih'].min()} → {df['tarih'].max()}")
print(f"\nİlk 5 satır:")
print(df.head().to_string(index=False))
print(f"\nİstatistikler:")
print(df['yeraltisu_anomali_cm'].describe().round(3).to_string())

# ── KAYDET ──
csv_yolu = f"{CIKTI_KLASOR}/konya_grace_2002_2024.csv"
df.to_csv(csv_yolu, index=False, encoding='utf-8-sig')
print(f"\nKaydedildi: {csv_yolu}")

print("\n" + "=" * 50)
print("GRACE-FO verisi hazır!")
print("Sonraki adım: ERA5 + GRACE birleştirme ve model eğitimi")
print("=" * 50)

ds.close()