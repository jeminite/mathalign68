/* Minimal .xlsx reader -- ZIP + SpreadsheetML, no dependencies.
 *
 * The same file runs in Node (for the test harness) and in the browser. It
 * takes the bytes of a workbook and returns grid[row][col] of strings, numbers
 * and nulls. It does nothing else: no formulas, no styles, no dates, no
 * multi-sheet selection beyond "the first one".
 *
 * WHY NOT SheetJS
 * preflight.py refuses to publish an analyze page that loads anything from a
 * third-party origin, so the CDN tag RegentsAlign uses cannot come across, and
 * the alternative is committing ~950 KB of vendored library to serve one sheet
 * of one workbook. Every entry in a real ISA export is deflate-compressed, and
 * DecompressionStream('deflate-raw') is native, so the whole job is this file.
 *
 * SheetJS stays in devDependencies and is still the reason to trust this: the
 * engine suite reads the same fixture both ways and asserts the grids match.
 * Two independent parse paths agreeing is the only reason to trust a parse.
 */
(function (root) {
  "use strict";

  /* --------------------------------------------------------------- inflate */

  // Node and the browser have entirely different inflate APIs and neither is
  // optional, so pick one at call time rather than at load time -- the engine
  // suite loads this file in Node, the page loads it in a browser.
  function inflateRaw(bytes) {
    if (typeof module !== "undefined" && module.exports) {
      return Promise.resolve(new Uint8Array(require("zlib").inflateRawSync(bytes)));
    }
    var ds = new DecompressionStream("deflate-raw");
    var stream = new Blob([bytes]).stream().pipeThrough(ds);
    return new Response(stream).arrayBuffer().then(function (b) {
      return new Uint8Array(b);
    });
  }

  /* ------------------------------------------------------------------- zip */

  // Read the central directory rather than walking local headers: a local
  // header may carry sizes of zero and defer them to a data descriptor, and
  // then there is no way to know where the entry ends. The central directory
  // always has the real sizes.
  function unzip(buf) {
    var b = new Uint8Array(buf);
    var dv = new DataView(b.buffer, b.byteOffset, b.byteLength);

    // End-of-central-directory, scanned backwards because the comment that may
    // follow it is variable length.
    var eocd = -1;
    for (var i = b.length - 22; i >= 0 && i >= b.length - 66000; i--) {
      if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error("Not a .xlsx file: no ZIP end-of-central-directory record.");

    var count = dv.getUint16(eocd + 10, true);
    var off = dv.getUint32(eocd + 16, true);
    var entries = [];
    for (var e = 0; e < count; e++) {
      if (dv.getUint32(off, true) !== 0x02014b50) break;
      var method = dv.getUint16(off + 10, true);
      var csize = dv.getUint32(off + 20, true);
      var nameLen = dv.getUint16(off + 28, true);
      var extraLen = dv.getUint16(off + 30, true);
      var cmtLen = dv.getUint16(off + 32, true);
      var local = dv.getUint32(off + 42, true);
      var name = utf8(b.subarray(off + 46, off + 46 + nameLen));
      entries.push({ name: name, method: method, csize: csize, local: local });
      off += 46 + nameLen + extraLen + cmtLen;
    }

    var map = {};
    entries.forEach(function (en) {
      // The local header's own name and extra lengths are authoritative for
      // where the data starts; they can differ from the central directory's.
      var ln = dv.getUint16(en.local + 26, true);
      var lx = dv.getUint16(en.local + 28, true);
      var start = en.local + 30 + ln + lx;
      map[en.name] = { method: en.method, data: b.subarray(start, start + en.csize) };
    });
    return map;
  }

  function utf8(bytes) {
    if (typeof TextDecoder !== "undefined") return new TextDecoder("utf-8").decode(bytes);
    return Buffer.from(bytes).toString("utf8");
  }

  function read(map, name) {
    var en = map[name];
    if (!en) return Promise.resolve(null);
    if (en.method === 0) return Promise.resolve(utf8(en.data));   // stored
    if (en.method !== 8) return Promise.reject(new Error(
      "Unsupported ZIP compression in " + name + " (method " + en.method + ")."));
    return inflateRaw(en.data).then(utf8);
  }

  /* ------------------------------------------------------------------- xml */

  // A deliberately small XML reader. The parts of SpreadsheetML this needs are
  // flat and attribute-driven, and DOMParser does not exist in Node.
  function unescapeXml(s) {
    return s.replace(/&(lt|gt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);/g, function (m, g) {
      if (g === "lt") return "<";
      if (g === "gt") return ">";
      if (g === "amp") return "&";
      if (g === "quot") return '"';
      if (g === "apos") return "'";
      if (g.charAt(1) === "x") return String.fromCharCode(parseInt(g.slice(2), 16));
      return String.fromCharCode(parseInt(g.slice(1), 10));
    });
  }

  // Concatenate every <t> in a chunk. A shared string split across formatting
  // runs arrives as several <t> elements and is one string; taking only the
  // first would silently truncate a header like "Q1 (6.RP.2)" to "Q1 (".
  function textOf(chunk) {
    var out = "", re = /<t[^>]*>([\s\S]*?)<\/t>|<t[^>]*\/>/g, m;
    while ((m = re.exec(chunk)) !== null) out += unescapeXml(m[1] || "");
    return out;
  }

  function sharedStrings(xml) {
    if (!xml) return [];
    var out = [], re = /<si\b[^>]*>([\s\S]*?)<\/si>|<si\b[^>]*\/>/g, m;
    while ((m = re.exec(xml)) !== null) out.push(textOf(m[1] || ""));
    return out;
  }

  /* ----------------------------------------------------------------- cells */

  // "AA" -> 26. Cell references are decoded rather than counted, because a row
  // that omits an empty cell entirely is normal in this format and counting
  // would shift every later value one column left.
  function colIndex(ref) {
    var n = 0;
    for (var i = 0; i < ref.length; i++) {
      var c = ref.charCodeAt(i);
      if (c < 65 || c > 90) break;
      n = n * 26 + (c - 64);
    }
    return n - 1;
  }

  function sheetGrid(xml, strings) {
    var grid = [], maxCol = -1;
    var rowRe = /<row\b([^>]*)>([\s\S]*?)<\/row>|<row\b([^>]*)\/>/g, rm;
    while ((rm = rowRe.exec(xml)) !== null) {
      var attrs = rm[1] || rm[3] || "";
      var body = rm[2] || "";
      var rAttr = /\br="(\d+)"/.exec(attrs);
      var r = rAttr ? parseInt(rAttr[1], 10) - 1 : grid.length;
      var row = grid[r] || (grid[r] = []);

      var cellRe = /<c\b([^>]*)>([\s\S]*?)<\/c>|<c\b([^>]*)\/>/g, cm;
      while ((cm = cellRe.exec(body)) !== null) {
        var cAttrs = cm[1] || cm[3] || "";
        var inner = cm[2] || "";
        var refM = /\br="([A-Z]+)\d+"/.exec(cAttrs);
        if (!refM) continue;
        var c = colIndex(refM[1]);
        var t = (/\bt="([^"]+)"/.exec(cAttrs) || [])[1] || "n";
        var val = null;

        if (t === "inlineStr") {
          val = textOf(inner);
        } else if (t === "s") {
          var vm = /<v[^>]*>([\s\S]*?)<\/v>/.exec(inner);
          if (vm) val = strings[parseInt(vm[1], 10)];
          if (val === undefined) val = null;
        } else {
          var vn = /<v[^>]*>([\s\S]*?)<\/v>/.exec(inner);
          if (vn) {
            var raw = unescapeXml(vn[1]);
            if (t === "str" || t === "e") val = raw;
            else if (t === "b") val = raw === "1";
            else {
              var num = parseFloat(raw);
              val = isNaN(num) ? raw : num;
            }
          }
        }
        row[c] = val;
        if (c > maxCol) maxCol = c;
      }
    }

    // Densify. Callers index grid[r][c] directly and a hole would read as
    // undefined rather than null; every consumer here treats null as "blank".
    for (var i = 0; i < grid.length; i++) {
      var g = grid[i] || (grid[i] = []);
      for (var j = 0; j <= maxCol; j++) if (g[j] === undefined) g[j] = null;
    }
    return grid;
  }

  /* ------------------------------------------------------------------- api */

  // Returns a Promise of grid[row][col] for the workbook's first sheet.
  function parse(buf) {
    var map;
    try {
      map = unzip(buf);
    } catch (err) {
      return Promise.reject(err);
    }
    // Sheet order in workbook.xml is presentation order; the file on disk may
    // be named anything, so take the lowest-numbered worksheet part rather
    // than assuming sheet1.xml exists.
    var sheets = Object.keys(map).filter(function (n) {
      return /^xl\/worksheets\/sheet\d+\.xml$/.test(n);
    }).sort(function (a, b) {
      return parseInt(/(\d+)/.exec(a)[1], 10) - parseInt(/(\d+)/.exec(b)[1], 10);
    });
    if (!sheets.length) {
      return Promise.reject(new Error("That file has no worksheets in it."));
    }
    return read(map, "xl/sharedStrings.xml").then(function (ssXml) {
      var strings = sharedStrings(ssXml);
      return read(map, sheets[0]).then(function (sheetXml) {
        return sheetGrid(sheetXml || "", strings);
      });
    });
  }

  // Every sheet, in workbook order, with its name. The analyse page deliberately
  // reads only the first sheet -- a results export has one -- but a longitudinal
  // workbook keeps one sheet per cohort, and a caller that needs those should not
  // have to reimplement the unzip to get them.
  function parseAll(buf) {
    var map;
    try {
      map = unzip(buf);
    } catch (err) {
      return Promise.reject(err);
    }
    var sheets = Object.keys(map).filter(function (n) {
      return /^xl\/worksheets\/sheet\d+\.xml$/.test(n);
    }).sort(function (a, b) {
      return parseInt(/(\d+)/.exec(a)[1], 10) - parseInt(/(\d+)/.exec(b)[1], 10);
    });
    if (!sheets.length) return Promise.reject(new Error("That file has no worksheets in it."));

    return read(map, "xl/workbook.xml").then(function (wbXml) {
      // Sheet names live in workbook.xml in presentation order, which is not
      // necessarily the sheetN.xml numbering order. Zipping them by position is
      // what every other reader does and is right often enough to be useful;
      // callers that must be certain should match on content, not on name.
      var names = [];
      var re = /<sheet\b[^>]*\bname="([^"]*)"/g, m;
      while ((m = re.exec(wbXml || "")) !== null) names.push(unescapeXml(m[1]));
      return read(map, "xl/sharedStrings.xml").then(function (ssXml) {
        var strings = sharedStrings(ssXml);
        var out = [];
        function step(i) {
          if (i >= sheets.length) return out;
          return read(map, sheets[i]).then(function (sheetXml) {
            out.push({ name: names[i] || sheets[i], grid: sheetGrid(sheetXml || "", strings) });
            return step(i + 1);
          });
        }
        return step(0);
      });
    });
  }

  var api = { parse: parse, parseAll: parseAll, colIndex: colIndex };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.XlsxLite = api;
})(this);
