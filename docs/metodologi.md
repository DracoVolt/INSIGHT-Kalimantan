# METODOLOGI

Metodologi proyek INSIGHT disusun secara sistematis untuk memastikan prototipe dapat diselesaikan dalam waktu terbatas dengan sumber daya yang memadai. Alur pengerjaan proyek ini dirangkum dalam diagram alur berikut:

```
Identifikasi Permasalahan
        ↓
Studi Konsep Fisika (termodinamika perpindahan panas & dinamika angin)
        ↓
Pengumpulan dan Pengolahan Data (OpenStreetMap, NASA FIRMS, iNaturalist)
        ↓
Perancangan Solusi (model hibrida Cellular Automata + Machine Learning)
        ↓
Pembuatan Prototype (aplikasi web interaktif)
        ↓
Pengujian Prototype
        ↓
Evaluasi dan Penyempurnaan  ←─ (siklus iteratif)
        ↓
Prototype Final INSIGHT
```

## Tahap 1 — Identifikasi Permasalahan
Tahap ini dimulai dengan studi literatur mengenai kebakaran hutan dan lahan (karhutla) di Indonesia, khususnya pada ekosistem gambut tropis di Kalimantan Tengah yang meliputi Palangka Raya, Hutan Gambut Sebangau, dan DAS Kahayan. Berdasarkan laporan BMKG dan publikasi ilmiah terkait, diketahui bahwa api permukaan (surface fire) pada lahan gambut yang kaya bahan bakar organik kering menyebar sangat cepat, dan arah perambatannya sulit diprediksi hanya dengan pemantauan titik panas (hotspot) biasa. Permasalahan dirumuskan sebagai berikut: bagaimana merancang sistem prediksi jalur perambatan api permukaan yang berlandaskan fisika komputasi dan sekaligus menautkannya dengan sebaran flora–fauna endemik terancam punah, sehingga mitigasi dapat dilakukan secara dini dan tepat sasaran. Untuk membatasi cakupan proyek, ditetapkan area demonstrasi berupa bounding box berukuran 2° × 2° (112,5°–114,5° BT dan 1,5°–3,5° LS) di Kalimantan Tengah, dengan Palangka Raya sebagai pusat area kajian.

## Tahap 2 — Studi Konsep Fisika
Pada tahap ini dikaji konsep fisika yang menjadi dasar model perambatan api:

**a. Termodinamika perpindahan panas.** Api permukaan merambat karena tiga mekanisme perpindahan panas klasik: konduksi, konveksi, dan radiasi. Dalam model ini, perpindahan panas terhadap bahan bakar di sekitar titik api diabstraksikan ke dalam probabilitas penjalaran antarsel (perhitungan untuk ketiga mekanisme dijabarkan pada Tahap 4).

**b. Dinamika angin.** Arah dan kecepatan angin menentukan anisotropi penjalaran api: sel yang berada di hilir angin (downwind) memiliki peluang terbakar lebih besar daripada sel di hulu angin (upwind). Pengaruh angin dihitung melalui faktor keselarasan angin W(θ) ∈ [0, 1] yang mengukur kedekatan arah langkah antarsel terhadap arah angin θ (konvensi meteorologi, 0° = angin bertiup dari utara). Untuk pasangan sel sumber dan tetangganya,

  P(S→N) = P_base + k_wind · W(θ) + k_peat · 𝟙[N berisiko gambut]

dengan P_base = 0,15; k_wind = 0,25; dan k_peat = 0,20. Bobot W(θ) = max(0, 1 − Δθ/180°), di mana Δθ adalah selisih sudut antara arah langkah dan arah angin (di-wrap ke rentang 0°–180°). Sel gambut di hilir angin karenanya memiliki peluang terbakar per langkah hingga 0,60, sekitar empat kali peluang sel non-gambut di hulu angin (0,15).

**c. Cellular Automata (CA).** Lahan direpresentasikan sebagai grid diskrit dengan jarak antarsel 0,035° (≈ 4 km) dan tetangga 8-arah (Moore neighborhood). Setiap sel memiliki lima status: healthy, igniting, burning, burned, dan peat_risk. Pada setiap langkah waktu t → t+1: (1) sel burning/igniting menjadi burned; (2) tetangga yang dapat terbakar (healthy atau peat_risk) berubah menjadi igniting dengan probabilitas P(S→N); (3) sel burned bersifat tidak mudah terbakar kembali; dan (4) sel air dikeluarkan dari permukaan yang dapat terbakar. Seluruh probabilitas transisi dipotong (clamped) pada rentang [0, 1].

## Tahap 3 — Pengumpulan dan Pengolahan Data
Tiga sumber data publik digunakan sebagai input spasial sistem:

1. **OpenStreetMap (ODbL)** — diekstraksi melalui Overpass API untuk memperoleh sungai/badan air, jalan, permukiman, dan konteks tutupan lahan pada bounding box demo. Data ini menjadi fondasi peta dasar, penanda sel air yang tidak dapat terbakar, dan fitur jarak untuk model ML.
2. **NASA FIRMS (MODIS/VIIRS)** — titik panas aktif digunakan sebagai label keberadaan api untuk pelatihan model ML sekaligus titik inisiasi (seeding) simulasi CA dari kejadian kebakaran nyata.
3. **iNaturalist (CC licensing)** — observasi research-grade flora dan fauna endemik Kalimantan (orangutan Kalimantan, bekantan, Rafflesia arnoldii, dan kantong semar/Nepenthes) diambil melalui API v2 iNaturalist untuk membentuk layer spasial keanekaragaman hayati pada peta.

Pengolahan data mencakup konversi koordinat geodetik ke indeks sel grid (menggunakan metrik geodesik, m_per_deg_lon = 111.000 × cos(2,5°) ≈ 110.895 m; m_per_deg_lat ≈ 111.000 m), filter sel daratan pedalaman (sel air disaring keluar), dan penyimpanan hasil olahan dalam format CSV/JSON ringan di direktori `data/raw/` dan `data/processed/`. Tersedia fixture cadangan (stub) offline untuk setiap sumber data sehingga simulasi tetap dapat didemonstrasikan tanpa koneksi internet.

## Tahap 4 — Perancangan Solusi
Sistem dirancang sebagai aplikasi web dengan arsitektur modular yang menggabungkan model fisika dan statistik (model hibrida):

- **Modul pemodelan fisika (CA).** Mesin CA menerapkan aturan transisi Tahap 2c, di mana tiga mekanisme perpindahan panas diabstraksikan sebagai berikut: konveksi direpresentasikan oleh suku angin k_wind · W(θ) (kolom panas miring ke hilir angin dan memanaskan bahan bakar di depan muka api), radiasi direpresentasikan oleh P_base (setiap sel terbakar memancarkan energi ~ σT⁴ mengikuti hukum Stefan–Boltzmann ke segala arah), dan konduksi diabaikan karena berukuran sangat kecil pada skala sel 4 km. Suku k_peat merepresentasikan beban bahan bakar gambut yang tinggi dan kelembapan yang rendah sehingga energi penyalaan yang dibutuhkan menurun.
- **Modul Machine Learning.** Klasifikator Random Forest dilatih dengan fitur spasial per sel — riwayat hotspot FIRMS 7 hari terakhir, jarak ke sungai/jalan/permukiman (OSM), tipe tutupan lahan, penanda risiko gambut, dan keselarasan arah angin — untuk memprediksi probabilitas risiko r(cell) ∈ [0, 1] per sel. Sel berisiko tinggi (r di atas ambang batas) digunakan sebagai titik awal (seeding) simulasi CA, sehingga simulasi fisika berangkat dari peta risiko statistik, bukan titik acak. Alur lengkapnya: data → peta risiko ML → seeding CA → frame perambatan CA → notifikasi mitigasi.
- **Modul visualisasi web.** Peta interaktif berbasis Folium dengan zoom dibatasi hingga wilayah Indonesia (max_bounds), grid titik (dot grid) daratan pedalaman yang berwarna sesuai status CA, panel data simulasi (jumlah sel per status, langkah waktu, estimasi luas terdampak), serta layer sebaran flora–fauna endemik Kalimantan dari iNaturalist yang tumpang tindih dengan jalur api untuk memproyeksikan dampak ekologis secara langsung.
- **Modul mitigasi masyarakat.** Aturan sederhana memicu peringatan mitigasi ketika sel terbakar berada dalam radius 2 sel (≈ 8 km) dari permukiman (radius rural ≈ 3 sel ≈ 12 km), dengan filter lokasi pengguna agar hanya notifikasi di sekitarnya yang muncul. Pesan mitigasi bertingkat (rendah/sedang/tinggi) disusun dari kombinasi jarak ke sel terbakar, status CA, dan probabilitas risiko ML.

## Tahap 5 — Pembuatan Prototype
Prototype dikembangkan dengan bahasa Python dan pustaka Streamlit, NumPy, Pandas, GeoPandas/Shapely, scikit-learn, serta Folium, dalam satu repositori modular (`src/` untuk logika inti, `app/` untuk antarmuka web, `notebooks/` untuk eksplorasi data, dan `tests/` untuk pengujian). Fase pengerjaan: (1) membangun grid dan mesin CA; (2) mengintegrasikan data OSM dan hotspot FIRMS; (3) melatih model ML dan menghubungkannya ke seeding CA; (4) membangun antarmuka peta interaktif dua layer (kebakaran dan keanekaragaman hayati); (5) menambahkan panel mitigasi dan notifikasi berbasis lokasi pengguna. Seluruh konstanta model terpusat pada satu berkas konfigurasi (src/config.py) agar setiap angka dapat ditelusuri kembali ke kode dan direproduksi.

## Tahap 6 — Pengujian Prototype
Pengujian dilakukan berlapis:

- **Uji unit logika CA** — memastikan api hanya menyebar ke sel yang valid (tidak menembus sel air atau sel burned), probabilitas transisi selalu berada di [0, 1], dan status sel berubah sesuai aturan transisi.
- **Uji sensitivitas parameter** — mengubah arah angin dan status gambut lalu memverifikasi bahwa pola perambatan berubah sesuai intuisi fisika (muka api lebih cepat ke hilir angin; sel gambut lebih mudah terbakar).
- **Uji integrasi data** — memverifikasi bahwa layer OSM, hotspot FIRMS, dan observasi iNaturalist tampil pada koordinat yang benar di atas grid.
- **Uji pengguna** — anggota tim dan teman sekolah mencoba aplikasi dan memberikan masukan mengenai kejelasan visual, keterbacaan panel informasi, dan kemudahan penggunaan.

## Tahap 7 — Evaluasi dan Penyempurnaan
Hasil pengujian dievaluasi dengan membandingkan jalur simulasi terhadap pola umum sebaran hotspot historis dan kesesuaian visual peta risiko ML terhadap titik api nyata. Metrik kinerja model ML (akurasi, presisi, recall, ROC-AUC, dan PR-AUC pada pembagian temporal: enam hari latih dan dua hari uji terakhir) dilaporkan secara terbuka. Temuan seperti resolusi grid yang terlalu kasar, data yang belum tersinkron, atau antarmuka yang kurang jelas dicatat sebagai umpan balik iteratif. Siklus perancangan → prototype → pengujian → evaluasi diulang hingga simulasi menghasilkan proyeksi yang konsisten secara fisika dan aplikasi mudah digunakan oleh masyarakat umum, bukan hanya peneliti. Hasil akhir dari metodologi ini adalah prototipe INSIGHT yang mampu memproyeksikan perambatan api permukaan secara real-time, menampilkan dampaknya terhadap habitat flora–fauna endemik, dan memberikan rekomendasi mitigasi dini bagi masyarakat.

## Keterbatasan Metodologi
Sebagai proyek sains berskala pelajar, beberapa keterbatasan diakui secara eksplisit: fisika yang disederhanakan (CA adalah model pembelajaran, bukan model operasional seperti Rothermel); angin statis yang dianggap seragam di seluruh area demo; potensi ketidaklengkapan data FIRMS/OSM/iNaturalist pada bounding box; model ML baseline yang dirancang untuk mudah dijelaskan, bukan dioptimalkan; dan panduan mitigasi yang bersifat ilustratif, bukan pengganti instruksi resmi penanggulangan bencana.

---

## Daftar Sumber Data dan Referensi

Sumber data dan referensi yang digunakan dalam metodologi ini dirangkum pada berkas terpisah: [`docs/daftar-sumber.md`](daftar-sumber.md).
