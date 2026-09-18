/* Renders a PDF as a page-flip book inside an App.modal, using pdf.js (render
   pages to canvas) and page-flip / StPageFlip (the flip animation). Loaded
   only on pages that need it (home, request detail) - see their page_scripts. */
(function () {
    "use strict";

    if (window.pdfjsLib) {
        pdfjsLib.GlobalWorkerOptions.workerSrc =
            "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    }

    function renderPage(pdf, num) {
        return pdf.getPage(num).then(function (page) {
            var viewport = page.getViewport({ scale: 1.5 });
            var canvas = document.createElement("canvas");
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            return page.render({ canvasContext: canvas.getContext("2d"), viewport: viewport })
                .promise.then(function () { return canvas.toDataURL("image/jpeg", 0.85); });
        });
    }

    function openFlipbook(pdfUrl, title) {
        var modal = App.modal({
            title: title || "Flipbook",
            large: true,
            content: '<div class="flipbook-stage" id="flipbook-stage">Memuat halaman...</div>',
            buttons: [{ label: "Tutup", class: "btn-outline" }]
        });
        var stage = modal.root.querySelector("#flipbook-stage");

        pdfjsLib.getDocument(pdfUrl).promise.then(function (pdf) {
            var pages = [];
            for (var i = 1; i <= pdf.numPages; i++) { pages.push(i); }
            return pages.reduce(function (chain, num) {
                return chain.then(function (images) {
                    return renderPage(pdf, num).then(function (img) {
                        images.push(img);
                        return images;
                    });
                });
            }, Promise.resolve([]));
        }).then(function (images) {
            stage.innerHTML = "";
            var flip = new St.PageFlip(stage, {
                width: 500, height: 700, size: "stretch",
                minWidth: 300, maxWidth: 1000, minHeight: 400, maxHeight: 1400,
                showCover: false
            });
            flip.loadFromImages(images);
        }).catch(function (err) {
            stage.textContent = "Gagal memuat PDF: " + (err && err.message ? err.message : err);
        });
    }

    window.App = window.App || {};
    App.openFlipbook = openFlipbook;
}());
