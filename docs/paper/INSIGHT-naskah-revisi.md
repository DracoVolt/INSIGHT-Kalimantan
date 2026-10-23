# SCIENCE PROJECT COMPETITION EUREKA! ITB 2026

## INSIGHT: Simulasi Prediksi Perambatan Api Permukaan Lahan Gambut Berbasis Cellular Automata dan Machine Learning Berpenjelas untuk Pemetaan Flora-Fauna Endemik

oleh

**Atahya Rayyan Alghifari Yuwono, Melvin Khaizuran, Prabu Ditya Irfahany**

SMA Negeri 34 Jakarta, Jakarta Selatan, DKI Jakarta, Indonesia
Himpunan Mahasiswa Fisika, Institut Teknologi Bandung
Email: atahya.yuwono@gmail.com

Subtema: Komputasi, Simulasi, dan Kecerdasan Buatan.

Tanggal: 21 Oktober 2026

---

## ABSTRAK

Kebakaran hutan dan lahan di ekosistem gambut tropis Indonesia merupakan bencana ekologis berulang yang dipicu oleh kerentanan bahan bakar organik kering terhadap perambatan api permukaan (*surface fire*). Keterbatasan sistem pemodelan yang dirancang khusus untuk topografi dan kondisi termodinamika gambut menyulitkan upaya mitigasi dini yang akurat di lapangan. Proyek ini bertujuan merumuskan model probabilistik hibrida, membangun perangkat lunak simulasi interaktif berbasis web yang dilengkapi prediksi sebaran api dan pemetaan flora-fauna endemik, serta memproyeksikan lintasan penyebaran api secara kuasi-*real-time* untuk menekan dampak kerusakan lingkungan. Berlandaskan konsep fisika komputasi melalui prinsip perpindahan panas dan dinamika angin, proyek ini menawarkan INSIGHT (*Integrated Surface Ignition & Flora Fauna Mapping Hazard Tracker*) sebagai sistem pendukung keputusan yang terintegrasi dengan analisis spasial sebaran flora dan fauna endemik Kalimantan yang terancam punah. Metode pengembangan menerapkan algoritma transisi ruang-waktu berbasis *Cellular Automata* (CA) pada grid 58 × 58 sel berukuran 0,035° (≈ 3,9 km) yang mencakup wilayah Palangka Raya, Taman Nasional Sebangau, dan Daerah Aliran Sungai Kahayan, serta mengintegrasikan data OpenStreetMap, NASA FIRMS, dan iNaturalist. Setiap langkah CA menyulut sel tetangga dengan probabilitas 0,15–0,60 yang bergantung pada keselarasan arah angin dan status risiko gambut, sehingga terbentuk batas depan api yang anisotropik. Lapisan *Random Forest* dengan 200 pohon dan 11 fitur prediktor—termasuk riwayat titik panas 1–7 hari dan jarak ke titik panas hari sebelumnya—menyediakan peta risiko per sel yang dapat dijelaskan (ROC-AUC 0,883 dan PR-AUC 0,283 pada pembagian temporal); apabila berkas model atau data FIRMS belum tersedia, sistem secara otomatis memakai baseline heuristik transparan agar simulasi tetap berjalan. Luaran yang diharapkan adalah prototipe perangkat lunak simulasi interaktif yang dapat memproyeksikan risiko kebakaran sekaligus memandu prioritas evakuasi habitat satwa dan perlindungan lahan gambut secara berkelanjutan.

**Kata kunci:** *Cellular Automata*, *Machine Learning*, Pemodelan Termodinamika, Simulasi Mitigasi, *Surface Fire*.

---

## 1. PENDAHULUAN

### 1.1 Latar Belakang

Indonesia memiliki salah satu ekosistem lahan gambut tropis terluas di dunia, dengan estimasi luasan sekitar 13,4 juta hektar berdasarkan pembaruan peta gambut nasional [1]. Ekosistem yang masif ini sangat rentan menjadi episentrum bencana kebakaran hutan dan lahan (karhutla) tahunan. Pada krisis karhutla berskala besar, sekitar 2,6 juta hektar lahan terbakar sepanjang Juni–Oktober 2015 [2], sedangkan pada 2019 Kementerian Lingkungan Hidup dan Kehutanan mencatat 1,64 juta hektar area terdampak [3]. Area gambut menyumbang tingkat kerusakan serta emisi karbon tertinggi pada kedua peristiwa tersebut.

Fenomena ini berakar pada karakteristik unik lahan gambut yang kaya bahan bakar organik kering di permukaan, sehingga vegetasi dan serasah di atasnya sangat rentan terhadap perambatan api permukaan. Perambatan api bersifat dinamis karena dikendalikan kondisi termodinamika lingkungan, seperti fluktuasi arah dan kecepatan angin serta kelembapan bahan bakar, yang memicu persebaran masif dan menyulitkan pengendalian di lapangan.

Selama ini, upaya penanggulangan dan pemantauan karhutla umumnya masih bergantung pada pemetaan titik panas (*hotspot*) statis berbasis satelit maupun observasi visual konvensional. Pendekatan reaktif ini memiliki keterbatasan signifikan, terutama dalam merespons munculnya titik api baru yang menyebar cepat. Ketiadaan sistem prediksi perambatan api proaktif berbasis fisika komputasi yang dirancang spesifik untuk topografi dan kondisi termodinamika gambut membuat lintasan pergerakan kebakaran sulit diantisipasi secara presisi, sehingga langkah mitigasi dini dan evakuasi sering terlambat. Menjawab tantangan tersebut, penelitian ini mengusulkan INSIGHT (*Integrated Surface Ignition & Flora Fauna Mapping Hazard Tracker*), sebuah perangkat lunak simulasi interaktif berbasis web untuk memproyeksikan perambatan api permukaan. Sistem ini merumuskan model probabilistik yang mengombinasikan prinsip fisika komputasi—khususnya perpindahan panas—dengan *Cellular Automata* dan lapisan prediksi *Machine Learning*, serta mengintegrasikan modul pemetaan spasial wilayah sebaran flora dan fauna endemik Kalimantan yang terancam punah.

### 1.2 Rumusan Masalah

1. Bagaimana merumuskan model simulasi probabilistik perambatan api permukaan pada lahan gambut melalui integrasi prinsip perpindahan panas, *Cellular Automata*, dan *Machine Learning*?
2. Bagaimana menyajikan hasil proyeksi lintasan pergerakan api dan informasi sebaran keanekaragaman hayati secara akurat melalui peta interaktif berbasis web?
3. Bagaimana mengembangkan prototipe sistem pendukung keputusan yang andal untuk mengoptimalkan mitigasi karhutla dan perlindungan ekologis secara proaktif?

### 1.3 Tujuan Penelitian

1. Merumuskan model matematis probabilistik penjalaran api permukaan melalui pendekatan perpindahan panas dan algoritma ruang-waktu *Cellular Automata*.
2. Membangun model prediksi risiko spasial *Machine Learning* berbasis *Random Forest* dengan memanfaatkan data geospasial multisumber dari OpenStreetMap, NASA FIRMS, dan iNaturalist.
3. Mengembangkan prototipe perangkat lunak simulasi interaktif berbasis web INSIGHT guna mendukung pengambilan keputusan mitigasi karhutla dan perlindungan ekologis secara berkelanjutan.

### 1.4 Kontribusi dan Kebaruan

Kontribusi utama penelitian ini adalah sistem pendukung keputusan operasional yang mengintegrasikan pemodelan komputasi fisika dengan analisis spasial ekologis untuk memproyeksikan area terdampak sekaligus memandu prioritas evakuasi habitat satwa. Kebaruan INSIGHT terletak pada arsitektur hibrida yang menyatukan aturan transisi probabilistik berbasis *Cellular Automata* dengan lapisan risiko *Machine Learning* dan indeks kerentanan ekologis dalam satu platform web yang ringan dan interaktif.

Berbeda dari platform GIS konvensional yang statis, INSIGHT menjawab tema kompetisi "Physics for Future Solutions" dengan menggeser paradigma mitigasi karhutla dari pemantauan titik panas menuju proyeksi lintasan api dan perlindungan ekologis yang berkelanjutan. Seluruh parameter model dinyatakan terbuka dalam satu berkas konfigurasi, sehingga setiap angka dalam simulasi dapat ditelusuri dan direproduksi. Lapisan *Machine Learning* bukan hiasan: peta risiko pada kotak demo adalah keluaran model yang dilatih pada titik panas NASA FIRMS nyata, dan antarmuka selalu mencantumkan sumber serta metrik model tersebut.

---

## 2. DASAR TEORI DAN IDE SOLUSI

Proyek: **INSIGHT** (*Integrated Surface Ignition & Flora Fauna Mapping Hazard Tracker*)

- Wilayah demo: Kalimantan Tengah — Palangka Raya, Taman Nasional Sebangau, dan lahan gambut DAS Kahayan.
- Batas wilayah (*bounding box*): 112,5°–114,5° BT, 1,5°–3,5° LS.
- Jarak kisi (*grid spacing*): 0,035°, yaitu sekitar 3,885 km arah utara–selatan dan 3,881 km arah timur–barat pada lintang 2,5° LS.
- Dimensi grid: 58 baris × 58 kolom = 3.364 sel, dengan ketetanggan 8-Moore. Karena pembulatan ke atas, grid menutup 2,03° (≈ 225 km) pada setiap arah, sedikit lebih luas daripada kotak nominal 2° (≈ 222 km).
- Konvensi indeks: baris 0 berada di tepi utara dan indeks baris bertambah ke selatan; indeks kolom bertambah ke timur.

Semua nilai di bawah ini sesuai dengan `src/config.py` dan logika `src/ca.py`, sehingga setiap angka dapat ditelusuri kembali ke kode program.

### 2.1 Faktor keselarasan angin

Untuk setiap sel terbakar *S* dan tetangga *N*, hitung arah kompas (*bearing*) langkah dari *S* ke *N*:

θ_bearing = atan2(Δkolom, −Δbaris), dengan 0° = utara dan 90° = timur.

Arah ini dibandingkan dengan arah hembusan api, bukan arah asal angin. Karena data angin mengikuti konvensi meteorologi (0° berarti angin bertiup **dari** utara), arah rambat yang didorong angin adalah:

θ_downwind = (θ_angin + 180°) mod 360°.

Faktor keselarasan kemudian dihitung sebagai:

W(θ) = 1 − |θ_bearing − θ_downwind| / 180°,

dengan selisih sudut diambil pada rentang 0°–180° dan hasilnya dibatasi pada [0, 1].

Interpretasi:

- W = 1: tetangga berada tepat searah hembusan angin (api bertiup ke arahnya).
- W = 0,5: tetangga berada tegak lurus terhadap arah angin.
- W = 0: tetangga berada tepat berlawanan arah hembusan angin.

### 2.2 Probabilitas penyulutan (aturan transisi CA)

Sel terbakar *S* menyulut tetangga *N* yang dapat terbakar dengan probabilitas:

P(S→N) = min(1, P_base + k_wind · W(θ) + k_peat · 1[N berisiko gambut]),

dengan konstanta demo:

- P_base = 0,15 (probabilitas penyulutan dasar per langkah),
- k_wind = 0,25 (kekuatan keselarasan angin),
- k_peat = 0,20 (bonus kemudahan terbakar gambut, hanya untuk sel gambut).

Rentang hasil per tetangga per langkah:

- Minimum (berlawanan arah angin, non-gambut): 0,15.
- Maksimum (searah hembusan angin, gambut): 0,15 + 0,25 + 0,20 = 0,60.

Dengan demikian, sel gambut yang berada tepat searah hembusan angin memiliki peluang terbakar empat kali lebih besar per langkah dibandingkan sel non-gambut yang berlawanan arah angin. Kombinasi angin dan jenis bahan bakar ini membentuk batas depan kebakaran yang anisotropik.

**Asimetri terarah berbobot angin.** Karena W bervariasi linear terhadap perbedaan sudut, batas depan api bergerak paling cepat ke arah hembusan angin. Untuk jumlah langkah tetap, perkiraan laju penyebaran ke arah θ relatif terhadap arah angin adalah:

v(θ) ∝ P(S→N; θ) = P_base + k_wind · W(θ) + k_peat · 1[N gambut].

Ini merupakan analogi diskrit dari prinsip Huygens: setiap sel terbakar bertindak sebagai sumber titik, dan batas depan api berikutnya adalah amplop dari penyulutan yang berhasil.

### 2.3 Aturan pembaruan status CA

Setiap sel memiliki satu status: `healthy` (sehat), `igniting` (mulai menyala), `burning` (terbakar), `burned` (hangus), atau `peat_risk` (risiko gambut).

- Aturan 1 (habis terbakar): `igniting`, `burning` → `burned` pada langkah berikutnya.
- Aturan 2 (penyulutan): tetangga *N* dari sel yang sedang menyala (`burning` atau `igniting`) dan berstatus `healthy` atau `peat_risk` berubah menjadi `igniting` dengan probabilitas P(S→N).
- Aturan 3 (bahan bakar): sel berstatus `burned` tidak dapat terbakar lagi, sehingga api tidak dapat masuk kembali.
- Aturan 4 (batas domain): penyulutan hanya terjadi di dalam grid; sel di luar batas wilayah tidak diikutkan.
- Aturan 5 (air): sel yang ditandai air oleh mask OpenStreetMap tidak dapat terbakar, sehingga sungai dan danau memotong batas depan api. Seluruh sel daratan lain — termasuk permukiman dan sel `peat_risk` — tetap dapat terbakar, dan titik panas yang jatuh di sel air tidak dipakai sebagai benih.

Penarikan penyulutan bersifat uji Bernoulli independen: untuk setiap pasangan sel–tetangga, bilangan acak seragam u ~ U(0,1) dibangkitkan dan penyulutan berhasil bila u < P(S→N).

Intensitas pembakaran dilacak sebagai pencatat monoton per sel: bertambah 1 untuk sel yang habis terbakar pada langkah ini dan diberi nilai 0,5 untuk sel yang baru mulai menyala.

### 2.4 Intuisi perpindahan panas

*Cellular Automata* mengabstraksikan tiga moda perpindahan panas klasik ke dalam probabilitas penyulutan:

- **Konveksi** ditangkap oleh suku angin k_wind · W(θ): pluma panas miring searah hembusan angin dan memanaskan bahan bakar di depan garis api.
- **Radiasi** direpresentasikan oleh probabilitas dasar P_base: setiap tetangga yang terbakar memancarkan radiasi ke bahan bakar di sekitarnya tanpa memandang arah.
- **Konduksi** dapat diabaikan pada skala sel ≈ 3,9 km dan digabungkan ke dalam P_base.

Hukum Stefan–Boltzmann (P_rad = εσAT⁴) menjadi landasan konseptual untuk suku radiasi, tetapi prototipe ini **tidak menghitung σT⁴ secara eksplisit**; kontribusi radiasi diringkas menjadi probabilitas dasar yang konstan. Bonus gambut memodelkan beban bahan bakar yang lebih tinggi dan kelembapan tanah gambut yang lebih rendah: bahan organik kering menurunkan energi penyulutan yang dibutuhkan, sehingga fluks panas yang sama menghasilkan probabilitas penyulutan yang lebih tinggi.

### 2.5 Lapisan *Machine Learning*

Klasifikasi *Random Forest* dilatih menggunakan fitur spasial publik per sel:

- **Fitur prediktor (11 kolom):** `cell_row`, `cell_col`, jarak ke sel air terdekat, jarak ke sel permukiman terdekat, jarak ke titik panas terdekat hari sebelumnya, penanda risiko gambut, keberadaan titik panas 1 hari terakhir, 3 hari terakhir, dan 7 hari terakhir, jumlah titik panas 7 hari terakhir, serta keselarasan angin. Kolom `lon` dan `lat` tetap ada di tabel fitur untuk keperluan pemetaan, tetapi tidak dipakai melatih model karena keduanya hanya mengodekan posisi grid.
- **Label:** apakah sel tersebut berisi titik panas FIRMS terkonfirmasi pada hari itu (1) atau tidak (0). Seluruh fitur riwayat dihitung **hanya dari hari-hari sebelum hari label** (D−1 sampai D−7); hari label itu sendiri tidak pernah masuk, sehingga model tidak dapat menyalin label. Aturan ini diuji secara eksplisit: sel yang terbakar pada hari D harus bernilai 0 pada fitur riwayat hari D.
- **Model:** `RandomForestClassifier` dengan 200 pohon, kedalaman maksimum 8, tanpa pembobotan kelas, dan `random_state = 42`. Pembobotan kelas seimbang diuji dan justru menurunkan kinerja pada pembagian temporal (ROC-AUC 0,863 vs 0,883; PR-AUC 0,222 vs 0,283), sekaligus menaikkan rata-rata probabilitas prediksi menjadi 0,24 padahal laju positif teramati 0,032.
- **Pembagian data:** temporal, bukan acak. Delapan hari pengamatan dibagi menjadi 6 hari latih dan 2 hari uji (20.184 baris latih, 6.728 baris uji, 163 positif uji). Pembagian acak per baris akan menempatkan sel yang sama di kedua sisi dan menggelembungkan metrik, karena sebagian sel terbakar berulang.
- **Metrik evaluasi:** akurasi, presisi, *recall*, ROC-AUC, dan *average precision* (PR-AUC).
- **Output:** r(cell), yaitu probabilitas prediksi kebakaran per sel pada hari berikutnya.
- **Pelatihan dan penyimpanan:** `python -m src.train --firms data/raw/MODIS_C6_1_Global_7d.csv` menulis `models/risk_rf.joblib` dan `models/risk_rf_metrics.json`. Aplikasi memuat kedua berkas itu saat inisialisasi; bila berkas atau pustaka tidak tersedia, aplikasi memakai baseline heuristik dan menampilkan sumber peta risiko di panel samping.

Jarak ke air dan permukiman dihitung dengan *Euclidean distance transform* eksak (algoritma Felzenszwalb–Huttenlocher [4]) sehingga seluruh grid diproses dalam O(N), bukan O(N²) per kueri. Hal ini penting karena tabel fitur tumbuh sebanding dengan jumlah sel dikali jumlah hari.

Saat inferensi, model diberi riwayat titik panas nyata: fitur D−1 sampai D−7 dihitung dari hari terakhir pengamatan FIRMS, sehingga peta menjawab "di mana titik panas akan muncul besok" dan bukan "di mana titik panas tercatat hari ini". Snapshot OpenStreetMap dibaca dari cache `data/raw/osm_snapshot.json` agar peta konteks air, permukiman, dan gambut saat inferensi identik dengan yang dipakai saat pelatihan.

Peta risiko hasil model digunakan untuk **prioritas mitigasi dan visualisasi**, bukan untuk membenihkan CA. Pembenihan CA berasal dari titik panas FIRMS: setiap hotspot di dalam kotak demo memetakan satu sel menjadi `burning`. Apabila berkas FIRMS belum tersedia atau tidak ada hotspot yang valid, simulasi membenihkan satu sel di pusat grid agar tetap dapat dijalankan.

Apabila model terlatih belum tersedia, `predict_risk_map` memakai baseline heuristik yang sepenuhnya transparan:

r(cell) = 0,05 + 0,25 · keselarasan angin + 0,15 · penanda gambut + 0,10 · kedekatan permukiman − 0,08 · kedekatan air,

dengan hasil dibatasi pada [0; 1]. Baseline ini memungkinkan antarmuka dan modul mitigasi diuji tanpa bergantung pada ketersediaan data latih.

### 2.6 Peta risiko skala Kalimantan

Selain kotak demo, aplikasi menampilkan peta risiko seluruh Kalimantan pada grid kasar 0,15° (≈ 16,6 km per sel), mencakup 108,8°–119,1° BT dan 4,2° LS–7,3° LU. Peta ini memakai heuristik fisika (keselarasan angin, pita gambut, dan kedalaman *inland*) yang dihitung secara vektorisasi NumPy, sehingga seluruh pulau dapat dirender dalam milidetik. Berbeda dari peta kotak demo yang memakai *Random Forest* terlatih, peta pulau **bukan** keluaran model: fitur OSM dan FIRMS per sel hanya tersedia di kotak demo. Peta ini karenanya bersifat indikatif, tidak menjalankan CA, dan diberi label eksplisit pada antarmuka.

Lingkaran risiko hanya digambar pada sel yang pusatnya berada di daratan, memakai garis pantai Natural Earth 1:50m [12] yang disederhanakan dan disimpan di `assets/geo/kalimantan_land.geojson`. Dari 5.313 sel pada kotak pembatas, 2.688 di antaranya berada di darat, sehingga Laut Jawa, Selat Karimata, dan Laut Cina Selatan tidak dipenuhi titik yang tidak memiliki bahan bakar. Mask ini dihitung sekali saat peta dirender dan diperbarui dengan perintah `python -m src.land_mask build`.

### 2.7 Aturan jarak peringatan mitigasi

Sel permukiman memicu panduan mitigasi apabila jarak sel terbakar ke permukiman ≤ 2 sel (≈ 7,8 km) atau ke area pedesaan ≤ 3 sel (≈ 11,7 km). Panduan yang sama ditampilkan pada panel darurat di sisi kanan aplikasi, yang dapat dibuka atau ditutup pengguna.

Peringatan bersifat per pengguna: pengguna mengetikkan koordinat lintang/bujur di dalam kotak demo, lalu sistem memetakannya ke sel dan hanya menampilkan peringatan untuk sel di sekitar lokasi tersebut. **Aplikasi web ini tidak mengakses GPS perangkat**; koordinat dimasukkan secara manual. Koordinat di luar kotak demo ditolak dengan pesan kesalahan yang jelas.

### 2.8 Tabel simbol

| Simbol | Arti | Nilai/Rentang |
| --- | --- | --- |
| P_base | Probabilitas dasar per langkah | 0,15 |
| k_wind | Kekuatan keselarasan angin | 0,25 |
| k_peat | Bonus kemudahan terbakar gambut | 0,20 |
| W(θ) | Faktor keselarasan angin | 0–1 |
| θ_angin | Arah angin (meteorologi, dari mana angin bertiup) | default demo 90° |
| r(cell) | Prediksi risiko kebakaran ML | 0–1 |
| Δ | Jarak kisi (*grid spacing*) | 0,035° ≈ 3,9 km |
| R_permukiman | Radius peringatan permukiman | 2 sel ≈ 7,8 km |
| R_pedesaan | Radius peringatan area pedesaan | 3 sel ≈ 11,7 km |

---

## 3. METODOLOGI

### 3.1 Alat dan Bahan

Proyek ini merupakan penelitian komputasi tanpa perangkat keras khusus, sehingga tidak memerlukan mikrokontroler, sensor, atau aktuator. Seluruh komponen perangkat lunak bersifat *open source* dan dijalankan pada laptop anggota tim.

| Komponen | Spesifikasi | Fungsi Utama |
| --- | --- | --- |
| Bahasa pemrograman | Python 3.10+ | Implementasi seluruh model dan antarmuka |
| Engine fisika CA | NumPy, pandas | Aturan transisi CA dan perhitungan matriks probabilitas |
| Model ML | scikit-learn, joblib | Pelatihan *Random Forest*, evaluasi metrik, penyimpanan model |
| Data geospasial | Overpass API (OpenStreetMap), NASA FIRMS, iNaturalist API v2 | Konteks lahan, titik panas, sebaran flora-fauna |
| Garis pantai | Natural Earth 1:50m (domain publik) | Mask daratan pada peta risiko pulau |
| Visualisasi peta | Folium, streamlit-folium | Peta interaktif, layer grid, dan penanda flora-fauna |
| Antarmuka web | Streamlit | Dasbor, kontrol simulasi, panel mitigasi, unggah ikon |
| Pengujian | pytest | Uji unit CA, fitur, ML, mitigasi, ikon, mask daratan, dan asap integrasi |

Tabel 1. Spesifikasi komponen perangkat lunak dan fungsinya.

Perangkat lunak pendukung lain: `urllib` untuk akses API, `shapely` untuk uji titik-dalam-poligon pada mask daratan, serta `base64` dan `mimetypes` untuk menyematkan berkas ikon sebagai data URI.

### 3.2 Metode Penelitian atau Perancangan

Metode yang digunakan adalah **pemodelan dan simulasi komputasi** yang dipadukan dengan **perancangan sistem perangkat lunak**. Tahapan dimulai dari identifikasi masalah dan kajian literatur, dilanjutkan dengan formulasi model matematis, implementasi prototipe, pengujian bertingkat, dan evaluasi iteratif. Model fisik tidak diselesaikan sebagai persamaan diferensial kontinu, melainkan didiskretisasi menjadi aturan transisi probabilistik pada grid seragam. Pendekatan ini dipilih agar komputasi tetap ringan di browser, setiap parameter dapat dijelaskan, dan hasil simulasi dapat direproduksi.

### 3.3 Diagram Alir Penelitian dan Perancangan

Alur kerja sistem:

1. **Akuisisi data** — Overpass API mengambil fitur air, permukiman, dan lahan gambut; NASA FIRMS menyediakan titik panas; iNaturalist API v2 menyediakan observasi flora-fauna dalam kotak Kalimantan.
2. **Praproses** — data titik dipetakan ke sel grid 58 × 58; dibangun peta konteks air, permukiman, dan risiko gambut; dihitung jarak eksak ke fitur terdekat.
3. **Pelatihan model** — tabel fitur per sel per hari dibangun dari ekspor FIRMS, lalu *Random Forest* dilatih, dievaluasi pada dua hari terakhir (pembagian temporal), dan disimpan ke `models/` bersama metriknya.
4. **Simulasi CA** — sel dibenihkan dari titik panas (atau sel pusat), lalu aturan transisi dijalankan sejumlah langkah yang dipilih pengguna.
5. **Penyajian** — peta sebaran biodiversitas, peta risiko kotak demo hasil model, peta risiko Kalimantan, panel mitigasi, dan panel darurat dirender di Streamlit.
6. **Evaluasi** — uji unit dan uji antarmuka dijalankan; parameter disesuaikan bila perilaku model tidak sesuai.

### 3.4 Tahapan Penelitian

#### 3.4.1 Analisis

Tahap awal meliputi analisis kebutuhan dan identifikasi masalah karhutla di ekosistem gambut tropis Kalimantan Tengah, mencakup Palangka Raya, Taman Nasional Sebangau, dan DAS Kahayan. Kajian difokuskan pada keterbatasan sistem pemantauan konvensional dalam memprediksi *surface fire* yang sulit diantisipasi hanya dari pemantauan titik panas. Wilayah studi dibatasi pada kotak 2° × 2° dengan Palangka Raya sebagai pusat kajian. Analisis juga mencakup pendataan sumber data publik:

| Sumber Data | Format | Fungsi dalam Sistem |
| --- | --- | --- |
| OpenStreetMap | Overpass API (ODbL) | Layer sungai/badan air, permukiman, lahan gambut, dan fitur jarak |
| NASA FIRMS | MODIS/VIIRS (CSV) | Titik panas aktif sebagai label pelatihan ML dan pembenihan CA |
| iNaturalist | API v2 (lisensi CC per observasi) | Titik observasi flora-fauna endemik yang terancam punah |
| Natural Earth | GeoJSON 1:50m (domain publik) | Garis pantai untuk mask daratan peta pulau |

Tabel 2. Spesifikasi sumber data dan fungsinya dalam sistem.

#### 3.4.2 Desain

Tahap perancangan berfokus pada formulasi matematis model dan arsitektur transisi ruang-waktu CA. Aturan transisi menggunakan grid 8-tetangga Moore dengan lima status sel. Probabilitas penjalaran api dirumuskan pada Bagian 2.2, sedangkan pembaruan status dijelaskan pada Bagian 2.3. Rancangan antarmuka menempatkan peta pada kolom utama dan panel darurat pada kolom kedua di sisi kanan, sehingga tidak ada elemen yang menutupi peta.

#### 3.4.3 Development

Tahap ini menerjemahkan rancangan menjadi kode Python. Struktur repositori memisahkan model (`src/ca.py`, `src/ml.py`, `src/features.py`), pelatihan (`src/train.py`), data (`src/osm.py`, `src/fire_data.py`, `src/bio_loader.py`), peta (`src/land_mask.py`), logika mitigasi (`src/mitigation.py`), registri ikon (`src/icons.py`), dan antarmuka (`app/main.py`). Seluruh konstanta fisika dan ML ditempatkan pada `src/config.py`, sedangkan artefak model disimpan di `models/`.

#### 3.4.4 Implementation

Prototipe diimplementasikan dan diuji secara bertahap melalui empat tingkatan:

1. **Uji logika CA:** memastikan perubahan status sel berjalan sesuai aturan dan probabilitas berada pada batas [0, 1].
2. **Uji sensitivitas parameter:** memverifikasi bahwa pola perambatan bergeser konsisten mengikuti perubahan arah angin dan keberadaan lahan gambut.
3. **Uji integrasi data:** menguji ketepatan penumpangsusunan koordinat OSM, FIRMS, dan iNaturalist di atas grid simulasi, termasuk konvensi baris utara–selatan.
4. **Uji pengguna (UI/UX):** menguji keterbacaan antarmuka, kemudahan navigasi dasbor, dan kejelasan notifikasi peringatan dini.

#### 3.4.5 Evaluation

Hasil pengujian dievaluasi secara iteratif. Kinerja model ML diukur dengan akurasi, presisi, *recall*, ROC-AUC, dan PR-AUC. Umpan balik dari pengujian digunakan untuk mengoptimalkan kecepatan komputasi serta menyempurnakan tampilan dasbor hingga dihasilkan prototipe yang stabil, akurat, dan intuitif.

---

## 4. HASIL DAN PEMBAHASAN

### 4.1 Hasil Perancangan dan Pengembangan Prototipe

Prototipe INSIGHT berupa aplikasi web Streamlit yang menampilkan empat lapisan utama:

1. **Peta sebaran flora-fauna** — titik observasi iNaturalist untuk Orangutan Kalimantan (*Pongo pygmaeus*), Bekantan (*Nasalis larvatus*), Rafflesia, dan Nepenthes, difilter ke wilayah Kalimantan dan ditampilkan dengan ikon khusus.
2. **Peta risiko kotak demo** — probabilitas *Random Forest* per sel untuk hari setelah pengamatan FIRMS terakhir, dengan keterangan sumber, ROC-AUC, PR-AUC, dan tanggal kondisi riwayat titik panas.
3. **Peta risiko skala Kalimantan** — permukaan risiko kasar 0,15° (≈ 16,6 km per sel) dari heuristik fisika, digambar hanya pada sel daratan.
4. **Panel darurat dan mitigasi** — kolom kedua di sisi kanan berisi lokasi pengguna, ringkasan hotspot terdekat, dan kartu panduan mitigasi per sel.

Grid demo memiliki 58 × 58 sel dengan ukuran 3,885 km (utara–selatan) × 3,881 km (timur–barat). Setiap sel menyimpan status CA, penanda risiko gambut, dan intensitas pembakaran. Simulasi default berjalan 12 langkah dan dapat diubah pengguna pada rentang 1–20 langkah.

Ikon flora-fauna dapat diganti pengguna tanpa mengubah kode: berkas gambar diletakkan di folder `assets/icons/` dengan nama sesuai kunci takson (`orangutan`, `proboscis-monkey`, `rafflesia`, `nepenthes`, atau `default`), mendukung format PNG, WEBP, JPG/JPEG, dan SVG. Registri ikon memilih format dengan prioritas PNG > WEBP > JPG/JPEG > SVG dan menyematkan gambar sebagai data URI sehingga peta tetap berfungsi tanpa server aset terpisah.

### 4.2 Pengujian dan Evaluasi Kinerja

**a. Uji logika dan sensitivitas CA.** Simulasi dijalankan pada grid penuh 58 × 58 dengan satu sel pusat sebagai titik awal, 12 langkah, dan 40 nilai benih acak berbeda untuk setiap arah angin. Proyeksi posisi sel terbakar diukur sepanjang sumbu hembusan angin (positif = searah hembusan).

| Arah angin (dari) | Rata-rata sel terbakar | Sentroid proyeksi (sel) | Persentil 90 (sel) | Persentil 10 (sel) |
| --- | --- | --- | --- | --- |
| 0° (utara) | 106,5 | +1,09 | +5,72 | −3,75 |
| 90° (timur) | 97,9 | +2,02 | +6,27 | −2,36 |
| 180° (selatan) | 98,3 | +2,25 | +6,13 | −1,60 |
| 270° (barat) | 93,1 | +2,25 | +6,63 | −2,34 |

Tabel 3. Hasil uji sensitivitas arah angin (12 langkah, 40 benih, satu sel pusat).

Pada keempat arah, sentroid dan persentil 90 bergeser positif searah hembusan angin, sedangkan persentil 10 tetap negatif. Artinya, batas depan api memang anisotropik: penyebaran ke arah hembusan angin mencapai 5,7–6,6 sel (≈ 22–26 km) setelah 12 langkah, sedangkan sisi berlawanan angin tertinggal 1,6–3,8 sel. Sel terbakar mencakup 2,8–3,2% dari 3.364 sel. Variasi antarbenih cukup besar karena setiap penyulutan bersifat stokastik; karena itu kesimpulan diambil dari kecenderungan statistik, bukan dari satu lintasan tunggal.

**b. Uji kinerja komputasi.** Satu langkah CA pada grid 58 × 58 memerlukan waktu di bawah 2 milidetik; 12 langkah selesai dalam ≈ 0,014 detik pada mesin pengujian tim. Inferensi *Random Forest* untuk seluruh 3.364 sel memerlukan ≈ 0,5 detik melalui salinan NumPy dari hutan model. Kebutuhan komputasi didominasi oleh pengambilan data jaringan (Overpass dan iNaturalist), bukan oleh CA atau model. Karena itu, hasil inisialisasi disimpan dengan cache `st.cache_resource`: pembaruan slider atau panel tidak lagi mengulang pengambilan data, dan hanya tombol "Run simulation" yang memuat ulang.

**c. Uji integrasi data dan konvensi grid.** Koordinat lintang/bujur dipetakan ke sel dengan baris 0 di tepi utara dan indeks baris bertambah ke selatan. Uji unit memverifikasi bahwa pusat sel dapat dipetakan balik ke indeks yang sama, sehingga hotspot FIRMS, lokasi pengguna, dan overlay peta berada pada sel yang konsisten.

**d. Uji kinerja model ML.** Ekspor MODIS 7 hari (66.482 baris) disaring ke kotak demo menjadi 1.770 titik panas pada 8 hari, lalu menghasilkan 20.184 baris latih dan 6.728 baris uji (163 positif uji; laju positif 3,2%). Pada dua hari uji yang tidak pernah dilihat model, akurasi 0,975, presisi 0,443, *recall* 0,166 (ambang 0,5), ROC-AUC 0,883, dan PR-AUC 0,283. PR-AUC hampir sembilan kali laju positif menunjukkan model memberi peringkat yang berarti pada kelas minoritas, meskipun *recall* pada ambang 0,5 rendah—karena itu antarmuka menampilkan peta probabilitas bergradasi, bukan keputusan biner. Fitur terpenting adalah jarak ke titik panas hari sebelumnya (0,167), riwayat 3 hari (0,138), posisi baris (0,119), keselarasan angin (0,116), dan jumlah titik panas 7 hari (0,108).

Pada peta kotak demo, 23 sel (0,7%) melewati probabilitas 0,5 dengan nilai tertinggi 0,76, dan rata-rata probabilitas 0,036—hampir sama dengan laju positif teramati 3,2%, sehingga peta dapat dibaca sebagai probabilitas, bukan sekadar peringkat. Setelah pemeriksaan kebocoran label dan penggunaan pembagian temporal, angka-angka ini lebih rendah daripada versi awal prototipe, tetapi merupakan estimasi yang jujur untuk data yang tidak pernah dilihat model.

**e. Uji perangkat lunak.** Rangkaian uji `pytest` mencakup 69 pengujian pada modul CA, fitur, ML, mitigasi, ikon, mask daratan, dan asap integrasi, seluruhnya lulus dalam ≈ 15 detik. Pengujian mencakup batas probabilitas 0,15–0,60, arah keselarasan angin (searah hembusan bernilai 1, berlawanan 0, tegak lurus 0,5), ketetanggan Moore, sifat bahan bakar yang tidak dapat terbakar ulang, sel air yang tidak pernah menyala meski peluang penyulutan diset 1, sel `peat_risk` yang tetap dapat terbakar, akurasi jarak *distance transform*, kebocoran label pada fitur riwayat, kesesuaian fitur riwayat saat inferensi, penolakan model usang, kesesuaian keluaran salinan NumPy dengan scikit-learn, penyimpanan dan pemuatan model, mask daratan peta pulau, serta pemetaan ikon dan fallback ke `default`.

**f. Uji antarmuka.** Pada viewport 1600 px, kolom peta berukuran 671 px dan panel darurat 270 px; ketika panel dimatikan, peta melebar menjadi 973 px. Pemeriksaan di browser menunjukkan seluruh ubin peta dimuat dari `tile.openstreetmap.org` dan menutup penuh area peta tanpa celah. Waktu muat pertama bergantung pada pengambilan iNaturalist dan, bila cache OSM sudah kedaluwarsa (7 hari), Overpass; dengan cache tersedia inisialisasi selesai dalam hitungan detik. Rendering dasbor lengkap dengan dua peta terverifikasi tanpa pengecualian melalui pengujian Streamlit.

### 4.3 Analisis Kelayakan Implementasi

**Teknis.** Seluruh komponen berjalan di browser melalui Streamlit dan Folium, tanpa server GPU dan tanpa basis data. Model CA sangat ringan, sedangkan beban terbesar adalah ketersediaan jaringan dan kuota API publik. Ketergantungan pada Overpass API dan iNaturalist dapat digantikan data luring (stub) yang telah disediakan, sehingga demonstrasi tetap berjalan di lokasi tanpa internet; model terlatih dan subset titik panas juga disertakan di repositori.

**Ekonomi.** Perangkat lunak yang digunakan bersifat *open source* dan data yang dipakai bersifat publik, sehingga biaya pengadaan mendekati nol. Biaya operasional utama adalah koneksi internet dan waktu pemeliharaan.

**Operasional.** Antarmuka hanya memerlukan satu tombol untuk menjalankan simulasi; parameter angin dan jumlah langkah tersedia sebagai slider. Panel mitigasi menggunakan bahasa sederhana dan dapat dimatikan agar peta lebih luas. Untuk penggunaan lapangan, aplikasi masih memerlukan penyederhanaan alur dan pengujian bersama pengguna akhir.

**Keberlanjutan.** Parameter model terpusat pada satu berkas konfigurasi dan seluruh data dipisahkan dari kode, sehingga pembaruan data musiman atau penambahan takson tidak memerlukan perubahan arsitektur.

### 4.4 Dampak dan Potensi Implementasi

INSIGHT berpotensi menjadi alat bantu edukasi dan perencanaan di tingkat desa, sekolah, dan lembaga mitigasi: pengguna dapat menguji skenario "bagaimana jika angin berbalik arah" dan melihat sel mana yang perlu diprioritaskan. Integrasi lapisan flora-fauna memungkinkan diskusi dampak ekologis tidak berhenti pada luas area terbakar, tetapi juga mencakup habitat spesies terancam.

Pengembangan lanjutan yang paling bernilai adalah kalibrasi waktu langkah terhadap data kejadian nyata, penggunaan data gambut resmi (ketebalan dan tingkat kematangan), validasi terhadap perimeter kebakaran historis, serta penyediaan data FIRMS terbaru secara otomatis. Dengan kalibrasi tersebut, prototipe dapat berkembang dari model pengajaran menjadi alat pendukung keputusan yang lebih operasional.

### 4.5 Keterbatasan

1. **Waktu langkah belum terkalibrasi.** Satu langkah CA adalah satu iterasi pembaruan, bukan satuan waktu fisik. Klaim laju penyebaran karena itu bersifat relatif, bukan km/jam.
2. **Air hanya dimodelkan sebagai penghalang geometris.** Sel air dari mask OpenStreetMap tidak dapat terbakar sehingga sungai dan danau memotong batas depan api, tetapi kelembapan bahan bakar, penguapan, dan hambatan hidrologis lain belum dimodelkan, dan mask gambut dibangun dari titik pusat fitur OSM sehingga poligon gambut besar hanya terwakili satu sel.
3. **Model adalah potret satu jendela data.** Model terlatih (`models/risk_rf.joblib`, ≈ 4 MB) dan subset FIRMS (`data/raw/firms_hotspots.csv`, 138 KB) disertakan di repositori agar aplikasi langsung memakai prediksi model, tetapi keduanya membekukan ekspor 7 hari pada Oktober 2026. Untuk musim baru, jalankan `python -m src.train` dengan ekspor terbaru. Bila model tidak dapat dimuat, aplikasi otomatis memakai baseline heuristik dan menyatakan sumbernya di panel samping; bila berkas FIRMS tidak ada, fitur riwayat bernilai nol sehingga peta menjadi prediksi "tanpa titik panas terbaru".
4. **Peta Kalimantan bersifat indikatif.** Peta pulau memakai grid kasar dan heuristik, bukan CA atau model terlatih. Mask daratan hanya menghapus sel laut, bukan menggantikan model per sel.
5. **Tanpa GPS.** Lokasi pengguna dimasukkan manual; integrasi geolokasi peramban berada di luar cakupan versi ini.
6. **Belum ada validasi terhadap perimeter kebakaran nyata.** Akurasi spasial model belum diukur terhadap data satelit historis.

---

## 5. KESIMPULAN

1. Model probabilistik hibrida berhasil dirumuskan: aturan transisi CA dengan probabilitas 0,15–0,60 yang bergantung pada keselarasan angin dan status gambut menghasilkan batas depan api anisotropik, dengan penyebaran searah hembusan angin mencapai 5,7–6,6 sel setelah 12 langkah pada grid 58 × 58.
2. Prototipe perangkat lunak INSIGHT berhasil dibangun sebagai aplikasi web interaktif yang menyajikan peta sebaran flora-fauna endemik, peta risiko kotak demo hasil *Random Forest*, peta risiko Kalimantan, panel mitigasi, dan panel darurat dalam satu dasbor.
3. Lapisan *Machine Learning* terbukti dapat dipakai, bukan sekadar dirancang: dilatih pada 1.770 titik panas FIRMS nyata dan dievaluasi pada dua hari yang tidak pernah dilihat model, model mencapai ROC-AUC 0,883 dan PR-AUC 0,283, lalu memuat dirinya saat aplikasi dijalankan dan mengondisikan peta pada hari terakhir pengamatan.
4. Sistem pendukung keputusan berhasil diwujudkan pada tingkat prototipe: panduan mitigasi dipicu oleh jarak 2 sel (≈ 7,8 km) ke permukiman dan 3 sel (≈ 11,7 km) ke area pedesaan, serta dapat difokuskan pada lokasi pengguna.
5. Penerapan konsep fisika tampak pada pemetaan konveksi ke suku angin, radiasi ke probabilitas dasar, dan konduksi yang digabungkan pada skala sel, sehingga model tetap dapat dijelaskan sekaligus ringan dihitung.
6. Keterbatasan utama—kalibrasi waktu, penghalang air, dan validasi terhadap data kebakaran nyata—menjadi agenda pengembangan berikutnya.

---

## 6. DAFTAR PUSTAKA

[1] Basuki, I., et al., "Land Cover and Land Use Change Decreases Net Ecosystem Production in Tropical Peatlands of West Kalimantan, Indonesia", *Forests*, 12(11), 1587, 2021. https://doi.org/10.3390/f12111587

[2] World Bank, *The Cost of Fire: An Economic Analysis of Indonesia's 2015 Fire Crisis*, World Bank, Jakarta, 2016.

[3] Mongabay, "2019 fires in Indonesia were twice as bad as the government claimed, study shows", 16 Desember 2021. https://news.mongabay.com/2021/12/2019-fires-in-indonesia-were-twice-as-bad-as-the-government-claimed-study-shows/

[4] Felzenszwalb, P.F. & Huttenlocher, D.P., "Distance Transforms of Sampled Functions", *Theory of Computing*, 8(19), pp. 415–428, 2012.

[5] NASA FIRMS, *Fire Information for Resource Management System*, https://firms.modaps.eosdis.nasa.gov/, (21 Oktober 2026).

[6] OpenStreetMap contributors, *OpenStreetMap Copyright and License (ODbL)*, https://www.openstreetmap.org/copyright, (21 Oktober 2026).

[7] iNaturalist, *API v2 Reference*, https://api.inaturalist.org/v2/docs, (21 Oktober 2026).

[8] Breiman, L., "Random Forests", *Machine Learning*, 45, pp. 5–32, 2001.

[9] Pedregosa, F., et al., "Scikit-learn: Machine Learning in Python", *Journal of Machine Learning Research*, 12, pp. 2825–2830, 2011.

[10] Streamlit, *Streamlit Documentation*, https://docs.streamlit.io/, (21 Oktober 2026).

[11] Folium, *Folium Documentation*, https://python-visualization.github.io/folium/, (21 Oktober 2026).

[12] Natural Earth, *1:50m Land*, https://www.naturalearthdata.com/downloads/50m-physical-vectors/, (domain publik, 21 Oktober 2026).

---

## 7. LAMPIRAN

### 7.1 Pembagian Tugas dan Kontribusi

| Anggota | Peran | Kontribusi utama |
| --- | --- | --- |
| Atahya Rayyan Alghifari Yuwono | Ketua tim, pemodelan fisika | Formulasi aturan CA, analisis sensitivitas angin, penulisan naskah |
| Melvin Khaizuran | Data dan *Machine Learning* | Pipeline OSM/FIRMS/iNaturalist, tabel fitur, pelatihan dan evaluasi model |
| Prabu Ditya Irfahany | Perangkat lunak dan visualisasi | Antarmuka Streamlit, peta Folium, panel mitigasi, pengujian antarmuka |

Tabel 4. Pembagian tugas dan kontribusi anggota tim.

### 7.2 Rincian Kebutuhan Biaya

Proyek ini tidak memerlukan pengadaan perangkat keras maupun lisensi perangkat lunak. Seluruh komponen menggunakan perangkat pribadi anggota tim dan perangkat lunak *open source*, sehingga tidak ada pengeluaran yang direncanakan.

| No. | Komponen | Jumlah | Harga Satuan (Rp) | Total (Rp) |
| --- | --- | --- | --- | --- |
| 1 | Perangkat lunak (Python, Streamlit, Folium, scikit-learn) | — | 0 (open source) | 0 |
| 2 | Perangkat keras (laptop pribadi) | 3 | 0 (milik sendiri) | 0 |
| 3 | Data geospasial publik (OSM, FIRMS, iNaturalist, Natural Earth) | — | 0 (akses publik) | 0 |
| **Total** | | | | **Rp 0** |

Tabel 5. Rincian kebutuhan biaya.

### 7.3 Dokumentasi Kode dan Pengujian

Kode simulasi tersedia di repositori proyek dengan struktur:

- `src/config.py` — seluruh konstanta wilayah, CA, ML, dan ambang mitigasi;
- `src/ca.py` — grid, aturan transisi, pembenihan, dan penjelasan langkah;
- `src/features.py` — tabel fitur, riwayat titik panas, dan *distance transform*;
- `src/ml.py` — pelatihan *Random Forest*, metrik, dan peta risiko;
- `src/train.py` — CLI pelatihan dari ekspor FIRMS;
- `src/land_mask.py` — mask daratan peta pulau dan pembangun garis pantai;
- `src/mitigation.py` — aturan jarak dan panduan mitigasi;
- `src/icons.py` — registri ikon flora-fauna yang dapat diganti pengguna;
- `app/ca_simulator.py` — orkestrasi data, CA, model, dan mitigasi;
- `app/main.py` — antarmuka Streamlit dan peta Folium;
- `tests/` — 69 pengujian unit dan asap (`pytest`).

Berkas data mentah berukuran besar diletakkan di `data/raw/` dan tidak disertakan dalam repositori, sedangkan subset FIRMS yang dipakai aplikasi (`data/raw/firms_hotspots.csv`), model terlatih (`models/`), ikon kustom (`assets/icons/`), dan garis pantai (`assets/geo/`) disertakan agar aplikasi dapat dijalankan tanpa pelatihan ulang.
