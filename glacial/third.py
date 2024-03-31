import rasterio
from rasterio.mask import mask
from shapely.geometry import shape
import fiona
import os
import numpy as np
import re
import matplotlib as mpl
import matplotlib.pyplot as plt

wd = "D:/4.LS/MEDPZ/semestralka/final/3+"
rootdir = wd + "/snimek"

source = []
for subdir, dirs, files in os.walk(rootdir):
    for file in files:
        if(os.path.join(subdir, file).endswith("B03_20m.jp2") or os.path.join(subdir, file).endswith("B11_20m.jp2")):
            source.append(os.path.join(subdir, file))

unique_dates = []
sorted_source = []

# projdi každý prvek v source
for item in source:
    # najdi datum v řetězci pomocí regulárního výrazu
    match = re.search(r'S2A_[A-Za-z\d]+_(\d+)T', item)
    if match:
        date = match.group(1)
        # pokud je datum unikátní, přidej ho do unique_dates
        if date not in unique_dates:
            unique_dates.append(date)
            # přidej item do sorted_source
            sorted_source.append(item)

#print(sorted_source)

with fiona.open(wd + "/aoi/aoiled.geojson", "r") as shapefile:
    geometry = shapefile[0]["geometry"]
    input_polygon = shape(geometry)

out_image = []
out_transform = []
out_meta = []
rozloha = []

for i in range(len(source)):
    with rasterio.open(source[i]) as src:
        # Oříznutí rastrového souboru na základě vstupního polygonu
        oi, ot = mask(src, [input_polygon], crop=True)
        out_image.append(oi)
        out_transform.append(ot)
        # Získání metadat rastrového souboru
        om = src.meta.copy()
        out_meta.append(om)

    # Aktualizace metadat oříznutého rastrového souboru
    out_meta[i].update({"driver": "GTiff",
                    "height": out_image[i].shape[1],
                    "width": out_image[i].shape[2],
                    "transform": out_transform[i],
                    "dtype": "float32"
                    })
    out_image[i] = out_image[i].astype('float32')

for i in range(len(source)//2):
    ndsi = (out_image[i*2] - out_image[i*2+1]) / (out_image[i*2] + out_image[i*2+1])
    #Reklasifikace todo - Zjistit tresholdy
    """ ndsi[(ndsi >= 0.3) & (ndsi <= 0.6)] = 1.0
    ndsi[(ndsi < 0.3) & (ndsi > 0.6)] = 0.0 """

    """ ndsi[(ndsi > 0.6)] = 0.0
    ndsi[(ndsi >= 0.3) & (ndsi <= 0.6)] = 1.0
    ndsi[(ndsi < 0.3)] = 0.0 """

    ndsi[(ndsi > 0.5)] = 1.0
    ndsi[(ndsi <= 0.5)] = 0.0

    # vypocet rozlohy ladovca: zrata sa pocet pixelov, ktore boli klasifikovane ako ladovec
    # ich pocet sa vynasobi velkostou jedneho pixela a kedze pouzivame pasmo s priestorovym rozlisenim 20 m, tak velkost pixela je 20x20=400 m2
    # nakoniec sa vysledok vydeli 1 milionom a dostaneme rozlohu v km2
    ledovecpix = np.sum(ndsi == 1.0)
    rozloha.append((ledovecpix*400)/1000000)
    datum = unique_dates[i]
    print(f"rozloha ľadovca dňa {datum[6:] + '.' + datum[4:6] + '.' + datum[:4]}: {rozloha[i]} km²")

    # Uložení vypočteného NDSI jako rastrový soubor
    with rasterio.open(wd + f'/ndsi{unique_dates[i]}.tif', 'w', **out_meta[i*2+1]) as dst:
        dst.write(ndsi)

    
#Rozdil prvni minus posledni
rozdiel = rozloha[0]-rozloha[len(rozloha)-1]
if rozdiel > 0:
    print(f"ľadovec sa zmenšil o {rozdiel} km²")
elif rozdiel < 0:
    print(f"ľadovec sa zväčšil o {abs(rozdiel)} km²")
else:
    print("ľadovec ostal rovnaký")

# Příklad data (roky a hodnoty)
roky = []
hodnoty = []
for i in range (len(unique_dates)):
    roky.append(unique_dates[i])
    hodnoty.append(rozloha[i])

plt.plot(roky, hodnoty, '-o', color='blue', linewidth=2, markersize=8)

# Nastavení popisků os a velikosti písma
plt.xlabel('Roky', fontsize=12)
plt.ylabel('Rozloha [km²]', fontsize=12)

# Přidání nadpisu
plt.title('Vývoj rozlohy ledovce', fontsize=14)


# Přidání mřížky
plt.grid(alpha=0.2)

# Zobrazení grafu
plt.show()