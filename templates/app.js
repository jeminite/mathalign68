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
  function table(cols, rows, opts) {
    opts = opts || {};
    var wrapper = el("div", "scroll");
    var t = el("table"), thead = el("thead"), tr = el("tr");
    var sort = { key: opts.sortKey || null, dir: opts.sortDir || 1 };

    cols.forEach(function (c) {
      var th = el("th", (c.num ? "num " : "") + (c.sort === false ? "plain" : ""), c.label);
      if (c.sort !== false) {
        th.addEventListener("click", function () {
          if (sort.key === c.key) sort.dir = -sort.dir;
          else { sort.key = c.key; sort.dir = c.desc ? -1 : 1; }
          draw();
        });
      }
      if (c.title) th.title = c.title;
      tr.appendChild(th);
    });
    thead.appendChild(tr);
    t.appendChild(thead);
    var tbody = el("tbody");
    t.appendChild(tbody);
    wrapper.appendChild(t);

    function draw() {
      Array.prototype.forEach.call(thead.querySelectorAll("th"), function (th, i) {
        if (cols[i].key === sort.key) th.setAttribute("aria-sort", sort.dir > 0 ? "ascending" : "descending");
        else th.removeAttribute("aria-sort");
      });
      var data = rows.slice();
      if (sort.key) {
        var col = cols.filter(function (c) { return c.key === sort.key; })[0];
        data.sort(function (a, b) {
          var x = col.value ? col.value(a) : a[sort.key];
          var y = col.value ? col.value(b) : b[sort.key];
          if (x === null || x === undefined) return 1;
          if (y === null || y === undefined) return -1;
          if (x === y) return 0;
          return (x > y ? 1 : -1) * sort.dir;
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
    var fYear = el("select");
    var anyY = el("option", "", "All years"); anyY.value = ""; fYear.appendChild(anyY);
    uniq(all.map(function (i) { return i.year; })).sort().forEach(function (y) {
      var o = el("option", "", String(y)); o.value = y; fYear.appendChild(o);
    });
    var search = el("input");
    search.type = "search";
    search.placeholder = "Search the questions";
    var showAns = el("input"); showAns.type = "checkbox"; showAns.checked = true;
    var l1 = el("label"); l1.appendChild(el("span", "", "Year")); l1.appendChild(fYear);
    var l2 = el("label"); l2.appendChild(search);
    var l3 = el("label"); l3.appendChild(showAns); l3.appendChild(el("span", "", "Show answers"));
    controls.appendChild(l1); controls.appendChild(l2); controls.appendChild(l3);
    host.appendChild(controls);

    var count = el("p", "lede");
    host.appendChild(count);
    var list = el("div");
    host.appendChild(list);

    function paint() {
      var q = search.value.trim().toLowerCase();
      var rows = all.filter(function (i) {
        if (fYear.value && String(i.year) !== fYear.value) return false;
        if (!q) return true;
        var hay = (i.stemPlain || "") + " " + i.standard + " " + (i.domainLabel || "") +
                  " " + (i.choiceList || []).map(function (c) { return c.text; }).join(" ");
        return hay.toLowerCase().indexOf(q) !== -1;
      });
      count.textContent = rows.length + " question" + (rows.length === 1 ? "" : "s");
      list.textContent = "";
      if (!rows.length) {
        list.appendChild(el("p", "empty", "Nothing matches that."));
        return;
      }
      var f = frag();
      rows.forEach(function (i) { f.appendChild(questionCard(i, showAns.checked)); });
      list.appendChild(f);
    }
    fYear.addEventListener("change", paint);
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

    var foot = el("div", "row");
    foot.style.marginTop = "12px";
    var link = pdfLink(i, "Check this item in the official PDF"
                          + (i.pdfPage ? " (page " + i.pdfPage + ")" : ""));
    foot.appendChild(link);
    box.appendChild(foot);
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
    function picker(label, values, render) {
      var sel = el("select");
      var any = el("option", "", "All"); any.value = ""; sel.appendChild(any);
      values.forEach(function (v) {
        var o = el("option", "", render ? render(v) : v); o.value = v; sel.appendChild(o);
      });
      var l = el("label"); l.appendChild(el("span", "", label)); l.appendChild(sel);
      controls.appendChild(l);
      return sel;
    }
    var fYear = picker("Year", uniq(all.map(function (i) { return i.year; })).sort());
    var fDomain = picker("Domain", uniq(all.map(function (i) { return i.domain; })).sort(),
                         function (d) { return D.blueprint.domains[d] || d; });
    var fType = picker("Type", ["Multiple Choice", "Constructed Response"]);
    var fHard = picker("Difficulty", ["hard", "mid", "easy"], function (b) {
      return { hard: "Hard (under 0.50)", mid: "Middling (0.50–0.74)",
               easy: "Easier (0.75 and up)" }[b];
    });
    var fPost = picker("Prior grade", ["yes", "no"], function (v) {
      return v === "yes" ? "Prior-grade standards only" : "This grade only"; });
    var search = el("input");
    search.type = "search";
    search.placeholder = "Standard code or domain";
    var ls = el("label"); ls.appendChild(search); controls.appendChild(ls);
    host.appendChild(controls);

    var count = el("p", "lede");
    host.appendChild(count);
    var slot = el("div");
    host.appendChild(slot);

    function paint() {
      var q = search.value.trim().toLowerCase();
      var rows = all.filter(function (i) {
        if (fYear.value && String(i.year) !== fYear.value) return false;
        if (fDomain.value && i.domain !== fDomain.value) return false;
        if (fType.value && i.type !== fType.value) return false;
        if (fHard.value && band(i.pValue) !== fHard.value) return false;
        if (fPost.value === "yes" && !i.postTest) return false;
        if (fPost.value === "no" && i.postTest) return false;
        if (q && (i.standard + " " + (i.domainLabel || "")).toLowerCase().indexOf(q) === -1) return false;
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
        { key: "secondary", label: "Also", sort: false, render: function (i) {
            return i.secondary && i.secondary.length ? i.secondary.join(", ") : "—"; } },
        { key: "pValue", label: "Statewide", render: function (i) { return pCell(i.pValue); } },
        { key: "avgPointsEarned", label: "Avg pts", num: true, render: function (i) {
            return i.avgPointsEarned === null ? "—" : i.avgPointsEarned.toFixed(2); } },
        { key: "pdfPage", label: "Official PDF", sort: false, render: function (i) { return pdfLink(i); } }
      ], rows, { sortKey: "year" }));
    }
    [fYear, fDomain, fType, fHard, fPost].forEach(function (s) { s.addEventListener("change", paint); });
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

  var VIEWS = {
    questions: viewQuestions, standards: viewStandards, difficulty: viewDifficulty,
    blueprint: viewBlueprint, posttest: viewPostTest, items: viewItems,
    about: viewAbout
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
