import zipfile, os, glob

for zip_path in glob.glob('era5_veri/*.nc'):
    print('Aciliyor:', zip_path)
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            print('  Icerik:', z.namelist())
            z.extractall('era5_veri/')
        os.rename(zip_path, zip_path + '.bak')
        print('  Tamamlandi')
    except Exception as e:
        print('  Hata:', e)

print('Bitti! era5_veri klasorunu kontrol edin.')