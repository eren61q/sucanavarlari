import xarray as xr
import pandas as pd
import glob
import os

dosyalar = sorted(glob.glob('era5_veri/data_stream-moda_stepType-avgad.nc'))
print(f"Bulunan dosya: {len(dosyalar)}")

# Tek dosya var — direkt oku
ds = xr.open_dataset('era5_veri/data_stream-moda_stepType-avgad.nc', engine='netcdf4')
print("\nDeğişkenler:", list(ds.data_vars))
print("Koordinatlar:", list(ds.coords))
print("Boyutlar:", dict(ds.dims))
print("\nİlk kayıt:", ds)