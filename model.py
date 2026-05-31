"""
AgriCast — Gerçek ERA5 Verisiyle Model Eğitimi
Konya Kapalı Havzası · 1940–2024
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
warnings.filterwarnings("ignore")

# ── 1. VERİ YÜKLEMESİ ──
print("=" * 50)
print("AgriCast — ERA5 Verisiyle Model Eğitimi")
print("=" * 50)

df = pd.read_csv('era5_veri/konya_era5_1940_2024.csv', parse_dates=['tarih'])
print(f"\nVeri yüklendi: {len(df)} kayıt")

# ── 2. ÖZELLİK MÜHENDİSLİĞİ ──
df = df.sort_values('tarih').reset_index(drop=True)
df['ay'] = df['tarih'].dt.month
df['yil'] = df['tarih'].dt.year

# Lag özellikler (geçmiş aylar)
for lag in [1, 2, 3, 6, 12]:
    df[f'sicaklik_lag{lag}'] = df['sicaklik_c'].shift(lag)
    df[f'yagis_lag{lag}']    = df['yagis_mm'].shift(lag)

# Kümülatif yağış (3 ve 6 aylık)
df['yagis_3ay'] = df['yagis_mm'].rolling(3).sum()
df['yagis_6ay'] = df['yagis_mm'].rolling(6).sum()

# Sıcaklık anomalisi (aylık ortalamadan sapma)
aylik_ort = df.groupby('ay')['sicaklik_c'].transform('mean')
df['sicaklik_anomali'] = df['sicaklik_c'] - aylik_ort

# Buharlaşma-yağış dengesi
df['su_dengesi'] = df['yagis_mm'] - df['buharlaşma_mm']
df['su_dengesi_3ay'] = df['su_dengesi'].rolling(3).sum()

df = df.dropna().reset_index(drop=True)
print(f"Özellik mühendisliği sonrası: {len(df)} kayıt")

# ── 3. HEDEF DEĞİŞKEN ──
# Gerçek yeraltı su seviyesi verisi gelene kadar:
# Su dengesi kümülatifi → yeraltı su proxy'si
df['yeraltisu_proxy'] = df['su_dengesi_3ay']

feature_cols = [
    'sicaklik_c', 'yagis_mm', 'buharlaşma_mm',
    'sicaklik_anomali', 'su_dengesi',
    'yagis_3ay', 'yagis_6ay',
    'sicaklik_lag1', 'sicaklik_lag3', 'sicaklik_lag12',
    'yagis_lag1', 'yagis_lag3', 'yagis_lag12',
    'ay', 'yil'
]

X = df[feature_cols]
y = df['yeraltisu_proxy']

# ── 4. MODEL EĞİTİMİ ──
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False  # zaman serisi — karıştırma yok
)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

print("\nModel eğitiliyor...")
model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    random_state=42
)
model.fit(X_train_s, y_train)

# ── 5. PERFORMANS ──
y_pred = model.predict(X_test_s)
mae = mean_absolute_error(y_test, y_pred)
r2  = r2_score(y_test, y_pred)

print(f"\nModel Performansı:")
print(f"  MAE : {mae:.3f}")
print(f"  R²  : {r2:.3f}")

# ── 6. SHAP — EN ETKİLİ FAKTÖRLER ──
try:
    import shap
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test_s)
    mean_abs    = np.abs(shap_values).mean(axis=0)
    shap_df = pd.DataFrame({
        'ozellik': feature_cols,
        'etki'   : mean_abs
    }).sort_values('etki', ascending=False)

    print("\nEn etkili faktörler (SHAP):")
    for _, row in shap_df.head(8).iterrows():
        bar = "█" * int(row['etki'] / mean_abs.max() * 20)
        print(f"  {row['ozellik']:25s} {bar}")
except ImportError:
    print("\nSHAP için: python -m pip install shap --user")

# ── 7. 6 AYLIK TAHMİN ──
print("\nÖnümüzdeki 6 ay su dengesi tahmini:")
son = df.iloc[-1].copy()
for i in range(1, 7):
    ay = (int(son['ay']) % 12) + 1
    yil = int(son['yil']) + (1 if ay == 1 else 0)
    X_pred = pd.DataFrame([{c: son.get(c, 0) for c in feature_cols}])
    X_pred['ay'] = ay
    X_pred['yil'] = yil
    tahmin = model.predict(scaler.transform(X_pred))[0]
    print(f"  {yil}-{ay:02d}  →  su dengesi proxy: {tahmin:+.1f}")
    son['ay'] = ay
    son['yil'] = yil

print("\n" + "=" * 50)
print("ERA5 verisi başarıyla modele entegre edildi!")
print("Sonraki adım: DSİ kuyu verisi ile yeraltı su seviyesi hedefi")
print("=" * 50)