/* MathAlign68 — the whole front end.
 *
 * Reads the payload embedded in <script id="D">, which is byte-identical to the
 * published data.json. Everything is computed here rather than baked into the
 * payload, so the data file stays a plain description of the items and the
 * aggregates cannot disagree with it.
 *
 * There is no question text anywhere in this file, on purpose. See README. */
(function () {
  "use strict";

  var D = JSON.parse(document.getElementById("D").textContent);

  /* The correction form's markup, captured once and then removed from the
     document. Every tab is rendered by clearing #view, so MOVING the original
     node into the About view worked exactly once: switching to another tab
     destroyed it, and coming back found nothing. Injecting a fresh copy each
     time is robust, and it costs nothing -- Netlify detects forms by scanning
     the deployed HTML file at build time, so what the page does with the node
     afterwards is irrelevant. */
  var FORM_HTML = "";
  (function () {
    var original = document.getElementById("fb");
    if (original) {
      FORM_HTML = original.outerHTML;
      original.parentNode.removeChild(original);
    }
  })();
  var STATE = { grade: 7, view: "questions" };

  /* ------------------------------------------------------------- utilities */

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }
  function frag() { return document.createDocumentFragment(); }
  function pct(v) { return (v * 100).toFixed(0) + "%"; }
  function mean(a) { return a.length ? a.reduce(function (x, y) { return x + y; }, 0) / a.length : null; }
  function uniq(a) { return a.filter(function (v, i) { return a.indexOf(v) === i; }); }

  // One shared vocabulary for "how hard was this", used by every view so the
  // colours mean the same thing everywhere.
  function band(p) { return p < 0.5 ? "hard" : (p < 0.75 ? "mid" : "easy"); }

  function pCell(p) {
    var w = el("span", "p " + band(p));
    var bar = el("span", "bar"), fill = el("i");
    fill.style.width = Math.max(2, Math.round(p * 100)) + "%";
    bar.appendChild(fill);
    w.appendChild(bar);
    w.appendChild(el("span", "v", p.toFixed(2)));
    return w;
  }

  /* One <select> in a .controls row. Lifted out of viewItems, which owned the
     only copy while viewQuestions, viewStandards and viewCurriculum each
     hand-rolled the same dozen lines. `host` is the .controls div to append to. */
  function picker(host, label, values, render) {
    var sel = el("select");
    var any = el("option", "", "All"); any.value = ""; sel.appendChild(any);
    values.forEach(function (v) {
      var o = el("option", "", render ? render(v) : v); o.value = v; sel.appendChild(o);
    });
    var l = el("label"); l.appendChild(el("span", "", label)); l.appendChild(sel);
    host.appendChild(l);
    return sel;
  }

  function searchBox(host, placeholder) {
    var input = el("input");
    input.type = "search";
    input.placeholder = placeholder;
    var l = el("label", "grow");
    l.appendChild(input);
    host.appendChild(l);
    return input;
  }

  function itemsFor(grade) {
    return D.items.filter(function (i) { return i.grade === grade; });
  }
  function testsFor(grade) {
    return D.tests.filter(function (t) { return t.grade === grade; });
  }

  function pdfLink(item, label) {
    if (!item.sourceUrl) return el("span", "", "—");
    var a = el("a", "", label || (item.pdfPage ? "p." + item.pdfPage : "PDF"));
    a.href = item.sourceUrl;
    a.target = "_blank";
    a.rel = "noopener";
    a.title = item.pdfPage
      ? "Open the official released-items PDF at page " + item.pdfPage
      : "Open the official released-items PDF (this item's page could not be determined)";
    return a;
  }

  function typeTag(item) {
    var t = el("span", "tag " + (item.type === "Multiple Choice" ? "mc" : "cr"),
               item.type === "Multiple Choice" ? "MC" : item.credits + "-cr CR");
    return t;
  }

  /* Sortable table. Columns declare how to render and how to sort, so no view
     re-implements either. */
  /* A sortable table.

     SORT IS A STACK, not a single key. Click a heading to sort by it;
     SHIFT-click to add it as a further level, or to flip a level already in the
     stack. One standard can be tested across four years at three difficulties,
     so "unit, then hardest first" is the question a teacher actually has, and a
     single key cannot express it. Ties used to fall through to whatever order
     `rows` happened to arrive in; now the tiebreak is the reader's to choose.

     `opts.sortKey` stays a plain string, so all ten existing call sites keep
     working untouched. */
  function table(cols, rows, opts) {
    opts = opts || {};
    /* The sort readout sits OUTSIDE the horizontally-scrolling box. Inside it,
       a table wider than the viewport scrolls the sentence out of view with the
       columns, so "Sorted by Year" rendered as "ted by Year". */
    var wrapper = el("div");
    var scroll = el("div", "scroll");
    var bar = el("p", "sortbar");
    var t = el("table"), thead = el("thead"), tr = el("tr");
    var sortable = cols.filter(function (c) { return c.sort !== false; }).length;
    var sort = [];
    if (opts.sortKey) sort.push({ key: opts.sortKey, dir: opts.sortDir || 1 });

    function levelOf(key) {
      for (var i = 0; i < sort.length; i++) if (sort[i].key === key) return i;
      return -1;
    }

    cols.forEach(function (c) {
      var th = el("th", (c.num ? "num " : "") + (c.sort === false ? "plain" : ""));
      th.appendChild(el("span", "", c.label));
      var mark = el("span", "sortmark");
      th.appendChild(mark);
      if (c.sort !== false) {
        th.title = (c.title ? c.title + " \u2014 " : "") +
                   "Click to sort. Shift-click to add another level.";
        th.addEventListener("click", function (e) {
          var at = levelOf(c.key);
          if (e.shiftKey) {
            if (at >= 0) sort[at].dir = -sort[at].dir;
            else sort.push({ key: c.key, dir: c.desc ? -1 : 1 });
          } else if (sort.length === 1 && at === 0) {
            sort = [{ key: c.key, dir: -sort[0].dir }];
          } else {
            sort = [{ key: c.key, dir: c.desc ? -1 : 1 }];
          }
          draw();
        });
      } else if (c.title) {
        th.title = c.title;
      }
      tr.appendChild(th);
    });
    thead.appendChild(tr);
    t.appendChild(thead);
    var tbody = el("tbody");
    t.appendChild(tbody);
    if (sortable) wrapper.appendChild(bar);
    scroll.appendChild(t);
    wrapper.appendChild(scroll);

    function labelFor(key) {
      var col = cols.filter(function (c) { return c.key === key; })[0];
      return col ? col.label : key;
    }

    function readout() {
      bar.textContent = "";
      if (!sort.length) {
        bar.appendChild(el("span", "muted", "Unsorted \u00b7 click a heading to sort, "
                           + "shift-click to add a level"));
        return;
      }
      var words = sort.map(function (s, i) {
        return (i ? "then " : "Sorted by ") + labelFor(s.key) +
               (s.dir > 0 ? "" : " (descending)");
      }).join(", ");
      bar.appendChild(el("span", "muted", words));
      if (sort.length > 1 || !opts.sortKey || sort[0].key !== opts.sortKey
          || sort[0].dir !== (opts.sortDir || 1)) {
        var reset = el("button", "linkish", "reset");
        reset.type = "button";
        reset.addEventListener("click", function () {
          sort = opts.sortKey ? [{ key: opts.sortKey, dir: opts.sortDir || 1 }] : [];
          draw();
        });
        bar.appendChild(document.createTextNode(" \u00b7 "));
        bar.appendChild(reset);
      }
    }

    function compare(spec, a, b) {
      var col = cols.filter(function (c) { return c.key === spec.key; })[0];
      var x = col && col.value ? col.value(a) : a[spec.key];
      var y = col && col.value ? col.value(b) : b[spec.key];
      /* Missing values sink, whichever way the column is pointing -- a blank
         is not "the smallest", it is absent. */
      if (x === null || x === undefined) return (y === null || y === undefined) ? 0 : 1;
      if (y === null || y === undefined) return -1;
      if (x === y) return 0;
      return (x > y ? 1 : -1) * spec.dir;
    }

    function draw() {
      Array.prototype.forEach.call(thead.querySelectorAll("th"), function (th, i) {
        var at = levelOf(cols[i].key);
        var mark = th.querySelector(".sortmark");
        if (at < 0) {
          th.removeAttribute("aria-sort");
          mark.textContent = "";
          return;
        }
        th.setAttribute("aria-sort", sort[at].dir > 0 ? "ascending" : "descending");
        mark.textContent = (sort[at].dir > 0 ? "\u25b2" : "\u25bc") +
                           (sort.length > 1 ? String(at + 1) : "");
      });
      readout();
      var data = rows.slice();
      if (sort.length) {
        data.sort(function (a, b) {
          for (var i = 0; i < sort.length; i++) {
            var c = compare(sort[i], a, b);
            if (c) return c;
          }
          return 0;
        });
      }
      tbody.textContent = "";
      var f = frag();
      data.forEach(function (row) {
        var r = el("tr");
        cols.forEach(function (c) {
          var td = el("td", (c.num ? "num " : "") + (c.wrap ? "wrap-ok" : ""));
          var out = c.render ? c.render(row) : row[c.key];
          if (out instanceof Node) td.appendChild(out);
          else td.textContent = (out === null || out === undefined) ? "—" : String(out);
          r.appendChild(td);
        });
        f.appendChild(r);
      });
      tbody.appendChild(f);
    }
    draw();
    return wrapper;
  }

  /* -------------------------------------------------- per-standard rollups */

  function standardRollup(grade) {
    var items = itemsFor(grade);
    var byCode = {};
    items.forEach(function (i) {
      (byCode[i.standard] = byCode[i.standard] || []).push(i);
    });

    var out = [];
    Object.keys(D.standards).forEach(function (code) {
      var reg = D.standards[code];
      if (reg.assessedOnGrades.indexOf(grade) === -1) return;
      var mine = byCode[code] || [];
      var ps = mine.map(function (i) { return i.pValue; });
      out.push({
        code: code,
        reg: reg,
        items: mine.sort(function (a, b) { return a.year - b.year || a.item - b.item; }),
        n: mine.length,
        credits: mine.reduce(function (s, i) { return s + i.credits; }, 0),
        years: uniq(mine.map(function (i) { return i.year; })).sort(),
        meanP: mean(ps),
        minP: ps.length ? Math.min.apply(null, ps) : null,
        maxP: ps.length ? Math.max.apply(null, ps) : null,
        maxCredits: mine.reduce(function (m, i) { return Math.max(m, i.credits); }, 0),
        crCount: mine.filter(function (i) { return i.type !== "Multiple Choice"; }).length
      });
    });
    return out;
  }

  /* --------------------------------------------------------------- headline */

  function renderStats(grade) {
    var host = document.getElementById("stats");
    host.textContent = "";
    var items = itemsFor(grade), tests = testsFor(grade);
    var roll = standardRollup(grade);
    var ps = items.map(function (i) { return i.pValue; });
    var hard = roll.filter(function (s) { return s.n >= 3 && s.meanP !== null && s.meanP < 0.5; });
    var never = roll.filter(function (s) { return s.n === 0; });

    [[items.length, "released items"],
     [tests.length + " tests", D.meta.years[0] + "–" + D.meta.years[D.meta.years.length - 1]],
     [items.reduce(function (s, i) { return s + i.credits; }, 0), "credits"],
     [ps.length ? mean(ps).toFixed(2) : "—", "mean statewide P-value"],
     [hard.length, "standards hard every year"],
     [never.length, "standards never released"],
     [items.filter(function (i) { return i.postTest; }).length, "prior-grade items"],
     [items.filter(function (i) { return i.transcribed; }).length, "questions transcribed"]
    ].forEach(function (pair) {
      var s = el("div", "stat");
      s.appendChild(el("span", "n", pair[0]));
      s.appendChild(el("span", "l", pair[1]));
      host.appendChild(s);
    });
  }

  /* ------------------------------------------------------------- standards */

  function viewStandards(grade) {
    var host = frag();
    var roll = standardRollup(grade);

    var card = el("div", "card");
    card.appendChild(el("h2", "", "What the state has asked about, standard by standard"));
    card.appendChild(el("p", "lede",
      "Every standard the grade " + grade + " test can assess, with each released item that has " +
      "tested it and how hard New York State as a whole found it. A standard with no released " +
      "item has not necessarily gone untested — roughly a quarter of each test is withheld."));
    host.appendChild(card);

    var controls = el("div", "controls");
    var sel = el("select");
    [["hardest", "Hardest first"], ["code", "Standard code"], ["most", "Most items first"],
     ["fewest", "Fewest items first"]].forEach(function (o) {
      var opt = el("option", "", o[1]); opt.value = o[0]; sel.appendChild(opt);
    });
    var search = el("input");
    search.type = "search";
    search.placeholder = "Filter by code, domain or wording";
    var lab1 = el("label"); lab1.appendChild(el("span", "", "Order")); lab1.appendChild(sel);
    var lab2 = el("label"); lab2.appendChild(search);
    controls.appendChild(lab1); controls.appendChild(lab2);
    host.appendChild(controls);

    var list = el("div");
    host.appendChild(list);

    function paint() {
      var q = search.value.trim().toLowerCase();
      var rows = roll.filter(function (s) {
        if (!q) return true;
        return (s.code + " " + (s.reg.domainName || "") + " " + (s.reg.clusterText || ""))
          .toLowerCase().indexOf(q) !== -1;
      });
      var mode = sel.value;
      rows.sort(function (a, b) {
        if (mode === "code") return a.code < b.code ? -1 : 1;
        if (mode === "most") return b.n - a.n || (a.code < b.code ? -1 : 1);
        if (mode === "fewest") return a.n - b.n || (a.code < b.code ? -1 : 1);
        // hardest: unreleased standards last, since they have no difficulty
        if (a.meanP === null && b.meanP === null) return a.code < b.code ? -1 : 1;
        if (a.meanP === null) return 1;
        if (b.meanP === null) return -1;
        return a.meanP - b.meanP;
      });

      list.textContent = "";
      if (!rows.length) { list.appendChild(el("p", "empty", "Nothing matches that filter.")); return; }
      var f = frag();
      rows.forEach(function (s) { f.appendChild(standardCard(s, grade)); });
      list.appendChild(f);
    }
    sel.addEventListener("change", paint);
    search.addEventListener("input", paint);
    paint();
    return host;
  }

  function standardCard(s, grade) {
    var box = el("div", "std");
    var head = el("div", "std-head");
    head.appendChild(el("span", "code", s.code));
    head.appendChild(el("span", "dom", s.reg.domainName || s.reg.domain));
    if (s.reg.postTest) {
      var t = el("span", "tag post", "post-test · taught in grade " + s.reg.grade);
      t.title = D.blueprint.postTestLegend;
      head.appendChild(t);
    }
    if (s.reg.note) head.appendChild(el("span", "tag", s.reg.note));
    if (s.n === 0) head.appendChild(el("span", "tag never", "no released item"));
    box.appendChild(head);

    if (s.reg.clusterText) {
      var c = el("p", "cluster", s.reg.clusterText);
      c.title = "NYSED publishes cluster descriptions, not per-standard wording. " +
                "This is the cluster this standard belongs to.";
      box.appendChild(c);
    }

    var row = el("div", "row");
    function bit(label, value) {
      var d = el("span");
      d.appendChild(el("b", "", value));
      d.appendChild(document.createTextNode(" " + label));
      row.appendChild(d);
    }
    if (s.n === 0) {
      row.appendChild(el("span", "", "Not among the released items for 2023–2026."));
    } else {
      bit("released items", s.n);
      bit("credits", s.credits);
      bit(s.years.length === 1 ? "year" : "of 4 years", s.years.length);
      bit("mean P-value", s.meanP.toFixed(2));
      if (s.n > 1) bit("spread", s.minP.toFixed(2) + "–" + s.maxP.toFixed(2));
      if (s.crCount) bit("constructed response", s.crCount + " of " + s.n);
      if (s.maxCredits > 1) bit("credit item seen", "up to a " + s.maxCredits + "-");
    }
    box.appendChild(row);

    if (s.n) {
      var det = el("details");
      det.appendChild(el("summary", "", "The " + s.n + " released item" + (s.n === 1 ? "" : "s")));
      det.appendChild(table([
        { key: "year", label: "Year", num: true },
        { key: "item", label: "Item", num: true },
        { key: "session", label: "Sess", num: true },
        { key: "type", label: "Type", render: typeTag },
        { key: "credits", label: "Cr", num: true },
        { key: "key", label: "Key", render: function (i) { return i.key || "—"; } },
        { key: "pValue", label: "Statewide", render: function (i) { return pCell(i.pValue); } },
        { key: "avgPointsEarned", label: "Avg pts", num: true,
          title: "Average points earned, for constructed-response items",
          render: function (i) { return i.avgPointsEarned === null ? "—" : i.avgPointsEarned.toFixed(2); } },
        { key: "pdfPage", label: "Official PDF", sort: false, render: function (i) { return pdfLink(i); } }
      ], s.items, { sortKey: "year" }));
      box.appendChild(det);
    }
    return box;
  }


  /* ------------------------------------------------------------- questions */

  /* The card browser. This is RegentsAlign's flagship view and the reason a
     teacher opens either site: the question itself, next to what the state
     asked and how hard everyone found it.

     Only transcribed items appear here. An item without a transcription still
     exists everywhere else in the site with its standard, its P-value and a
     link to the PDF, so partial coverage looks partial rather than broken. */

  function viewQuestions(grade) {
    var host = frag();
    var all = itemsFor(grade).filter(function (i) { return i.transcribed; });
    var total = itemsFor(grade).length;

    var card = el("div", "card");
    card.appendChild(el("h2", "", "The questions"));
    if (!all.length) {
      card.appendChild(el("p", "lede",
        "No grade " + grade + " questions are transcribed yet. Every item is still listed " +
        "under Standards, Difficulty and Items, with its statewide P-value and a link to " +
        "the exact page of the official PDF."));
      host.appendChild(card);
      return host;
    }
    card.appendChild(el("p", "lede",
      all.length + " of " + total + " grade " + grade + " items are transcribed so far. " +
      "The wording is NYSED's own, taken from the PDF's text layer character for character; " +
      "only the mathematics is reconstructed, and every item links to the official page so " +
      "you can check it."));
    host.appendChild(card);

    var controls = el("div", "controls");
    var units = unitOptionsFor(grade, all);
    var fYear = picker(controls, "Year",
                       uniq(all.map(function (i) { return i.year; })).sort());
    var fUnit = units.length
      ? picker(controls, "Taught in unit", units, function (u) {
          return unitOptionLabel(grade, u); })
      : null;
    var fStd = picker(controls, "Standard",
                      uniq(all.map(function (i) { return i.standard; })).sort());
    var fType = picker(controls, "Question type",
                       uniq(all.map(function (i) { return i.type; })).sort());
    var fSort = picker(controls, "Sort", ["year", "curriculum", "standard", "hardest"],
                       function (k) {
      return { year: "Year and item", curriculum: "Curriculum sequence",
               standard: "Standard", hardest: "Hardest first" }[k];
    });
    /* Sort is not a filter, so it has no meaningful "All" -- drop the blank
       option the picker adds and default to the natural reading order. */
    fSort.removeChild(fSort.firstChild);
    fSort.value = "year";
    var search = searchBox(controls, "Search the questions");
    var showAns = el("input"); showAns.type = "checkbox"; showAns.checked = true;
    var lAns = el("label");
    lAns.appendChild(showAns); lAns.appendChild(el("span", "", "Show answers"));
    controls.appendChild(lAns);
    host.appendChild(controls);
    if (fUnit) host.appendChild(derivedUnitNote());

    var count = el("p", "lede");
    host.appendChild(count);
    var list = el("div");
    host.appendChild(list);

    /* Searching the unit and lesson titles as well as the question text is what
       makes "circumference" find the items whose standards Measuring Circles
       teaches, not just the ones that happen to print the word. */
    function haystack(i) {
      if (i._hay) return i._hay;
      var spec = curriculumFor(grade);
      var words = [i.stemPlain || "", i.standard, i.domainLabel || "",
                   (i.choiceList || []).map(function (c) { return c.text; }).join(" ")];
      unitsForItem(grade, i).forEach(function (u) {
        var unit = spec && spec.units[u];
        if (unit) words.push("unit " + u + " " + unit.title);
      });
      i._hay = words.join(" ").toLowerCase();
      return i._hay;
    }

    function order(rows) {
      var key = fSort.value;
      return rows.slice().sort(function (a, b) {
        if (key === "hardest" && a.pValue !== b.pValue) return a.pValue - b.pValue;
        if (key === "standard" && a.standard !== b.standard) {
          return a.standard < b.standard ? -1 : 1;
        }
        if (key === "curriculum") {
          /* Lowest unit an item derives to, so an item taught in Units 2 and 5
             sorts with Unit 2. Items with no unit are prior-grade content and
             sort last rather than first. */
          var ua = unitsForItem(grade, a)[0], ub = unitsForItem(grade, b)[0];
          var na = ua === undefined ? 99 : Number(ua);
          var nb = ub === undefined ? 99 : Number(ub);
          if (na !== nb) return na - nb;
        }
        if (a.year !== b.year) return a.year - b.year;
        return a.item - b.item;
      });
    }

    function paint() {
      var q = search.value.trim().toLowerCase();
      var rows = all.filter(function (i) {
        if (fYear.value && String(i.year) !== fYear.value) return false;
        if (fUnit && !matchesUnit(grade, i, fUnit.value)) return false;
        if (fStd.value && i.standard !== fStd.value) return false;
        if (fType.value && i.type !== fType.value) return false;
        return !q || haystack(i).indexOf(q) !== -1;
      });
      rows = order(rows);
      count.textContent = rows.length === all.length
        ? all.length + " question" + (all.length === 1 ? "" : "s")
        : "Showing " + rows.length + " of " + all.length + " questions";
      list.textContent = "";
      if (!rows.length) {
        var none = el("div", "card");
        none.appendChild(el("p", "empty", "No question matches those filters."));
        var clear = el("button", "linkish", "Clear the filters");
        clear.type = "button";
        clear.addEventListener("click", function () {
          [fYear, fUnit, fStd, fType].forEach(function (sel) { if (sel) sel.value = ""; });
          search.value = "";
          paint();
        });
        none.appendChild(clear);
        list.appendChild(none);
        return;
      }
      var f = frag();
      rows.forEach(function (i) { f.appendChild(questionCard(i, showAns.checked)); });
      list.appendChild(f);
    }
    [fYear, fUnit, fStd, fType, fSort].forEach(function (sel) {
      if (sel) sel.addEventListener("change", paint);
    });
    search.addEventListener("input", paint);
    showAns.addEventListener("change", paint);
    paint();
    return host;
  }

  function questionCard(i, answers) {
    var box = el("div", "std");

    var head = el("div", "std-head");
    head.appendChild(el("span", "code", i.year + " \u00b7 item " + i.item));
    head.appendChild(el("span", "dom", i.standard));
    head.appendChild(typeTag(i));
    if (i.postTest) {
      var pt = el("span", "tag post", "grade " + i.postTestFromGrade + " standard");
      pt.title = D.blueprint.postTestLegend;
      head.appendChild(pt);
    }
    var p = el("span", "tag");
    p.appendChild(document.createTextNode("statewide " + i.pValue.toFixed(2)));
    p.className = "tag " + band(i.pValue);
    p.title = "The proportion of students in New York State who earned credit on this item";
    head.appendChild(p);
    box.appendChild(head);

    if (i.creditLine) box.appendChild(el("div", "credit-line", i.creditLine));

    // The stem, the displayed mathematics and the figures carry this project's
    // own markup and are inserted as HTML. Everything that came from a person
    // -- alt text, captions, answers -- is set as text instead.
    var stem = el("div", "stem");
    stem.innerHTML = i.stem || "";
    box.appendChild(stem);

    (i.display || []).forEach(function (html) {
      var d = el("div", "eqblock");
      d.innerHTML = html;
      box.appendChild(d);
    });

    (i.figures || []).forEach(function (fig) {
      var f = el("figure", "qfig");
      var img = el("img");
      img.src = "assets/" + fig.file;
      img.alt = fig.alt || "";
      img.loading = "lazy";
      f.appendChild(img);
      if (fig.longDescription) {
        var cap = el("figcaption", "", fig.longDescription);
        f.appendChild(cap);
      }
      box.appendChild(f);
    });

    if (i.stemAfter) {
      var after = el("div", "stem");
      after.innerHTML = i.stemAfter;
      box.appendChild(after);
    }

    (i.instructions || []).forEach(function (t) {
      box.appendChild(el("div", "instruction", t));
    });

    if ((i.choiceList || []).length && !i.choicesInImage) {
      var wrap = el("div", "choices");
      i.choiceList.forEach(function (c) {
        var row = el("div", "choice" + (answers && c.isCorrect ? " correct" : ""));
        row.appendChild(el("span", "lab", c.label));
        var body = el("span");
        body.innerHTML = c.text || "";
        row.appendChild(body);
        wrap.appendChild(row);
      });
      box.appendChild(wrap);
    } else if (i.choicesInImage) {
      box.appendChild(el("p", "lede",
        "The answer choices for this item are pictures, shown above."));
    }

    if (answers && i.cr) {
      var ans = el("div", "answer");
      ans.appendChild(el("h4", "", "Answer"));
      var val = el("div", "val");
      val.innerHTML = i.cr.answer;
      ans.appendChild(val);
      if (i.cr.note) ans.appendChild(el("div", "src", i.cr.note));
      ans.appendChild(el("div", "src", i.cr.source));
      box.appendChild(ans);
    }

    var placement = alignmentBlock(i);
    if (placement) box.appendChild(placement);

    var foot = el("div", "row");
    foot.style.marginTop = "12px";
    var link = pdfLink(i, "Check this item in the official PDF"
                          + (i.pdfPage ? " (page " + i.pdfPage + ")" : ""));
    foot.appendChild(link);
    box.appendChild(foot);
    return box;
  }

  /* ---------------------------------------------- the per-item alignment

     This shows the JUDGED placement, which is a different thing from the
     "Taught in" column elsewhere on the site. That column is DERIVED -- it
     lists every unit whose lessons teach the item's standard. This is one
     teacher's reading of what the item actually asks, and it names the
     activity and page so a reader can check it rather than take it on trust.

     Drafted entries never arrive here: build/payload.py drops them, so an
     item with no reviewed placement simply has no block. */

  var ROLE_NOTE = {
    introduces: "where the idea or method first appears",
    practises: "an activity or practice problem applying it",
    assessed: "where the curriculum itself tests the skill"
  };

  function alignmentBlock(i) {
    if (!i.unit && !i.lesson) return null;
    var box = el("div", "align");

    var head = el("div", "align-head");
    var where = i.course + " \u00b7 Unit " + i.unit +
                (i.unitTitle ? " " + i.unitTitle : "");
    head.appendChild(el("span", "align-where", where));
    if (i.lesson) {
      head.appendChild(el("span", "align-lesson",
        "Lesson " + i.lesson + (i.lessonTitle ? " \u00b7 " + i.lessonTitle : "")));
    } else {
      /* A unit-only entry is a deliberate refusal to guess, not a gap. */
      head.appendChild(el("span", "align-lesson note", "no lesson named"));
    }
    box.appendChild(head);

    var ev = i.lessons || [];
    if (ev.length) {
      var list = el("ul", "align-ev");
      ev.forEach(function (e) {
        var li = el("li");
        var role = el("span", "align-role", e.role);
        if (ROLE_NOTE[e.role]) role.title = ROLE_NOTE[e.role];
        li.appendChild(role);
        li.appendChild(el("span", "align-cite",
          "Lesson " + e.lesson + (e.lessonTitle ? " " + e.lessonTitle : "") +
          " \u00b7 " + e.activity + " \u00b7 p" + e.page));
        if (e.quote) li.appendChild(el("div", "align-quote", "\u201c" + e.quote + "\u201d"));
        list.appendChild(li);
      });
      box.appendChild(list);
    }

    box.appendChild(el("div", "src",
      "One teacher's judgement, not official guidance. The activity and page are "
      + "named so you can check the placement against the guide itself."));
    return box;
  }

  /* ------------------------------------------------------------ difficulty */

  function viewDifficulty(grade) {
    var host = frag();
    var items = itemsFor(grade).slice();
    var roll = standardRollup(grade).filter(function (s) { return s.n > 0; });

    var card = el("div", "card");
    card.appendChild(el("h2", "", "What New York State found hard"));
    card.appendChild(el("p", "lede",
      "NYSED publishes a P-value for every released item — the proportion of students " +
      "statewide who earned credit on it. It is the one figure here that tells you whether a " +
      "question was hard for your class or hard for everybody."));
    var n = el("p", "note");
    n.innerHTML = "<b>Two different quantities share this column.</b> For a multiple-choice item " +
      "the P-value is the percentage answering correctly. For a constructed-response item it is " +
      "average points earned divided by total possible points. They are comparable as difficulty " +
      "but they are not the same measurement, and NYSED does not publish the population either " +
      "is computed over.";
    card.appendChild(n);
    host.appendChild(card);

    var persistent = roll.filter(function (s) { return s.years.length >= 3 && s.meanP < 0.5; })
                         .sort(function (a, b) { return a.meanP - b.meanP; });
    var c1 = el("div", "card");
    c1.appendChild(el("h3", "", "Hard every time it is asked"));
    c1.appendChild(el("p", "lede",
      "Standards tested in at least three of the four years with a mean P-value below 0.50. " +
      "These are different from a standard that happened to draw one hard item."));
    if (!persistent.length) c1.appendChild(el("p", "empty", "None for grade " + grade + "."));
    else c1.appendChild(table([
      { key: "code", label: "Standard", render: function (s) { return el("span", "mono", s.code); } },
      { key: "domainName", label: "Domain", wrap: true, value: function (s) { return s.reg.domainName; },
        render: function (s) { return s.reg.domainName; } },
      { key: "n", label: "Items", num: true },
      { key: "years", label: "Years", num: true, value: function (s) { return s.years.length; },
        render: function (s) { return s.years.length + " of 4"; } },
      { key: "meanP", label: "Mean statewide", render: function (s) { return pCell(s.meanP); } },
      { key: "spread", label: "Range", sort: false,
        render: function (s) { return s.minP.toFixed(2) + "–" + s.maxP.toFixed(2); } },
      { key: "cluster", label: "Cluster", wrap: true, sort: false,
        render: function (s) { return s.reg.clusterText || "—"; } }
    ], persistent, { sortKey: "meanP" }));
    host.appendChild(c1);

    var c2 = el("div", "card");
    c2.appendChild(el("h3", "", "Every released item, hardest first"));
    c2.appendChild(el("p", "lede",
      "All " + items.length + " released grade " + grade + " items ordered by how New York State did."));
    c2.appendChild(table([
      { key: "year", label: "Year", num: true },
      { key: "item", label: "Item", num: true },
      { key: "session", label: "Sess", num: true },
      { key: "type", label: "Type", render: typeTag },
      { key: "credits", label: "Cr", num: true },
      { key: "standard", label: "Standard", render: function (i) {
          var s = el("span", "mono", i.standard);
          if (i.postTest) s.title = "A grade " + i.postTestFromGrade + " standard, assessed here";
          return s; } },
      { key: "domainLabel", label: "Domain", wrap: true },
      { key: "pValue", label: "Statewide", render: function (i) { return pCell(i.pValue); } },
      { key: "pdfPage", label: "Official PDF", sort: false, render: function (i) { return pdfLink(i); } }
    ], items, { sortKey: "pValue" }));
    host.appendChild(c2);
    return host;
  }

  /* ------------------------------------------------------------- blueprint */

  function viewBlueprint(grade) {
    var host = frag();
    var bp = D.blueprint.grades[String(grade)];
    var tests = testsFor(grade);

    var card = el("div", "card");
    card.appendChild(el("h2", "", "Tested weight against NYSED's own target"));
    card.appendChild(el("p", "lede",
      "NYSED publishes a percent range per domain for each grade. The marker shows the share of " +
      "released credits that actually fell in each domain; the band shows the published range."));
    var n = el("p", "note");
    n.innerHTML = "<b>Released items are a sample, so a marker outside the band is not " +
      "necessarily a discrepancy.</b> Around a quarter of each test is withheld, and the " +
      "released proportion is not even constant — 2026 released noticeably more than " +
      "2023–2025. Read the per-year rows rather than only the pooled one.";
    card.appendChild(n);
    if (bp.domainBlueprintNote) {
      var dn = el("p", "note", bp.domainBlueprintNote);
      card.appendChild(dn);
    }
    host.appendChild(card);

    // No domain range reaches half the test -- the widest is 28-41% -- so a
    // 0-100% axis would squeeze every band into the left third of the track.
    var AXIS_MAX = 50;

    function shareCard(title, subtitle, itemSet) {
      var c = el("div", "card");
      c.appendChild(el("h3", "", title));
      if (subtitle) c.appendChild(el("p", "lede", subtitle));
      var total = itemSet.reduce(function (s, i) { return s + i.credits; }, 0);
      Object.keys(bp.domainBlueprint).forEach(function (dom) {
        var range = bp.domainBlueprint[dom];
        var got = itemSet.filter(function (i) { return i.domain === dom; })
                         .reduce(function (s, i) { return s + i.credits; }, 0);
        var share = total ? (got / total) * 100 : 0;
        var row = el("div", "bp-row");
        var name = el("div", "name", D.blueprint.domains[dom] || dom);
        row.appendChild(name);

        var track = el("div", "bp-track");
        if (range) {
          var b = el("div", "bp-band");
          b.style.left = (range[0] / AXIS_MAX * 100) + "%";
          b.style.width = Math.max(1, (range[1] - range[0]) / AXIS_MAX * 100) + "%";
          b.title = "NYSED published range: " + range[0] + "–" + range[1] + "%";
          track.appendChild(b);
        }
        var m = el("div", "bp-actual");
        m.style.left = Math.min(99, share / AXIS_MAX * 100) + "%";
        m.title = "Released credits in this domain: " + share.toFixed(1) + "%";
        track.appendChild(m);
        row.appendChild(track);

        var val = el("div", "val");
        if (range) {
          val.textContent = share.toFixed(0) + "% vs " + range[0] + "–" + range[1] + "%";
          if (share < range[0] || share > range[1]) row.className = "bp-row out";
        } else {
          val.textContent = share.toFixed(0) + "% · post-test only";
          val.title = "Every standard in this domain is a post-test standard for grade " +
                      grade + ", so NYSED publishes no range.";
        }
        row.appendChild(val);
        c.appendChild(row);
      });
      var axis = el("p", "lede");
      axis.style.marginTop = "10px";
      axis.textContent = "Track runs 0 to " + AXIS_MAX + "% of released credits. " +
        "Band = NYSED's published range, marker = what the released items actually carry.";
      c.appendChild(axis);
      return c;
    }

    host.appendChild(shareCard(
      "All four years pooled",
      itemsFor(grade).length + " released items, " +
        itemsFor(grade).reduce(function (s, i) { return s + i.credits; }, 0) + " credits.",
      itemsFor(grade)));

    tests.forEach(function (t) {
      host.appendChild(shareCard(
        String(t.year),
        t.releasedItems + " of " + t.designedItems + " items released (" +
          t.releasedMultipleChoice + " multiple choice, " +
          t.releasedConstructedResponse + " constructed response), " +
          t.releasedCredits + " credits.",
        itemsFor(grade).filter(function (i) { return i.year === t.year; })));
    });

    var design = el("div", "card");
    design.appendChild(el("h3", "", "How the test is built"));
    design.appendChild(table([
      { key: "session", label: "Session", sort: false },
      { key: "items", label: "Items", sort: false },
      { key: "mc", label: "Multiple choice", num: true, sort: false },
      { key: "cr", label: "Constructed response", sort: false },
      { key: "calc", label: "Calculator", wrap: true, sort: false }
    ], Object.keys(bp.sessions).map(function (k) {
      var s = bp.sessions[k];
      var cr = [1, 2, 3].map(function (n) {
        return s["constructedResponse" + n + "Credit"] ? s["constructedResponse" + n + "Credit"] + "×" + n + "-credit" : null;
      }).filter(Boolean).join(", ") || "none";
      return { session: k, items: s.items[0] + "–" + s.items[1],
               mc: s.multipleChoice, cr: cr, calc: s.calculator };
    })));
    design.appendChild(el("p", "lede",
      bp.designedItems + " items and " + bp.totalCredits + " credits in total, including " +
      "embedded field-test questions that do not count toward a student's score. " +
      bp.itemNumbering.note));
    host.appendChild(design);
    return host;
  }

  /* --------------------------------------------------------- post-test tab */

  function viewPostTest(grade) {
    var host = frag();
    var items = itemsFor(grade).filter(function (i) { return i.postTest; });
    var tables = D.blueprint.postTestTables;

    var card = el("div", "card");
    card.appendChild(el("h2", "", "Standards from the grade below"));
    card.appendChild(el("p", "lede",
      "Some of what the grade " + grade + " test assesses is not grade " + grade + " content. " +
      "NYSED designates certain standards for May-to-June instruction, which is after their own " +
      "grade's test is given, so they are assessed the following year instead."));
    var n = el("p", "note");
    n.innerHTML = "<b>NYSED's own key for this: </b>“" + D.blueprint.postTestLegend
      .replace(/^[^"“]*[“"]/, "").replace(/[”"].*$/, "") + "”";
    card.appendChild(n);
    host.appendChild(card);

    var c1 = el("div", "card");
    c1.appendChild(el("h3", "", items.length + " released grade " + grade + " item" +
      (items.length === 1 ? "" : "s") + " assess a prior-grade standard"));
    if (!items.length) {
      c1.appendChild(el("p", "empty",
        "None among the released grade " + grade + " items — which does not mean none on the " +
        "test, since about a quarter of each test is withheld."));
    } else {
      c1.appendChild(table([
        { key: "year", label: "Year", num: true },
        { key: "item", label: "Item", num: true },
        { key: "type", label: "Type", render: typeTag },
        { key: "credits", label: "Cr", num: true },
        { key: "standard", label: "Standard", render: function (i) { return el("span", "mono", i.standard); } },
        { key: "postTestFromGrade", label: "From grade", num: true },
        { key: "cluster", label: "Cluster", wrap: true, sort: false,
          render: function (i) {
            var r = D.standards[i.standard];
            return r && r.clusterText ? r.clusterText : "—"; } },
        { key: "pValue", label: "Statewide", render: function (i) { return pCell(i.pValue); } },
        { key: "pdfPage", label: "Official PDF", sort: false, render: function (i) { return pdfLink(i); } }
      ], items, { sortKey: "year" }));
    }
    host.appendChild(c1);

    var prior = String(grade - 1);
    if (tables[prior]) {
      var c2 = el("div", "card");
      c2.appendChild(el("h3", "", "Every grade " + prior + " standard the grade " + grade + " test can assess"));
      c2.appendChild(el("p", "lede",
        "NYSED's published list — " + tables[prior].codes.length + " standards. A grade " +
        prior + " teacher teaches these; a grade " + grade + " teacher is tested on them."));
      c2.appendChild(table([
        { key: "code", label: "Standard", render: function (r) { return el("span", "mono", r.code); } },
        { key: "domain", label: "Domain", wrap: true },
        { key: "cluster", label: "Cluster", wrap: true },
        { key: "n", label: "Released items here", num: true }
      ], tables[prior].codes.map(function (code) {
        var reg = D.standards[code] || {};
        return { code: code, domain: reg.domainName || "—",
                 cluster: reg.clusterText || "—",
                 n: items.filter(function (i) { return i.standard === code; }).length };
      }), { sortKey: "code" }));
      host.appendChild(c2);
    }

    var mine = tables[String(grade)];
    if (mine) {
      var c3 = el("div", "card");
      c3.appendChild(el("h3", "", "And what grade " + grade + " teaches but does not get tested on"));
      c3.appendChild(el("p", "lede",
        mine.codes.length + " grade " + grade + " standards are designated for May-to-June " +
        "instruction" + (mine.testedInGrade
          ? " and are assessed on the grade " + mine.testedInGrade + " test instead."
          : ". There is no grade " + (grade + 1) + " State mathematics test, so these are not " +
            "assessed anywhere in this programme.")));
      c3.appendChild(table([
        { key: "code", label: "Standard", render: function (r) { return el("span", "mono", r.code); } },
        { key: "domain", label: "Domain", wrap: true },
        { key: "cluster", label: "Cluster", wrap: true }
      ], mine.codes.map(function (code) {
        var reg = D.standards[code] || {};
        return { code: code, domain: reg.domainName || "—", cluster: reg.clusterText || "—" };
      }), { sortKey: "code" }));
      host.appendChild(c3);
    }
    return host;
  }

  /* ------------------------------------------------------------ items tab */

  function viewItems(grade) {
    var host = frag();
    var all = itemsFor(grade);

    var card = el("div", "card");
    card.appendChild(el("h2", "", "Every released item"));
    card.appendChild(el("p", "lede",
      "Filter to what you want, then print the page for a review set. Each row links to the " +
      "exact page of NYSED's official released-items PDF."));
    var n = el("p", "note");
    n.innerHTML = "<b>This site does not reproduce item text or figures.</b> Every numeral and " +
      "figure in the NYSED PDFs is vector artwork with no text layer, so any transcription here " +
      "would be hand-typed or quietly wrong — and a subtly wrong question is worse than a " +
      "link to the real one. The <em>Official PDF</em> column opens the genuine question.";
    card.appendChild(n);
    host.appendChild(card);

    var controls = el("div", "controls");
    var units = unitOptionsFor(grade, all);
    var fYear = picker(controls, "Year", uniq(all.map(function (i) { return i.year; })).sort());
    var fUnit = units.length
      ? picker(controls, "Taught in unit", units, function (u) {
          return unitOptionLabel(grade, u); })
      : null;
    var fDomain = picker(controls, "Domain", uniq(all.map(function (i) { return i.domain; })).sort(),
                         function (d) { return D.blueprint.domains[d] || d; });
    var fType = picker(controls, "Type", ["Multiple Choice", "Constructed Response"]);
    var fHard = picker(controls, "Difficulty", ["hard", "mid", "easy"], function (b) {
      return { hard: "Hard (under 0.50)", mid: "Middling (0.50–0.74)",
               easy: "Easier (0.75 and up)" }[b];
    });
    var fPost = picker(controls, "Prior grade", ["yes", "no"], function (v) {
      return v === "yes" ? "Prior-grade standards only" : "This grade only"; });
    var search = searchBox(controls, "Standard code, domain or unit");
    host.appendChild(controls);
    if (fUnit) host.appendChild(derivedUnitNote());

    var count = el("p", "lede");
    host.appendChild(count);
    var slot = el("div");
    host.appendChild(slot);

    function paint() {
      var q = search.value.trim().toLowerCase();
      var rows = all.filter(function (i) {
        if (fYear.value && String(i.year) !== fYear.value) return false;
        if (fUnit && !matchesUnit(grade, i, fUnit.value)) return false;
        if (fDomain.value && i.domain !== fDomain.value) return false;
        if (fType.value && i.type !== fType.value) return false;
        if (fHard.value && band(i.pValue) !== fHard.value) return false;
        if (fPost.value === "yes" && !i.postTest) return false;
        if (fPost.value === "no" && i.postTest) return false;
        if (q && (i.standard + " " + (i.domainLabel || "") + " " +
                  unitText(grade, i)).toLowerCase().indexOf(q) === -1) return false;
        return true;
      });
      count.textContent = rows.length + " of " + all.length + " items · " +
        rows.reduce(function (s, i) { return s + i.credits; }, 0) + " credits";
      slot.textContent = "";
      if (!rows.length) { slot.appendChild(el("p", "empty", "Nothing matches those filters.")); return; }
      slot.appendChild(table([
        { key: "year", label: "Year", num: true },
        { key: "item", label: "Item", num: true },
        { key: "session", label: "Sess", num: true },
        { key: "type", label: "Type", render: typeTag },
        { key: "credits", label: "Cr", num: true },
        { key: "key", label: "Key", render: function (i) { return i.key || "—"; } },
        { key: "standard", label: "Standard", render: function (i) {
            var s = el("span", "mono", i.standard);
            if (i.postTest) { s.title = "grade " + i.postTestFromGrade + " standard"; }
            return s; } },
        { key: "domainLabel", label: "Domain", wrap: true },
        { key: "units", label: "Taught in", wrap: true, sort: false,
          title: "Units whose lessons teach this item's standard. Derived from the "
               + "standard, not an alignment of the item itself \u2014 where a judged "
               + "placement exists it is shown on the question and may differ.",
          render: function (i) {
            var us = unitsForItem(grade, i);
            if (!us.length) return el("span", "muted", "—");
            var box = el("span", "lesson-codes");
            us.forEach(function (u) {
              var spec = curriculumFor(grade);
              var unit = spec && spec.units[u];
              var chip = el("span", "chip", "U" + u);
              chip.title = unit ? "Unit " + u + " \u00b7 " + unit.title : "Unit " + u;
              box.appendChild(chip);
            });
            return box; } },
        { key: "secondary", label: "Also", sort: false, render: function (i) {
            return i.secondary && i.secondary.length ? i.secondary.join(", ") : "—"; } },
        { key: "pValue", label: "Statewide", render: function (i) { return pCell(i.pValue); } },
        { key: "avgPointsEarned", label: "Avg pts", num: true, render: function (i) {
            return i.avgPointsEarned === null ? "—" : i.avgPointsEarned.toFixed(2); } },
        { key: "pdfPage", label: "Official PDF", sort: false, render: function (i) { return pdfLink(i); } }
      ], rows, { sortKey: "year" }));
    }
    [fYear, fUnit, fDomain, fType, fHard, fPost].forEach(function (s) {
      if (s) s.addEventListener("change", paint);
    });
    search.addEventListener("input", paint);
    paint();
    return host;
  }


  /* ----------------------------------------------------------------- about */

  /* What this data is, how much of it there is, and what is already known to
     be wrong with it -- then the form.

     The known-issues list is the reason this view is worth building. A
     colleague who notices item 40's stray dollar sign should be able to see
     that it is already recorded, rather than spending their time writing it up.
     Everything here is read from the payload, so none of it can go stale as
     coverage grows. */

  function viewAbout(grade) {
    var host = frag();
    var tc = D.meta.transcriptionCoverage || {};

    var what = el("div", "card");
    what.appendChild(el("h2", "", "About this data"));
    what.appendChild(el("p", "lede",
      "Two different things are on this site, and they are worth telling apart."));
    var dl = el("div");
    [["NYSED's own published data",
      "Every item's type, answer key, credits, standard, cluster and statewide P-value comes " +
      "from the Map to the Standards table that NYSED publishes with each year's released " +
      "questions. So does the test design and the domain blueprint, from the Educator Guide. " +
      "None of that is my judgement and none of it is retyped."],
     ["One teacher's judgement",
      "The curriculum alignment — which unit and lesson an item belongs to — is a judgement " +
      "call, not official guidance from NYSED or Imagine Learning. Where a placement is " +
      "uncertain the site says so."]
    ].forEach(function (pair) {
      var h = el("h3", "", pair[0]);
      h.style.marginTop = "14px";
      dl.appendChild(h);
      dl.appendChild(el("p", "", pair[1]));
    });
    what.appendChild(dl);
    host.appendChild(what);

    var how = el("div", "card");
    how.appendChild(el("h3", "", "How a question gets onto this site"));
    how.appendChild(el("p", "",
      "The questions in these PDFs cannot simply be copied: every numeral, variable and figure " +
      "is drawn as vector artwork with no text behind it. The words, though, are real text. So " +
      "a stem arrives as a sentence with holes exactly where its mathematics should be, and " +
      "only the holes are reconstructed — each one decoded from the shapes of the drawn " +
      "characters against a table built by hand."));
    var n = el("p", "note");
    n.innerHTML = "<b>What that buys you.</b> Because the wording is never retyped, it can be " +
      "checked mechanically: before anything is published, the site strips the markup and the " +
      "reconstructed mathematics out of every stem and requires what remains to match the " +
      "PDF's own text character for character. A stem cannot drift from the original without " +
      "the build failing.";
    how.appendChild(n);
    how.appendChild(el("p", "",
      "Reconstructed mathematics can still be wrong, and a wrong number can look perfectly " +
      "reasonable. So every item links to the exact page of the official PDF, and that page — " +
      "not this site — is the authority. Answer keys are NYSED's own, and every " +
      "constructed-response answer comes from NYSED's published exemplary response."));
    host.appendChild(how);

    var cov = el("div", "card");
    cov.appendChild(el("h3", "", "How much is here"));
    cov.appendChild(table([
      { key: "grade", label: "Grade", num: true },
      { key: "items", label: "Released items", num: true },
      { key: "questions", label: "Questions shown", num: true,
        render: function (r) { return r.questions || "none yet"; } },
      { key: "note", label: "", wrap: true, sort: false }
    ], D.meta.grades.map(function (g) {
      var mine = D.items.filter(function (i) { return i.grade === g; });
      var t = mine.filter(function (i) { return i.transcribed; }).length;
      return {
        grade: g, items: mine.length, questions: t,
        note: t ? (t + " of " + mine.length + " transcribed so far")
                : "every item still carries its standard, its statewide P-value and a link " +
                  "to the official PDF"
      };
    }), { sortKey: "grade" }));
    host.appendChild(cov);

    var notes = tc.reviewNotes || {};
    var keys = Object.keys(notes);
    if (keys.length) {
      var known = el("div", "card");
      known.appendChild(el("h3", "", "Known problems — please don't spend time on these"));
      known.appendChild(el("p", "lede",
        "Found while checking the transcription, and left visible on purpose. Several could be " +
        "tidied by hand, but editing a stem would break the check that keeps the wording honest, " +
        "so they wait for a fix in the extraction instead."));
      keys.forEach(function (testId) {
        var list = el("ul");
        list.style.margin = "0";
        list.style.paddingLeft = "20px";
        (notes[testId] || []).forEach(function (text) {
          var li = el("li", "", text);
          li.style.marginBottom = "7px";
          li.style.fontSize = "13.5px";
          list.appendChild(li);
        });
        known.appendChild(el("h3", "", testId.replace("g", "Grade ").replace("-", ", ")));
        known.appendChild(list);
      });
      host.appendChild(known);
    }

    var sources = tc.keySources || {};
    if (Object.keys(sources).length) {
      var ks = el("div", "card");
      ks.appendChild(el("h3", "", "How the answer keys were verified"));
      Object.keys(sources).forEach(function (testId) {
        ks.appendChild(el("h3", "", testId.replace("g", "Grade ").replace("-", ", ")));
        var pr = el("p", "", sources[testId]);
        pr.style.fontSize = "13px";
        ks.appendChild(pr);
      });
      host.appendChild(ks);
    }

    var fbCard = el("div", "card");
    fbCard.appendChild(el("h3", "", "Found something wrong?"));
    fbCard.appendChild(el("p", "lede",
      "Corrections and disagreement are both welcome — including about a curriculum placement " +
      "you would have made differently. If you can, say which grade, year and item."));
    if (FORM_HTML) {
      var holder = el("div");
      holder.innerHTML = FORM_HTML;
      var form = holder.querySelector("form");
      form.hidden = false;
      fbCard.appendChild(form);
      wireForm(form);
    } else {
      fbCard.appendChild(el("p", "empty", "The correction form is unavailable on this page."));
    }
    host.appendChild(fbCard);
    return host;
  }

  /* Submit over fetch so the reader stays on the page. Netlify accepts a
     urlencoded POST to the page path as long as form-name is included. On a
     local preview there is no Netlify to answer, so the failure path has to say
     something useful rather than look broken. */
  function wireForm(form) {
    if (form.dataset.wired) return;
    form.dataset.wired = "1";
    var status = form.querySelector(".fb-status");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var body = new URLSearchParams(new FormData(form)).toString();
      status.textContent = "Sending…";
      status.className = "fb-status";
      fetch(form.getAttribute("action") || window.location.pathname, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body
      }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        form.reset();
        status.textContent = "Thank you — that has been sent.";
        status.className = "fb-status ok";
      }).catch(function () {
        status.className = "fb-status err";
        status.textContent = "That could not be sent from here. The form only works on the " +
          "published site, so if you are looking at a local preview this is expected.";
      });
    });
  }

  /* ------------------------------------------------------------------ shell */

  /* ------------------------------------------------------- curriculum tab */

  /* The Imagine IM New York index: what each unit teaches, when the guide
     paces it, and what the released tests have asked about the standards it
     covers.

     THE JOIN HERE IS BY STANDARD, NOT BY ITEM, and the view says so. A
     per-item curriculum alignment is hand-owned judgement that lives in
     data/alignment.json and is not written yet; what this can say without
     inventing anything is "the standards this unit teaches have been assessed
     by these released items", which is a weaker claim and a different one. Read
     as a per-item alignment it would overcount, because one item's standard can
     be taught in more than one unit. */

  function curriculumFor(grade) {
    return (D.curriculum && D.curriculum.grades) ? D.curriculum.grades[String(grade)] : null;
  }

  /* The course guides cite PARENT codes where NYSED's item maps cite the
     sub-standards: a lesson says NY-7.EE.4 and every released item says
     NY-7.EE.4a or NY-7.EE.4b. Matching the literal string finds nothing, and
     "nothing" is indistinguishable from "never tested" on the page. Grade 7
     Unit 8 went from 0 released items to 29 once the parents were expanded. */
  var EXPANDED = {};
  function expandCode(code) {
    if (EXPANDED[code]) return EXPANDED[code];
    var out = D.standards[code] ? [code] : [];
    Object.keys(D.standards).forEach(function (c) {
      if (c.length === code.length + 1 && c.indexOf(code) === 0 && /[a-z]$/.test(c)) out.push(c);
    });
    EXPANDED[code] = out.length ? out : [code];
    return EXPANDED[code];
  }

  function unitStandards(unit) {
    var codes = {};
    Object.keys(unit.lessons).forEach(function (n) {
      unit.lessons[n].standards.forEach(function (c) {
        expandCode(c).forEach(function (x) { codes[x] = true; });
      });
    });
    return Object.keys(codes);
  }

  function itemsForCodes(grade, codes) {
    var want = {};
    codes.forEach(function (c) { want[c] = true; });
    return itemsFor(grade).filter(function (i) {
      if (want[i.standard]) return true;
      return (i.secondary || []).some(function (c) { return want[c]; });
    });
  }

  function unitItems(grade, unit) {
    return itemsForCodes(grade, unitStandards(unit));
  }

  /* ---- deriving a unit for an ITEM, which is the reverse of the above ----

     This derivation predates the per-item alignment and still runs alongside it.
     data/alignment.json now carries judged placements -- all of grade 7 as of the
     second-pass review -- but the FILTER stays derived, because a filter has to
     answer for every item including the ones nobody has judged yet. What the
     derivation uses is the guide's standard-to-lesson index, so an item's unit is
     DERIVED from the standard it assesses -- the units whose lessons teach that
     standard. A judged placement can name a different unit, and the question card
     shows it; these two must not be conflated.

     That is weaker than an alignment and the page says so. "Unit 3" here means
     "Unit 3 teaches the standard this item assesses", not "this item belongs to
     Unit 3". It is over-inclusive, never wrong, and it is the same join the
     Curriculum tab already publishes, so the two tabs cannot disagree.

     PARENT CODES ARE THE HAZARD, in the opposite direction from expandCode's
     usual use. standardToLessons can be keyed on NY-7.EE.4 while every item
     cites NY-7.EE.4a, so the index is built by expanding each key and filing the
     lessons under every sub-standard as well. Without that, grade 7 Unit 8 finds
     none of its 29 items. */
  var UNIT_INDEX = {};
  function unitIndexFor(grade) {
    if (UNIT_INDEX[grade]) return UNIT_INDEX[grade];
    var index = {};
    var spec = curriculumFor(grade);
    if (spec) {
      Object.keys(spec.standardToLessons).forEach(function (code) {
        var units = {};
        spec.standardToLessons[code].forEach(function (lessonCode) {
          units[lessonCode.split(".")[1]] = true;
        });
        expandCode(code).forEach(function (c) {
          index[c] = index[c] || {};
          Object.keys(units).forEach(function (u) { index[c][u] = true; });
        });
      });
    }
    UNIT_INDEX[grade] = index;
    return index;
  }

  /* The units that teach this item's standards, as sorted number-strings.
     Empty means the item assesses a standard this grade's curriculum does not
     teach -- prior-grade content, which is exactly the post-test set. */
  function unitsForItem(grade, item) {
    var index = unitIndexFor(grade), found = {};
    var codes = [item.standard].concat(item.secondary || []);
    codes.forEach(function (c) {
      var hit = index[c];
      if (hit) Object.keys(hit).forEach(function (u) { found[u] = true; });
    });
    return Object.keys(found).sort(function (a, b) { return a - b; });
  }

  var NO_UNIT = "none";

  /* Every unit that at least one of this grade's items derives to, plus the
     sentinel when some item derives to nothing. Built from the items rather
     than from the curriculum so the dropdown never offers an empty result:
     grade 6 has no released item on Units 5 or 8, and those units are absent. */
  function unitOptionsFor(grade, items) {
    var seen = {}, bare = false;
    items.forEach(function (i) {
      var units = unitsForItem(grade, i);
      if (!units.length) { bare = true; return; }
      units.forEach(function (u) { seen[u] = true; });
    });
    var out = Object.keys(seen).sort(function (a, b) { return a - b; });
    if (bare) out.push(NO_UNIT);
    return out;
  }

  function unitOptionLabel(grade, value) {
    if (value === NO_UNIT) return "Not in this grade's units";
    var spec = curriculumFor(grade);
    var unit = spec && spec.units[value];
    if (!unit) return "Unit " + value;
    /* Unit 9 is "Putting It All Together" -- a wholly optional review unit that
       cites standards from the whole year, so it matches 88 of grade 7's 135
       items. Saying so stops that number reading as a finding. */
    return "Unit " + value + " \u00b7 " + unit.title +
           (unit.whollyOptional ? " (review unit \u2014 matches broadly)" : "");
  }

  /* "unit 3 measuring circles unit 5 rational number arithmetic" -- the searchable
     form of an item's derived units. */
  function unitText(grade, item) {
    var spec = curriculumFor(grade), out = [];
    unitsForItem(grade, item).forEach(function (u) {
      var unit = spec && spec.units[u];
      out.push("unit " + u + (unit ? " " + unit.title : ""));
    });
    return out.join(" ");
  }

  function matchesUnit(grade, item, value) {
    if (!value) return true;
    var units = unitsForItem(grade, item);
    if (value === NO_UNIT) return !units.length;
    return units.indexOf(value) !== -1;
  }

  /* The caveat, in one place, so the Questions and Items tabs cannot drift
     apart on how they describe it. */
  function derivedUnitNote() {
    var n = el("p", "note");
    /* Keep this phrase inside ONE string literal: preflight greps the BUILT page,
       which embeds this source, so a phrase split across a "+" concatenation is
       not contiguous there and the check cannot see it. */
    n.innerHTML = "<b>This filter's unit is derived from the standard, not judged per item.</b> " +
      "An item is counted against a unit when that unit teaches the standard the item " +
      "assesses \u2014 which is not the same as saying the item belongs to the unit. One " +
      "standard is often taught in several units, so an item can appear under more than " +
      "one, and the filtered counts overlap. Where an item carries a judged placement it " +
      "is shown on the question itself, and it can name a different unit from this one.";
    return n;
  }

  /* How much of a unit is taught AFTER its own grade's test. NYSED designates
     some standards for May-to-June instruction and assesses them the following
     year, and whole units can consist of them -- grade 7's Unit 8 (angles,
     triangles and prisms) is entirely post-test, which is why no released grade
     7 item touches it. A bare zero in the table reads as an error; this is the
     explanation. */
  function postTestShare(grade, unit) {
    var codes = unitStandards(unit).filter(function (c) { return D.standards[c]; });
    if (!codes.length) return null;
    /* postTest alone is not the question. It means "designated for May-to-June
       instruction in the standard's OWN grade", and a unit can teach a
       prior-grade standard that carries the flag yet is assessed on the very
       test this reader is preparing for -- grade 7 Unit 7 teaches six grade 6
       statistics standards, all flagged, all assessed on the grade 7 test,
       because New York moved probability down a grade. Reporting those as
       "taught after the test" said the opposite of the truth. What matters here
       is whether the standard is assessed somewhere OTHER than this grade. */
    var post = codes.filter(function (c) {
      var reg = D.standards[c];
      return reg.postTest && (reg.assessedOnGrades || []).indexOf(grade) < 0;
    });
    return { total: codes.length, post: post.length,
             to: uniq(post.reduce(function (a, c) {
               return a.concat(D.standards[c].assessedOnGrades || []); }, [])).sort() };
  }

  function standardChip(code, grade) {
    var reg = D.standards[code];
    var family = expandCode(code).filter(function (c) { return D.standards[c]; });
    /* A PARENT CODE IS STILL A STANDARD. The guides cite NY-7.RP.2; NYSED's
       standards list holds only NY-7.RP.2a through 2d, so a lookup on the
       parent misses and the chip was struck through as "not a standard" --
       which is plainly wrong about a standard every teacher knows. Treat a
       parent whose sub-standards exist as known, and count its whole family. */
    var known = !!reg || family.length > 0;
    var n = el("span", "mono chip" + (known ? "" : " chip-unknown"), code);
    if (known) {
      var hits = itemsForCodes(grade, family.length ? family : [code]).length;
      var post = family.filter(function (c) { return D.standards[c].postTest; });
      n.title = ((reg && (reg.clusterText || reg.domainName)) ||
                 (family[0] && D.standards[family[0]].clusterText) || code) +
        " \u2014 " + hits + " released grade " + grade + " item" + (hits === 1 ? "" : "s") +
        (!reg && family.length
          ? ". The course guide cites this parent code; NYSED's standards list and item "
            + "maps use " + family.join(", ") + ", which is what the count covers."
          : (family.length > 1 ? " across " + family.join(", ") : "")) +
        (post.length
          ? ". Designated for May-to-June instruction, so assessed on the grade "
            + (uniq(post.reduce(function (a, c) {
                return a.concat(D.standards[c].assessedOnGrades || []); }, [])).join(" and ")
               || (grade + 1) + " test \u2014 except there is none")
            + " test rather than grade " + grade + "."
          : "");
      if (hits) n.setAttribute("data-tested", "1");
      if (post.length === family.length && post.length) n.setAttribute("data-post", "1");
    } else {
      /* NY-8.SP.4 is the clearest case: removed from the standards under
         NGMLS but still named by the guide's alignment table. */
      n.title = code + " is cited by the course guide but is not in NYSED's " +
        "own standards list for the grades 3-8 tests, in any form.";
    }
    return n;
  }

  function viewCurriculum(grade) {
    var host = frag();
    var cur = curriculumFor(grade);
    if (!cur) {
      var none = el("div", "card");
      none.appendChild(el("h2", "", "Curriculum index"));
      none.appendChild(el("p", "empty", "Not built for this deploy."));
      host.appendChild(none);
      return host;
    }
    var meta = D.curriculum.meta;
    var units = cur.units;
    var order = Object.keys(units).sort(function (a, b) { return a - b; });

    var intro = el("div", "card");
    intro.appendChild(el("h2", "", meta.edition + " — grade " + grade));
    intro.appendChild(el("p", "lede",
      cur.counts.units + " units, " + cur.counts.sections + " sections and " +
      cur.counts.lessonsTitled + " lessons, with the guide's own pacing across " +
      meta.weeks + " weeks. Lesson numbers follow the " + meta.edition +
      " edition — the one New York classrooms teach from, which is not the national " +
      "sequence."));
    var basis = el("p", "note");
    basis.innerHTML = "<b>How the item counts below are worked out: </b>by standard, " +
      "not by item. A released item is counted against a unit when the unit teaches " +
      "the standard that item assesses. That is not the same as saying the item " +
      "belongs to the unit — one standard can be taught in several units, so the " +
      "counts overlap and do not sum to " + itemsFor(grade).length + ". A per-item " +
      "curriculum alignment is a separate, hand-checked piece of work, and where " +
      "it exists it is shown on the question itself rather than in these counts.";
    intro.appendChild(basis);
    host.appendChild(intro);

    var summary = el("div", "card");
    summary.appendChild(el("h3", "", "The year at a glance"));
    summary.appendChild(table([
      { key: "unit", label: "Unit", num: true },
      { key: "title", label: "Title", wrap: true },
      { key: "week", label: "Starts week", num: true },
      { key: "days", label: "Days", sort: false, value: function (r) { return r.daysLo; } },
      { key: "lessons", label: "Lessons", num: true },
      { key: "optional", label: "Optional", num: true },
      { key: "ma", label: "Mid-unit check", sort: false,
        render: function (r) { return r.ma ? el("span", "tag", "yes") : "—"; } },
      { key: "post", label: "Taught after the test", wrap: true, sort: false,
        title: "Standards this unit teaches that NYSED designates for May-to-June "
             + "instruction, and so assesses the following year" },
      { key: "items", label: "Released items on its standards", num: true, desc: true }
    ], order.map(function (u) {
      var unit = units[u];
      var lessons = Object.keys(unit.lessons);
      var share = postTestShare(grade, unit);
      return {
        /* Grade 8's post-test standards go nowhere: there is no grade 9 State
           mathematics test, so they are taught after the last test that could
           assess them and then never assessed. Joining an empty list produced
           "1 of 3 -> grade" with the number missing. */
        post: !share || !share.post ? "\u2014"
              : (share.post === share.total ? "all " : share.post + " of ") +
                share.total + (share.to.length
                  ? " \u2192 grade " + share.to.join("/")
                  : " \u2192 not assessed"),
        unit: Number(u), title: unit.title, week: unit.startWeek,
        days: unit.days ? (unit.days[0] === unit.days[1] ? String(unit.days[0])
                           : unit.days[0] + "\u2013" + unit.days[1]) : "—",
        daysLo: unit.days ? unit.days[0] : null,
        lessons: lessons.length,
        optional: lessons.filter(function (n) { return unit.lessons[n].optional; }).length,
        ma: unit.midUnitAssessment,
        items: unitItems(grade, unit).length
      };
    }), { sortKey: "unit" }));
    var conv = el("p", "note");
    conv.textContent = meta.pacingConventions ? meta.pacingConventions.days : "";
    summary.appendChild(conv);
    host.appendChild(summary);

    /* One card per unit, sections in order, lessons under their section. A
       filter, because 427 lessons across the three grades is more than anyone
       wants to scroll. */
    var filterCard = el("div", "card");
    filterCard.appendChild(el("h3", "", "Every lesson"));
    var row = el("div", "controls");
    var lab = el("label", "", "Filter by lesson title, section or standard ");
    var box = el("input");
    box.type = "search";
    box.placeholder = "circumference, NY-7.G.4, \u2026";
    lab.appendChild(box);
    row.appendChild(lab);
    var count = el("span", "muted");
    row.appendChild(count);
    filterCard.appendChild(row);
    host.appendChild(filterCard);

    var listHost = el("div");
    host.appendChild(listHost);

    function matches(q, unit, n, lesson) {
      if (!q) return true;
      var hay = [lesson.title, lesson.sectionTitle, unit.title,
                 lesson.standards.join(" "), lesson.clusters.join(" ")]
        .join(" ").toLowerCase();
      return hay.indexOf(q) >= 0;
    }

    function draw() {
      var q = box.value.trim().toLowerCase();
      listHost.textContent = "";
      var shown = 0;
      order.forEach(function (u) {
        var unit = units[u];
        var keep = Object.keys(unit.lessons).sort(function (a, b) { return a - b; })
          .filter(function (n) { return matches(q, unit, n, unit.lessons[n]); });
        if (!keep.length) return;
        shown += keep.length;

        var card = el("div", "card");
        var h = el("h3", "", "Unit " + u + " · " + unit.title);
        card.appendChild(h);
        var bits = [];
        if (unit.days) bits.push(unit.days[0] === unit.days[1]
          ? unit.days[0] + " days" : unit.days[0] + "\u2013" + unit.days[1] + " days");
        if (unit.startWeek) bits.push("from week " + unit.startWeek);
        if (unit.midUnitAssessment) bits.push("has a mid-unit assessment");
        if (unit.whollyOptional) bits.push("optional in its entirety");
        bits.push(unitItems(grade, unit).length + " released items on its standards");
        card.appendChild(el("p", "lede", bits.join(" · ")));

        /* A unit with no released items at all. Left bare it reads as "the
           State never asks about this", which the data cannot support: about a
           quarter of every test is withheld, and the guide aligns some lessons
           to a whole cluster rather than a single standard, which cannot be
           matched to an item at all. Grade 6 Unit 5 is the case in point -- it
           teaches NY-6.NS.2 and NY-6.NS.3 and neither has ever been released. */
        var share = postTestShare(grade, unit);
        if (!unitItems(grade, unit).length && !(share && share.post)) {
          var zn = el("p", "note");
          zn.innerHTML = "<b>No released item assesses this unit's standards. </b>" +
            "That is not the same as never tested: roughly a quarter of every test " +
            "is withheld and never published, and some of this unit's lessons are " +
            "aligned by the guide to a whole cluster rather than to a single " +
            "standard, which cannot be matched to an item at all. Read this as " +
            "\u201cno evidence either way\u201d.";
          card.appendChild(zn);
        }

        /* Taught after the test that could assess it. Whole units can consist
           of these -- grade 7's Unit 8 is entirely post-test -- so a low or
           zero item count here has a specific, publishable explanation. */
        if (share && share.post) {
          var pn = el("p", "note");
          pn.innerHTML = "<b>Taught after your own test: </b>" +
            (share.post === share.total
              ? "every one of this unit's " + share.total + " standards is"
              : share.post + " of this unit's " + share.total + " standards are") +
            " designated by NYSED for May-to-June instruction. " +
            (share.to.length
              ? (share.post === share.total ? "They are" : "Those are") +
                " assessed on the grade " + share.to.join(" and ") + " test rather " +
                "than grade " + grade + ", so a low released-item count here is expected."
              : "There is no grade " + (grade + 1) + " State mathematics test, so " +
                (share.post === share.total ? "they are" : "those are") +
                " not assessed anywhere in this programme \u2014 taught, but never tested.");
          card.appendChild(pn);
        }

        var section = null;
        keep.forEach(function (n) {
          var lesson = unit.lessons[n];
          if (lesson.sectionLetter !== section) {
            section = lesson.sectionLetter;
            card.appendChild(el("h4", "", "Section " + section + " · " + lesson.sectionTitle));
          }
          var line = el("div", "lesson");
          line.appendChild(el("span", "mono lesson-no", grade + "." + u + "." + n));
          var name = el("span", "lesson-title", lesson.title);
          line.appendChild(name);
          if (lesson.optional) line.appendChild(el("span", "tag", "optional"));
          var codes = el("span", "lesson-codes");
          lesson.standards.forEach(function (c) { codes.appendChild(standardChip(c, grade)); });
          lesson.clusters.forEach(function (c) {
            /* "NY-7.G.Cluster-2" -> "G cluster 2". The full printed code is in
               the tooltip; the row needs the domain and the number, not the
               boilerplate. */
            var parts = /^NY-(\d)\.([A-Z]{1,3})\.Cluster-(\d+)$/.exec(c);
            var chip = el("span", "mono chip chip-cluster",
              parts ? (parts[2] + " cluster " + parts[3] +
                       (Number(parts[1]) !== grade ? " (grade " + parts[1] + ")" : "")) : c);
            chip.title = c + " — the guide cites this whole cluster rather than one " +
              "standard. Its number is the publisher's own and does not match NYSED's " +
              "cluster order, so it is shown as printed.";
            codes.appendChild(chip);
          });
          if (!lesson.standards.length && !lesson.clusters.length) {
            var blank = el("span", "muted", "the guide lists no standard");
            blank.title = "Not a gap in this site's data: the course guide's " +
              "Standards Addressed cell for this lesson is empty. Most are a unit's " +
              "opening lesson, which invites the mathematics rather than teaching a " +
              "standard.";
            codes.appendChild(blank);
          }
          line.appendChild(codes);
          card.appendChild(line);
        });
        listHost.appendChild(card);
      });
      count.textContent = q ? shown + " of " + cur.counts.lessonsTitled + " lessons"
                            : cur.counts.lessonsTitled + " lessons";
      if (q && !shown) {
        var empty = el("div", "card");
        empty.appendChild(el("p", "empty", "No lesson matches \u201c" + box.value + "\u201d."));
        listHost.appendChild(empty);
      }
    }
    box.addEventListener("input", draw);
    draw();

    /* The caveats, last but published. Unit numbering is the thing most likely
       to mislead someone comparing this against a national-edition document. */
    var caveats = el("div", "card");
    caveats.appendChild(el("h3", "", "Before comparing this against another document"));
    var ul = el("ul", "notes-list");
    meta.hazards.forEach(function (h) { ul.appendChild(el("li", "", h)); });
    caveats.appendChild(ul);
    if (cur.tableDisagreements && cur.tableDisagreements.length) {
      caveats.appendChild(el("h4", "", "Where the guide's own two alignment tables disagree"));
      caveats.appendChild(el("p", "lede",
        "The guide lists standards by lesson in one table and lessons by standard in " +
        "another. For grade " + grade + " they differ on " + cur.tableDisagreements.length +
        " pairs. Neither is authoritative over the other, so both readings are kept."));
      caveats.appendChild(table([
        { key: "lesson", label: "Lesson", render: function (r) { return el("span", "mono", r.lesson); } },
        { key: "standard", label: "Standard", render: function (r) { return el("span", "mono", r.standard); } },
        { key: "citedBy", label: "Cited by", wrap: true }
      ], cur.tableDisagreements, { sortKey: "lesson" }));
    }
    var src = el("p", "note");
    src.innerHTML = "<b>Source: </b>the Imagine IM New York Teacher Course Guides, " +
      "extracted and re-checked on every deploy. The pacing table is printed in all " +
      "three guides; every figure here was read from all three independently and the " +
      "three readings agree.";
    caveats.appendChild(src);
    host.appendChild(caveats);
    return host;
  }

  var VIEWS = {
    questions: viewQuestions, standards: viewStandards, difficulty: viewDifficulty,
    blueprint: viewBlueprint, posttest: viewPostTest, items: viewItems,
    curriculum: viewCurriculum, about: viewAbout
  };

  function render() {
    document.documentElement.setAttribute("data-grade", String(STATE.grade));
    Array.prototype.forEach.call(document.querySelectorAll(".grades button"), function (b) {
      b.setAttribute("aria-pressed", b.dataset.grade === String(STATE.grade) ? "true" : "false");
    });
    Array.prototype.forEach.call(document.querySelectorAll(".tabs button"), function (b) {
      b.setAttribute("aria-selected", b.dataset.view === STATE.view ? "true" : "false");
    });
    var statsHost = document.getElementById("stats");
    if (STATE.view === "about") statsHost.textContent = "";
    else renderStats(STATE.grade);
    var host = document.getElementById("view");
    host.textContent = "";
    host.appendChild(VIEWS[STATE.view](STATE.grade));
    window.scrollTo(0, 0);
  }

  function writeUrl() {
    var q = "?g=" + STATE.grade + "&v=" + STATE.view;
    history.replaceState(null, "", q);
    try { localStorage.setItem("mathalign68", q); } catch (e) { /* private window */ }
  }

  function readUrl() {
    var q = window.location.search;
    if (!q || q.indexOf("g=") === -1) {
      try { q = localStorage.getItem("mathalign68") || ""; } catch (e) { q = ""; }
    }
    var g = /[?&]g=(\d)/.exec(q), v = /[?&]v=(\w+)/.exec(q);
    if (g && D.meta.grades.indexOf(Number(g[1])) !== -1) STATE.grade = Number(g[1]);
    if (v && VIEWS[v[1]]) STATE.view = v[1];
    // Land on Standards rather than an empty Questions tab for a grade whose
    // items are not transcribed yet.
    if (STATE.view === "questions" &&
        !D.items.some(function (i) { return i.grade === STATE.grade && i.transcribed; })) {
      STATE.view = "standards";
    }
  }

  document.querySelector(".grades").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-grade]");
    if (!b) return;
    STATE.grade = Number(b.dataset.grade);
    writeUrl(); render();
  });
  document.querySelector(".tabs").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-view]");
    if (!b) return;
    STATE.view = b.dataset.view;
    writeUrl(); render();
  });

  var footLink = document.getElementById("tofb");
  if (footLink) {
    footLink.addEventListener("click", function (e) {
      e.preventDefault();
      STATE.view = "about";
      writeUrl();
      render();
    });
  }

  readUrl();
  render();
})();
