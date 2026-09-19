# flipbook.js

Menampilkan file PDF sebagai buku yang bisa dibalik halamannya (page-flip), di dalam modal `App.modal`.

Lokasi: [flipbook.js](app/static/js/flipbook.js)

## Dependensi
- **pdf.js** (`pdfjsLib`) — merender tiap halaman PDF ke `<canvas>`, lalu diubah jadi gambar JPEG (data URL).
- **StPageFlip** (`St.PageFlip`) — animasi flip buku dari kumpulan gambar.
- `App.modal` — dari `app.js`, dipakai untuk membuka jendela modal tempat flipbook ditampilkan.

Kedua library eksternal ini harus sudah dimuat (via `<script>`) sebelum `flipbook.js` dijalankan.

## Cara pakai
Skrip ini hanya dimuat di halaman yang membutuhkan (lihat `page_scripts` masing-masing template), lalu dipanggil lewat:

```js
App.openFlipbook(pdfUrl, title);
```

Contoh pemakaian nyata:
- [home.html:167](app/templates/public/home.html#L167) — `App.openFlipbook(button.dataset.url, button.dataset.title)`
- [request_detail.html:683](app/templates/dash/request_detail.html#L683) — `App.openFlipbook("/api/files/" + button.dataset.flipFile, button.dataset.flipTitle)`

Biasanya dipicu dari tombol dengan `data-url`/`data-title` (atau `data-flip-file`/`data-flip-title`) di HTML.

## Alur kerja

1. **`openFlipbook(pdfUrl, title)`**
   - Membuka `App.modal` (mode `large`) berisi placeholder `"Memuat halaman..."` dan tombol "Tutup".
   - Memuat dokumen PDF dari `pdfUrl` via `pdfjsLib.getDocument`.
   - Merender setiap halaman **secara berurutan** (pakai `reduce` + `Promise` chain, bukan paralel — supaya urutan halaman terjaga) menjadi array data URL gambar lewat `renderPage`.
   - Setelah semua halaman selesai dirender, membuat instance `St.PageFlip` di dalam stage modal dan memuat gambar-gambar tersebut dengan `flip.loadFromImages(images)`.
   - Jika gagal (PDF tidak bisa dimuat/dirender), pesan error ditampilkan di dalam stage.

2. **`renderPage(pdf, num)`**
   - Mengambil satu halaman (`pdf.getPage(num)`), merendernya ke `<canvas>` dengan skala `1.5`, lalu mengembalikan `canvas.toDataURL("image/jpeg", 0.85)`.

## Konfigurasi PageFlip

```js
{ width: 500, height: 700, size: "stretch",
  minWidth: 300, maxWidth: 1000, minHeight: 400, maxHeight: 1400,
  showCover: false }
```

`size: "stretch"` membuat buku menyesuaikan ukuran stage modal, dibatasi oleh min/max width-height di atas.

## Catatan
- Worker pdf.js diarahkan ke CDN cloudflare (`pdf.worker.min.js` versi 3.11.174) — lihat baris 7-10.
- Rendering halaman dilakukan berurutan, jadi PDF dengan banyak halaman akan terasa lambat sebelum flipbook muncul (tidak ada progress per-halaman, hanya teks "Memuat halaman...").
- `App.openFlipbook` didaftarkan sebagai fungsi global di `window.App`.
