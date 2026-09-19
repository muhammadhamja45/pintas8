/* Book 2 Management - shared vanilla JS helpers.
   Loaded on every page. No frameworks, no build step. */
(function () {
    "use strict";

    var App = window.App = {};

    /* ------------------------------------------------------------------
       DOM helpers
       ------------------------------------------------------------------ */
    function qs(sel, root) { return (root || document).querySelector(sel); }
    function qsa(sel, root) {
        return Array.prototype.slice.call((root || document).querySelectorAll(sel));
    }
    function el(tag, attrs, children) {
        var node = document.createElement(tag);
        Object.keys(attrs || {}).forEach(function (key) {
            if (key === "class") { node.className = attrs[key]; }
            else if (key === "text") { node.textContent = attrs[key]; }
            else if (key === "html") { node.innerHTML = attrs[key]; }
            else if (key.indexOf("on") === 0) { node.addEventListener(key.slice(2), attrs[key]); }
            else if (attrs[key] !== null && attrs[key] !== undefined) {
                node.setAttribute(key, attrs[key]);
            }
        });
        (children || []).forEach(function (child) {
            node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
        });
        return node;
    }
    App.qs = qs; App.qsa = qsa; App.el = el;

    /* Escape anything that came from the database before it touches innerHTML. */
    function esc(value) {
        if (value === null || value === undefined) { return ""; }
        return String(value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    }
    App.esc = esc;

    /* ------------------------------------------------------------------
       CSRF + API client
       ------------------------------------------------------------------ */
    function csrf() {
        var meta = qs('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }
    App.csrf = csrf;

    function request(method, url, body, isForm) {
        var opts = { method: method, headers: { "Accept": "application/json" },
                     credentials: "same-origin" };
        if (method !== "GET" && method !== "HEAD") {
            opts.headers["X-CSRF-Token"] = csrf();
        }
        if (isForm) {
            opts.body = body;
        } else if (body !== undefined && body !== null) {
            opts.headers["Content-Type"] = "application/json";
            opts.body = JSON.stringify(body);
        }
        return fetch(url, opts).then(function (res) {
            return res.json().catch(function () {
                return { success: false, message: "Respons server tidak valid.", errors: [] };
            }).then(function (payload) {
                if (!res.ok || payload.success === false) {
                    var err = new Error(payload.message || "Terjadi kesalahan.");
                    err.status = res.status;
                    err.errors = payload.errors || [];
                    throw err;
                }
                return payload;
            });
        });
    }

    App.api = {
        get: function (url) { return request("GET", url); },
        post: function (url, body) { return request("POST", url, body || {}); },
        put: function (url, body) { return request("PUT", url, body || {}); },
        del: function (url) { return request("DELETE", url); },
        upload: function (url, formData) { return request("POST", url, formData, true); }
    };

    /* ------------------------------------------------------------------
       Toast
       ------------------------------------------------------------------ */
    function toast(message, kind) {
        var box = qs("#toast-container");
        if (!box) {
            box = el("div", { id: "toast-container" });
            document.body.appendChild(box);
        }
        var node = el("div", { class: "toast is-" + (kind || "info"), text: message });
        box.appendChild(node);
        setTimeout(function () {
            node.style.opacity = "0";
            node.style.transition = "opacity .2s";
            setTimeout(function () { node.remove(); }, 220);
        }, 3800);
    }
    App.toast = toast;
    App.error = function (err) {
        var message = err && err.message ? err.message : "Terjadi kesalahan.";
        if (err && err.errors && err.errors.length) {
            message += " " + err.errors.join(" ");
        }
        toast(message, "danger");
    };

    /* ------------------------------------------------------------------
       Modal + confirmation
       ------------------------------------------------------------------ */
    function modal(options) {
        var opts = options || {};
        var backdrop = el("div", { class: "modal-backdrop" });
        var body = el("div", { class: "modal-body" });
        if (typeof opts.content === "string") { body.innerHTML = opts.content; }
        else if (opts.content) { body.appendChild(opts.content); }

        var foot = el("div", { class: "modal-foot" });
        var box = el("div", { class: "modal" + (opts.large ? " modal-lg" : "") }, [
            el("div", { class: "modal-head" }, [
                el("h3", { text: opts.title || "" }),
                el("button", { class: "modal-close", type: "button", "aria-label": "Tutup",
                               text: "×", onclick: close })
            ]),
            body, foot
        ]);
        backdrop.appendChild(box);

        (opts.buttons || []).forEach(function (spec) {
            foot.appendChild(el("button", {
                class: "btn " + (spec.class || "btn-outline"),
                type: "button",
                text: spec.label,
                onclick: function () { spec.onClick ? spec.onClick(close, box) : close(); }
            }));
        });

        function close() {
            document.removeEventListener("keydown", onKey);
            backdrop.remove();
        }
        function onKey(ev) { if (ev.key === "Escape") { close(); } }

        backdrop.addEventListener("click", function (ev) {
            if (ev.target === backdrop) { close(); }
        });
        document.addEventListener("keydown", onKey);
        document.body.appendChild(backdrop);
        var focusable = box.querySelector("input, textarea, select, button.btn");
        if (focusable) { focusable.focus(); }
        return { close: close, root: box };
    }
    App.modal = modal;

    /* Confirmation dialog. `reasonRequired` renders a mandatory note field. */
    function confirmDialog(opts) {
        return new Promise(function (resolve) {
            var wrap = el("div");
            if (opts.message) {
                wrap.appendChild(el("p", { text: opts.message, class: "mb-2" }));
            }
            var textarea = null, errorNode = null;
            if (opts.reason) {
                var field = el("div", { class: "field" });
                field.appendChild(el("label", {
                    for: "confirm-reason",
                    html: esc(opts.reasonLabel || "Alasan") +
                          (opts.reasonRequired ? ' <span class="required">*</span>' : "")
                }));
                textarea = el("textarea", { id: "confirm-reason",
                                            placeholder: opts.reasonPlaceholder || "" });
                field.appendChild(textarea);
                errorNode = el("div", { class: "field-error hidden" });
                field.appendChild(errorNode);
                wrap.appendChild(field);
            }

            var dialog = modal({
                title: opts.title || "Konfirmasi",
                content: wrap,
                buttons: [
                    { label: opts.cancelLabel || "Cancel", class: "btn-outline",
                      onClick: function (close) { close(); resolve(null); } },
                    { label: opts.confirmLabel || "Confirm",
                      class: opts.confirmClass || "btn",
                      onClick: function (close) {
                          var value = textarea ? textarea.value.trim() : "";
                          if (opts.reasonRequired && !value) {
                              errorNode.textContent = "Alasan wajib diisi.";
                              errorNode.classList.remove("hidden");
                              textarea.classList.add("input-invalid");
                              textarea.focus();
                              return;
                          }
                          close();
                          resolve({ note: value });
                      } }
                ]
            });
            void dialog;
        });
    }
    App.confirm = confirmDialog;

    /* ------------------------------------------------------------------
       Formatting
       ------------------------------------------------------------------ */
    App.statusLabel = function (status) {
        return (window.STATUS_LABELS && window.STATUS_LABELS[status]) || status || "-";
    };
    App.roleLabel = function (role) {
        return (window.ROLE_LABELS && window.ROLE_LABELS[role]) || role || "-";
    };
    App.statusBadge = function (status) {
        var tone = (window.STATUS_TONES && window.STATUS_TONES[status]) || "muted";
        return '<span class="badge badge-' + tone + '">' + esc(App.statusLabel(status)) +
               "</span>";
    };
    App.fileSize = function (bytes) {
        var value = Number(bytes || 0), units = ["B", "KB", "MB", "GB"], i = 0;
        while (value >= 1024 && i < units.length - 1) { value /= 1024; i += 1; }
        return (i === 0 ? value.toFixed(0) : value.toFixed(1)) + " " + units[i];
    };
    App.dash = function (value) { return (value === null || value === undefined ||
                                          value === "") ? "-" : value; };

    /* Loading / empty / error rows for tables. */
    App.rowState = function (tbody, colspan, kind, message, onRetry) {
        tbody.innerHTML = "";
        var td = el("td", { colspan: colspan });
        if (kind === "loading") {
            td.innerHTML = '<span class="spinner"></span> Loading...';
        } else if (kind === "empty") {
            td.innerHTML = '<span class="empty-icon">\u{1F4C4}</span>' +
                           esc(message || "Belum ada data.");
        } else {
            td.innerHTML = esc(message || "Data gagal dimuat.") + " ";
            var btn = el("button", { class: "btn btn-sm btn-outline", type: "button",
                                     text: "Coba lagi" });
            if (onRetry) { btn.addEventListener("click", onRetry); }
            td.appendChild(btn);
        }
        tbody.appendChild(el("tr", { class: "state-row" }, [td]));
    };

    /* ------------------------------------------------------------------
       Pagination renderer
       ------------------------------------------------------------------ */
    App.renderPagination = function (container, meta, onGo) {
        if (!container) { return; }
        container.innerHTML = "";
        if (!meta || !meta.total) { return; }

        var from = (meta.page - 1) * meta.per_page + 1;
        var to = Math.min(meta.page * meta.per_page, meta.total);
        container.appendChild(el("div", { class: "small muted",
            text: "Menampilkan " + from + "-" + to + " dari " + meta.total + " data" }));

        var pages = el("div", { class: "pages" });
        function pageBtn(label, target, disabled, active) {
            return el("button", {
                type: "button", text: label,
                class: active ? "active" : "",
                disabled: disabled ? "disabled" : null,
                onclick: function () { if (!disabled && !active) { onGo(target); } }
            });
        }
        pages.appendChild(pageBtn("‹", meta.page - 1, !meta.has_prev, false));
        var start = Math.max(1, meta.page - 2);
        var end = Math.min(meta.pages, start + 4);
        start = Math.max(1, Math.min(start, end - 4));
        for (var i = start; i <= end; i += 1) {
            pages.appendChild(pageBtn(String(i), i, false, i === meta.page));
        }
        pages.appendChild(pageBtn("›", meta.page + 1, !meta.has_next, false));
        container.appendChild(pages);
    };

    /* Build a query string, dropping empty values. */
    App.qsBuild = function (params) {
        var parts = [];
        Object.keys(params).forEach(function (key) {
            var value = params[key];
            if (value === null || value === undefined || value === "") { return; }
            if (Array.isArray(value)) {
                value.forEach(function (item) {
                    parts.push(encodeURIComponent(key) + "=" + encodeURIComponent(item));
                });
            } else {
                parts.push(encodeURIComponent(key) + "=" + encodeURIComponent(value));
            }
        });
        return parts.length ? "?" + parts.join("&") : "";
    };

    /* Debounce for search inputs. */
    App.debounce = function (fn, wait) {
        var timer;
        return function () {
            var args = arguments, ctx = this;
            clearTimeout(timer);
            timer = setTimeout(function () { fn.apply(ctx, args); }, wait || 350);
        };
    };

    /* Disable a button while a promise runs, restoring its label afterwards. */
    App.busy = function (button, promise, busyLabel) {
        if (!button) { return promise; }
        var original = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span class="spinner"></span>' + (busyLabel || "Memproses...");
        return promise.finally(function () {
            button.disabled = false;
            button.innerHTML = original;
        });
    };

    /* ------------------------------------------------------------------
       Global behaviours
       ------------------------------------------------------------------ */
    document.addEventListener("DOMContentLoaded", function () {
        // public navbar hamburger
        var navToggle = qs(".nav-toggle");
        if (navToggle) {
            navToggle.addEventListener("click", function () {
                var nav = qs(".public-nav");
                var open = nav.classList.toggle("open");
                navToggle.setAttribute("aria-expanded", String(open));
            });
        }

        // show/hide password
        qsa(".password-toggle").forEach(function (button) {
            button.addEventListener("click", function () {
                var input = document.getElementById(button.dataset.target);
                if (!input) { return; }
                var hidden = input.type === "password";
                input.type = hidden ? "text" : "password";
                button.textContent = hidden ? "Hide" : "Show";
            });
        });

        // dropdowns (notifications, profile)
        qsa("[data-dropdown]").forEach(function (trigger) {
            var menu = document.getElementById(trigger.dataset.dropdown);
            if (!menu) { return; }
            trigger.addEventListener("click", function (ev) {
                ev.stopPropagation();
                var isOpen = !menu.classList.contains("hidden");
                qsa(".dropdown-menu").forEach(function (m) { m.classList.add("hidden"); });
                if (!isOpen) {
                    menu.classList.remove("hidden");
                    if (trigger.dataset.onopen && window[trigger.dataset.onopen]) {
                        window[trigger.dataset.onopen]();
                    }
                }
            });
            menu.addEventListener("click", function (ev) { ev.stopPropagation(); });
        });
        document.addEventListener("click", function () {
            qsa(".dropdown-menu").forEach(function (m) { m.classList.add("hidden"); });
        });

        // sidebar collapse / mobile drawer
        var sidebarToggle = qs("#sidebar-toggle");
        if (sidebarToggle) {
            if (localStorage.getItem("sidebarCollapsed") === "1") {
                document.body.classList.add("sidebar-collapsed");
            }
            sidebarToggle.addEventListener("click", function () {
                if (window.innerWidth <= 992) {
                    document.body.classList.toggle("sidebar-open");
                } else {
                    var collapsed = document.body.classList.toggle("sidebar-collapsed");
                    localStorage.setItem("sidebarCollapsed", collapsed ? "1" : "0");
                }
            });
        }
        var scrim = qs(".sidebar-scrim");
        if (scrim) {
            scrim.addEventListener("click", function () {
                document.body.classList.remove("sidebar-open");
            });
        }

        // tabs
        qsa("[data-tabs]").forEach(function (group) {
            var buttons = qsa("button[data-tab]", group);
            buttons.forEach(function (button) {
                button.addEventListener("click", function () {
                    buttons.forEach(function (b) { b.classList.remove("active"); });
                    button.classList.add("active");
                    qsa("[data-panel]").forEach(function (panel) {
                        if (panel.dataset.panel === button.dataset.tab) {
                            panel.classList.remove("hidden");
                        } else if (buttons.some(function (b) {
                            return b.dataset.tab === panel.dataset.panel;
                        })) {
                            panel.classList.add("hidden");
                        }
                    });
                });
            });
        });
    });
}());
