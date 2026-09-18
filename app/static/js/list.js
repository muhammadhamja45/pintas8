/* Reusable server-side list: filters + sort + pagination against a JSON endpoint.
   Used by every request/order/user/audit table so no page re-implements it. */
(function () {
    "use strict";

    function ListTable(options) {
        this.endpoint = options.endpoint;
        this.body = document.getElementById(options.tableId + "-body");
        this.pager = document.getElementById(options.tableId + "-pagination");
        this.table = document.getElementById(options.tableId);
        this.columns = options.columns;          // number of <th>
        this.renderRow = options.renderRow;      // (item) -> html string
        this.baseParams = options.params || {};  // fixed filters (e.g. status list)
        this.filters = options.filters || {};    // id -> query key
        this.sort = options.sort || "created_at";
        this.direction = options.direction || "desc";
        this.perPage = options.perPage || 10;
        this.emptyMessage = options.emptyMessage || "Belum ada data.";
        this.onLoaded = options.onLoaded;
        this.page = 1;
        this.bind();
        this.load();
    }

    ListTable.prototype.bind = function () {
        var self = this;
        Object.keys(this.filters).forEach(function (id) {
            var node = document.getElementById(id);
            if (!node) { return; }
            var handler = function () { self.page = 1; self.load(); };
            node.addEventListener(node.tagName === "SELECT" || node.type === "date"
                ? "change" : "input",
                node.tagName === "SELECT" || node.type === "date"
                    ? handler : App.debounce(handler, 350));
        });

        if (this.table) {
            App.qsa("th.sortable", this.table).forEach(function (th) {
                th.addEventListener("click", function () {
                    var key = th.dataset.sort;
                    if (self.sort === key) {
                        self.direction = self.direction === "asc" ? "desc" : "asc";
                    } else {
                        self.sort = key;
                        self.direction = "asc";
                    }
                    self.page = 1;
                    self.load();
                });
            });
        }
    };

    ListTable.prototype.params = function () {
        var params = {};
        Object.keys(this.baseParams).forEach(function (key) {
            params[key] = this.baseParams[key];
        }, this);
        Object.keys(this.filters).forEach(function (id) {
            var node = document.getElementById(id);
            if (node && node.value) { params[this.filters[id]] = node.value; }
        }, this);
        params.sort = this.sort;
        params.direction = this.direction;
        params.page = this.page;
        params.per_page = this.perPage;
        return params;
    };

    ListTable.prototype.load = function () {
        var self = this;
        App.rowState(this.body, this.columns, "loading");
        if (this.table) {
            App.qsa("th.sortable", this.table).forEach(function (th) {
                th.classList.remove("asc", "desc");
                if (th.dataset.sort === self.sort) { th.classList.add(self.direction); }
            });
        }

        App.api.get(this.endpoint + App.qsBuild(this.params())).then(function (res) {
            var items = res.data.items || [];
            if (!items.length) {
                App.rowState(self.body, self.columns, "empty", self.emptyMessage);
            } else {
                self.body.innerHTML = items.map(self.renderRow).join("");
            }
            App.renderPagination(self.pager, res.data, function (page) {
                self.page = page;
                self.load();
                window.scrollTo({ top: 0, behavior: "smooth" });
            });
            if (self.onLoaded) { self.onLoaded(items, res.data, self.body); }
        }).catch(function (err) {
            App.rowState(self.body, self.columns, "error",
                err.message || "Data gagal dimuat. Coba lagi.",
                function () { self.load(); });
        });
    };

    ListTable.prototype.reload = function () { this.load(); };

    window.ListTable = ListTable;
}());
