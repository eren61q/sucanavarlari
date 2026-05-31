import zipfile, glob, os

zip_dosyalari = sorted(glob.glob('era5_veri/*.nc.bak'))
print(f"{len(zip_dosyalari)} zip dosyasi bulundu")

for zip_path in zip_dosyalari:
    yil = zip_path.replace('era5_veri\\era5_', '').replace('.nc.bak', '')
    print(f"\nAciliyor: {zip_path} ({yil})")
    with zipfile.ZipFile(zip_path, 'r') as z:
        for dosya_adi in z.namelist():
            tip = 'avgua' if 'avgua' in dosya_adi else 'avgad'
            yeni_ad = f'era5_veri/era5_{yil}_{tip}.nc'
            with z.open(dosya_adi) as kaynak:
                with open(yeni_ad, 'wb') as hedef:
                    hedef.write(kaynak.read())
            print(f"  Kaydedildi: {yeni_ad}")

print("\nBitti!")