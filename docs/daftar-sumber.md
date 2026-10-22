# Daftar Sumber Data dan Referensi — INSIGHT

Dokumen ini merangkum seluruh sumber data, perangkat lunak, dan literatur yang digunakan dalam metodologi proyek INSIGHT (Integrated Surface Ignition & Flora Fauna Mapping Hazard Tracker). Setiap entri mencantumkan nama penyedia, URL akses, jenis lisensi/ketentuan, tanggal akses, dan peran data/perangkat tersebut dalam proyek.

Tanggal akses mengacu pada periode pengembangan prototipe (September 2026).

---

## 1. Sumber Data Spasial

### 1.1 OpenStreetMap (OSM)
- **Penyedia:** OpenStreetMap Foundation (kontributor komunitas)
- **URL:** https://www.openstreetmap.org — diekstraksi melalui Overpass API (https://overpass-api.de/) dan antarmuka kueri Overpass Turbo (https://overpass-turbo.eu/); ekstrak wilayah tersedia di Geofabrik Indonesia (https://download.geofabrik.de/asia/indonesia.html)
- **Lisensi:** Open Database License (ODbL) v1.0 — https://www.openstreetmap.org/copyright
- **Tanggal akses:** September 2026
- **Peran dalam proyek:** Sungai/badan air, jalan, permukiman, dan konteks tutupan lahan pada bounding box demo (112,5°–114,5° BT; 1,5°–3,5° LS) di Kalimantan Tengah; fondasi peta dasar aplikasi web serta fitur jarak (jarak ke air/permukiman/jalan) untuk model Machine Learning.

### 1.2 NASA FIRMS (Fire Information for Resource Management System)
- **Penyedia:** NASA / LANCE FIRMS — data MODIS Active Fire (MCD14ML) dan VIIRS S-NPP/NOAA-20 (VNP14IMGT)
- **URL:** https://firms.modaps.eosdis.nasa.gov/ (portal); https://firms.modaps.eosdis.nasa.gov/api/ (API); unduhan CSV melalui NASA FIRMS Export Tool atau NASA Earthdata (https://www.earthdata.nasa.gov/)
- **Lisensi/Ketentuan:** Data ilmu bumi NASA — penggunaan terbuka untuk tujuan riset dan pendidikan dengan atribusi (lihat ketentuan terkini di situs FIRMS)
- **Tanggal akses:** September 2026
- **Peran dalam proyek:** Titik panas (hotspot) aktif sebagai label keberadaan api untuk pelatihan model ML dan titik inisiasi (seeding) simulasi Cellular Automata dari kejadian kebakaran nyata di Kalimantan Tengah.

### 1.3 iNaturalist
- **Penyedia:** iNaturalist — inisiatif bersama California Academy of Sciences dan National Geographic Society
- **URL:** https://www.inaturalist.org; API observasi v2: https://api.inaturalist.org/v2/observations (parameter: taxon_name, bbox, quality_grade=research)
- **Lisensi:** Data observasi dirilis dengan lisensi Creative Commons (CC0/CC-BY/CC-BY-NC, sesuai pengaturan masing-masing pengamat); ketentuan API: https://www.inaturalist.org/pages/api+recommended+practices
- **Tanggal akses:** September 2026
- **Peran dalam proyek:** Observasi research-grade flora dan fauna endemik Kalimantan — Orangutan Kalimantan (*Pongo pygmaeus*), Bekantan (*Nasalis larvatus*), *Rafflesia arnoldii*, dan kantong semar (*Nepenthes* spp.) — sebagai layer spasial keanekaragaman hayati yang ditumpangkan dengan jalur potensi kebakaran.

### 1.4 Konteks Gambut dan Hidrologi
- **Penyedia:** Wetlands International dan peta gambut global publik (ketersediaan untuk Kalimantan bervariasi); konteks hidrologi alternatif dari OSM
- **URL:** https://www.wetlands.org
- **Lisensi:** Bervariasi per dataset; dikonsultasikan ke penyedia masing-masing
- **Tanggal akses:** September 2026
- **Peran dalam proyek:** Penanda risiko gambut (peat_risk flag) dan narasi ekosistem Hutan Gambut Sebangau–Kahayan; flag gambut didefinisikan secara sederhana berbasis tutupan lahan OSM karena ketersediaan raster gambut publik yang konsisten masih terbatas.

---

## 2. Perangkat Lunak dan Pustaka

| Pustaka | Lisensi | Peran |
|---|---|---|
| Python 3.10+ | PSF License | Bahasa utama proyek |
| NumPy | BSD | Operasi array grid CA dan perhitungan numerik |
| Pandas | BSD | Pengolahan tabular data hotspot dan fitur ML |
| GeoPandas / Shapely | BSD | Analisis geometri spasial (jarak, titik-dalam-poligon) |
| scikit-learn | BSD | Random Forest untuk klasifikasi risiko kebakaran |
| Streamlit | Apache 2.0 | Antarmuka aplikasi web interaktif |
| Folium / streamlit-folium | MIT | Peta interaktif dengan pembatasan zoom (max_bounds) |
| Matplotlib / Seaborn | BSD | Grafik distribusi status CA dan visualisasi |

---

## 3. Referensi Ilmiah (Daftar Pustaka)

Referensi berikut identik dengan DAFTAR PUSTAKA pada Extended Abstract INSIGHT:

1. D. Kurniawan and A. Prasetyo, "Machine learning approach for dynamic weight estimation in fire spread models," in *Proc. International Conference on Computer Science and Environment*, pp. 102–108, 2024.
2. Badan Meteorologi, Klimatologi, dan Geofisika (BMKG), *Analisis sebaran titik panas dan iklim kebakaran hutan di Indonesia*, BMKG Indonesia, https://www.bmkg.go.id/karhutla, (diakses 15 Agustus 2025).
3. M. R. Cochrane, "Fire science for rainforests," *Nature*, vol. 421, no. 6926, pp. 913–919, 2003.
4. B. H. Saharjo, *Kebakaran Hutan dan Lahan Gambut di Indonesia: Dampak dan Penanggulangannya*, IPB Press, Bogor, pp. 45–60, 2018.
5. A. Y. Widiyatno, F. X. Suryadi, and R. W. Putra, "Web-based cellular automata for spatial fire spread prediction in tropical peatlands," *Journal of Environmental Informatics*, vol. 35, no. 2, pp. 115–128, 2022.
6. C. J. Bradshaw, R. A. Sodhi, and L. W. Brooker, "The devastating ecological footprint of Southeast Asian peatland fires and the threat to endemic fauna," *Biological Conservation*, vol. 169, pp. 312–320, 2014.
7. T. K. Le, V. D. Nguyen, and S. H. Tran, "Optimizing dynamic fire propagation parameters using machine learning models in web GIS platforms," *Computers, Environment and Urban Systems*, vol. 98, p. 101875, 2023.

---

## 4. Dokumentasi Teknis

- **Overpass API documentation** — https://wiki.openstreetmap.org/wiki/Overpass_API
- **NASA FIRMS API documentation** — https://firms.modaps.eosdis.nasa.gov/api/
- **iNaturalist API documentation** — https://api.inaturalist.org/v1/docs/
- **Streamlit documentation** — https://docs.streamlit.io
- **Folium documentation** — https://python-visualization.github.io/folium/
- **scikit-learn documentation (RandomForestClassifier)** — https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html

---

## 5. Catatan Penggunaan

- Seluruh sumber data digunakan dalam batasan lisensinya masing-masing, dengan atribusi yang sesuai.
- Data demo berskala ilmiah-pelajar; hasil simulasi bersifat ilustratif dan bukan produk operasional penanggulangan bencana.
- Fixture cadangan offline (stub) di repositori (`src/bio_stub_fixture.json`, `src/osm_stub.py`, `src/fire_data_stub.py`) hanya meniru struktur data API di atas dan tidak menggantikan data asli.
