# Daftar Koreksi Naskah INSIGHT

Berkas hasil: `docs/paper/INSIGHT-naskah-revisi.md` (versi Word: `docs/paper/INSIGHT-naskah-revisi.docx`).

Setiap koreksi di bawah ini dapat ditelusuri ke kode proyek. Nomor mengacu pada urutan kemunculan di naskah lama.

---

## A. Kesalahan editorial

| No | Lokasi | Teks lama | Masalah | Perbaikan |
| --- | --- | --- | --- | --- |
| A1 | Judul | "...Machine Learning Berpenjelas Pemetaan Flora-Fauna Endemik" | Frasa tidak gramatikal | "...Machine Learning Berpenjelas **untuk** Pemetaan Flora-Fauna Endemik" |
| A2 | Halaman judul | "Tanggal: masukan tanggal penyelesaian" | Placeholder template | Diisi "21 Oktober 2026" — ganti sesuai tanggal submit |
| A3 | Abstrak | "Celular Automata" | Salah ejaan | "Cellular Automata" |
| A4 | Kata kunci | "Celular Automata" | Salah ejaan | "Cellular Automata" |
| A5 | Bab 2 | "Jarak kiai (grid spacing)" | Salah ketik | "Jarak kisi (grid spacing)" |
| A6 | Bab 2 | "Pembatas wilayah (bounding box)" | Pilihan kata | "Batas wilayah (bounding box)" |
| A7 | Bab 2 | "Rule Transisi CA" | Istilah asing tidak konsisten | "Aturan transisi CA" |
| A8 | Bab 2 | Daftar 1–8 lalu diulang sebagai daftar 3–12 | Duplikasi isi | Duplikat dihapus; isi digabung menjadi subbab 2.1–2.8 |
| A9 | Bab 12 | "METODELOGI" dan penomoran 12–16 | Salah ejaan dan penomoran melompat dari 2 | Menjadi Bab 3 METODOLOGI, 4 HASIL, 5 KESIMPULAN, 6 DAFTAR PUSTAKA, 7 LAMPIRAN |
| A10 | Bab 12.2 | "Design (Perancangan)" | Tidak konsisten bahasa | "Desain" |
| A11 | Bab 12.1 | Daftar alat: ESP32, DHT22, BH1750, panel surya, MATLAB, COMSOL, Arduino IDE | Alat tidak dipakai proyek | Diganti tabel perangkat lunak yang benar-benar dipakai |
| A12 | Bab 12.2–13 | "Jelaskan metode...", "Subbab ini menjelaskan...", "Apabila proyek memerlukan alat..." | Instruksi template masih tertinggal | Dihapus dan diganti isi sebenarnya |
| A13 | Tabel 2 (lama) | Caption "Spesifikasi sumber data dan fungsinya" untuk tabel komponen perangkat lunak | Caption salah/duplikat | Caption tabel komponen diperbaiki menjadi Tabel 1 |
| A14 | Daftar Pustaka | Referensi contoh Wijaya/Riyanto/Majerski/Nurdin | Palsu, hanya contoh template | Diganti 11 rujukan nyata dan dapat diverifikasi |
| A15 | Lampiran anggaran | Baris "xxx" dan contoh sensor | Placeholder | Diganti pernyataan tanpa pengadaan, total Rp 0 |
| A16 | Lampiran | Tidak ada pembagian tugas | Template meminta | Ditambahkan tabel pembagian tugas |

---

## B. Ketidaksesuaian antara naskah dan kode

### B1. Arah angin (kesalahan konsep fisis)

Naskah menyatakan W = 1 untuk tetangga **searah hembusan angin**, dan angin mengikuti konvensi meteorologi (0° = angin **dari** utara). Kode lama membandingkan arah langkah langsung dengan `wind_dir_deg`, sehingga W = 1 justru untuk tetangga **berlawanan arah hembusan**.

- Kode: `src/ca.py`, fungsi `wind_alignment_factor`.
- Perbaikan: arah rambat dihitung sebagai `(wind_dir_deg + 180) % 360`, baru dibandingkan dengan bearing langkah.
- Dampak: seluruh hasil sensitivitas angin pada naskah lama tidak sahih; naskah baru memakai hasil setelah perbaikan.
- Pengujian: `test_wind_alignment_factor_directionality` diperbarui (angin 0° → sel selatan bernilai 1, sel utara 0; tegak lurus 0,5) dan `test_spread_probability_matches_documented_range` ditambahkan untuk memastikan batas 0,15 dan 0,60.

### B2. Konvensi baris grid terbalik

Naskah menyatakan "indeks baris bertambah ke selatan". Kode lama memetakan `row = (lat - min_lat) / spacing`, sehingga baris 0 justru berada di **selatan**, sementara modul mitigasi dan rumus bearing CA menganggap baris 0 di utara. Akibatnya hotspot FIRMS dan lokasi pengguna bisa masuk ke sel yang tercermin secara vertikal.

- Kode: `src/fire_data.py` (`cell_bounds`, `lon_lat_to_row_col`, `row_col_to_center`), `app/main.py` (overlay peta risiko), `src/ml.py` (peta risiko Kalimantan).
- Perbaikan: baris 0 = tepi utara di semua modul; rumus bearing CA kini konsisten.
- Pengujian: `test_cell_grid_rows_run_north_to_south` ditambahkan (baris utara lebih tinggi lintangnya, pemetaan pusat sel bolak-balik konsisten, batas sel utara > selatan).

### B3. Klaim "ML membenihkan CA"

Naskah lama: "output r(cell) digunakan untuk membenihkan CA dengan sel BURNING". Kode tidak melakukan ini: `ca_simulator.initialize_simulation` membenihkan dari hotspot FIRMS (`seed_from_hotspots`), dan bila tidak ada hotspot memakai satu sel pusat. Peta risiko dipakai untuk tampilan dan prioritas mitigasi.

- Perbaikan naskah: bagian 2.5 menjelaskan alur yang sebenarnya, dan klaim kebaruan tidak lagi menyebut pembenihan oleh ML.

### B4. Fitur ML tidak sesuai

Naskah lama menyebut "jarak ke titik panas terdekat", "jarak ke jalan", dan "jenis penutup lahan" sebagai fitur. Kode memakai 13 kolom: `cell_row`, `cell_col`, jarak ke air, jarak ke permukiman, jarak ke titik panas hari sebelumnya, penanda gambut, keberadaan hotspot 1/3/7 hari, jumlah hotspot 7 hari, keselarasan angin, serta `lon`/`lat` yang hanya dipakai untuk pemetaan (11 fitur efektif). Jalan dan penutup lahan diambil dari OSM tetapi tidak dipakai sebagai fitur.

- Perbaikan naskah: daftar fitur ditulis persis seperti `FEATURE_NAMES` di `src/features.py`.

### B5. Hyperparameter dan metrik ML tidak disebut

Naskah lama tidak menyebut konfigurasi model. Ditambahkan: 200 pohon, `max_depth=8`, tanpa pembobotan kelas, `random_state=42`, pembagian **temporal** (6 hari latih, 2 hari uji terakhir), metrik akurasi/presisi/recall/ROC-AUC/PR-AUC — sesuai `src/config.py` dan `src/ml.py`.

Pembagian acak per baris sempat dipakai dan menaikkan metrik secara palsu: sel yang sama muncul di sisi latih dan uji, sementara sebagian sel terbakar berulang. Selain itu, fitur riwayat titik panas semula ikut membaca hari label itu sendiri (kebocoran label), sehingga `has_hotspot_last_1_day` = 1 pada hari kebakaran itu sendiri. Keduanya diperbaiki di `src/features.py` (`hotspot_history_for_cell`, `recent_hotspot_arrays`) dan dikunci oleh `tests/test_ml_wiring.py`. Angka 4.2 butir d adalah hasil setelah perbaikan.

### B6. "GPS pengguna"

Naskah lama: "Popup difilter berdasarkan posisi GPS pengguna". Aplikasi tidak memakai GPS; pengguna mengetik lintang/bujur manual dan koordinat di luar kotak demo ditolak (`src/mitigation.py: loc_to_cell`).

- Perbaikan naskah: dijelaskan input manual, dan keterbatasan "tanpa GPS" dicantumkan.

### B7. Aturan air pada CA

Naskah lama menyatakan sel air "dikecualikan sepenuhnya dari permukaan yang dapat terbakar". Kode hanya memakai air sebagai fitur jarak dan mengeluarkannya dari daftar area pedesaan; CA tetap dapat menyulut sel air.

- Perbaikan naskah: aturan 4 diganti menjadi batas domain, dan keterbatasan "air belum menjadi penghalang api" dicantumkan secara eksplisit.

### B8. Hukum Stefan–Boltzmann

Naskah lama menyiratkan model "memodelkan radiasi melalui Hukum Stefan–Boltzmann". Kode tidak menghitung σT⁴; suku radiasi diringkas menjadi probabilitas dasar konstan.

- Perbaikan naskah: Stefan–Boltzmann disebut sebagai landasan konseptual, bukan bagian yang dihitung.

### B9. Ukuran grid dan sel

Naskah lama menulis "≈ 4 km" dan "2° × 2°" tanpa angka pasti. Nilai sebenarnya: 0,035° = 3,885 km (U–S) × 3,881 km (T–B); 58 × 58 = 3.364 sel; grid menutup 2,03° ≈ 225 km karena pembulatan ke atas.

- Perbaikan naskah: angka pasti dicantumkan pada Bagian 2 dan 4.

### B10. Perangkat lunak yang tidak dipakai

GeoPandas dan Shapely tercantum di `requirements.txt` tetapi tidak diimpor oleh kode aplikasi; MATLAB, COMSOL, Arduino IDE, dan komponen keras tidak dipakai sama sekali. Tabel komponen hanya memuat NumPy, pandas, scikit-learn, Folium, streamlit-folium, Streamlit, dan pytest.

### B11. Klaim "real-time"

Naskah lama menyebut "real-time" dan "near-real-time" tanpa kualifikasi. Muat pertama memerlukan 2–4 menit (Overpass + iNaturalist) dan hasilnya di-cache.

- Perbaikan naskah: dipakai "kuasi-real-time" dan waktu muat dilaporkan pada Bagian 4.2e.

---

## C. Penambahan isi yang sebelumnya kosong

| Bagian | Kondisi lama | Isi baru |
| --- | --- | --- |
| 4.1 Hasil perancangan | Placeholder template | Deskripsi tiga lapisan peta, ukuran grid, panel darurat, dan sistem ikon kustom |
| 4.2 Pengujian | Placeholder | Tabel sensitivitas angin (40 benih, 4 arah), waktu komputasi, jumlah uji (44 lulus), pengukuran tata letak 671/270/973 px |
| 4.3 Kelayakan | Placeholder | Analisis teknis, ekonomi, operasional, keberlanjutan |
| 4.4 Dampak | Placeholder | Potensi edukasi/mitigasi dan agenda pengembangan |
| 4.5 Keterbatasan | Tidak ada | Enam keterbatasan yang jujur (waktu, air, data FIRMS, peta kasar, GPS, validasi) |
| 5 Kesimpulan | Placeholder | Lima butir yang terhubung ke tujuan dan hasil terukur |
| 7.2 Anggaran | Contoh "xxx" | Tanpa pengadaan, total Rp 0 |
| 7.3 Dokumentasi | Tidak ada | Struktur berkas kode dan data |

---

## D. Angka yang perlu dicek ulang sebelum submit

1. **Tanggal penyelesaian** — diisi 21 Oktober 2026; sesuaikan dengan tanggal pengumpulan.
2. **Pembagian tugas** — peran pada Tabel 4 disusun dari struktur proyek; pastikan sesuai kesepakatan tim.
3. **Data FIRMS dan model** — repositori kini memuat `data/raw/firms_hotspots.csv` (1.770 titik panas kotak demo, 8 hari) dan model terlatih di `models/`; demo memakai Random Forest, bukan baseline heuristik. Metrik 4.2 butir d berasal dari dua hari uji terakhir pada ekspor MODIS 7 hari yang sama. Bila ekspor FIRMS diperbarui, jalankan `python -m src.train` dan perbarui angka pada Abstrak, 3.4.1, dan 4.2 butir d.
4. **Proporsi gambut** — angka "47% gambut tropis global" dari draf lama tidak dipakai karena estimasi literatur berkisar 36–47%. Naskah baru hanya menyebut 13,4 juta ha [1].
5. **Sitasi luasan terbakar 2015/2019** — memakai World Bank (2016) dan Mongabay (2021) yang mengutip KLHK.
