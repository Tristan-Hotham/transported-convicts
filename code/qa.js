// QA: open index.html at desktop and phone widths, log console errors, take screenshots to qa/.
// Run from the study root with a static server (python3 -m http.server 8941; set PORT to change).
// MapLibre from a local npm copy (the CDN is not reachable from the build container); tiles and fonts are blocked here.
// OFFLINE=1 also blocks MapLibre itself, to check that the page degrades gracefully; the chart screenshots are taken in
// that run, because software WebGL in the build container makes every screenshot of a page with a live map slow.
const { chromium } = require("playwright");
const fs = require("fs");
const ML = process.env.MAPLIBRE_DIST || "/tmp/ml/node_modules/maplibre-gl/dist";
fs.mkdirSync("qa", { recursive: true });
(async () => {
  const b = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
  const errs = [];
  const sizes = process.env.ONLY ? [[process.env.ONLY, process.env.ONLY === "phone" ? 390 : 1280, 860]] : [["desktop", 1280, 900], ["phone", 390, 844]];
  for (const [nm, vw, vh] of sizes) {
    const p = await b.newPage({ viewport: { width: vw, height: vh }, deviceScaleFactor: nm === "phone" ? 2 : 1 });
    p.setDefaultTimeout(300000);
    await p.route(/arcgisonline|googleapis|gstatic/, r => r.abort());
    if (process.env.OFFLINE) await p.route(/maplibre-gl/, r => r.abort());
    else {
      await p.route(/maplibre-gl\.js$/, r => r.fulfill({ path: ML + "/maplibre-gl.js" }));
      await p.route(/maplibre-gl\.css$/, r => r.fulfill({ path: ML + "/maplibre-gl.css" }));
    }
    p.on("console", m => { if (m.type() === "error" && !/ERR_FAILED|net::|Failed to fetch|AJAXError/.test(m.text())) errs.push(nm + ": " + m.text()); });
    p.on("pageerror", e => errs.push(nm + " pageerror: " + e.message));
    await p.goto("http://localhost:" + (process.env.PORT || 8941) + "/index.html", { waitUntil: "load" });
    const shot = async (sel, f) => { await p.locator(sel).scrollIntoViewIfNeeded(); await p.waitForTimeout(700); await p.locator(sel).screenshot({ path: `qa/${pre}${nm}_${f}.png` }); };
    const pre = process.env.OFFLINE ? "offline_" : "";
    if (process.env.OFFLINE) {
      await p.waitForTimeout(1500);
      console.log(nm, "offline note:", await p.textContent("#map"));
      await p.screenshot({ path: `qa/${pre}${nm}_top.png` }); await shot("#atlas", "map");
      for (const c of ["yearChart", "colTable", "coverChart", "daysChart", "deathChart", "portChart", "shipTable", "womenChart", "worldTable"]) await shot("#" + c, c);
      if (nm === "phone") { await p.click("#theme"); await p.waitForTimeout(800); for (const c of ["yearChart", "daysChart", "deathChart"]) await shot("#" + c, "dark_" + c); }
      const ov = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth); console.log(nm, "offline horizontal overflow px:", ov);
      await p.close(); continue;
    }
    for (let k = 0; k < 60 && !(await p.evaluate(() => !!window.map && !document.getElementById("loading"))); k++) await p.waitForTimeout(500);
    console.log(nm, "map ready:", await p.evaluate(() => !!window.map && !document.getElementById("loading")));
    await p.waitForTimeout(1500);
    await p.screenshot({ path: `qa/${nm}_top.png` });
    await shot("#atlas", "map_1868");
    console.log(nm, "rendered voyage lines:", await p.evaluate(() => new Set(map.queryRenderedFeatures({ layers: ["voy"] }).map(f => f.properties.i)).size));
    await p.evaluate(() => setYear(1833)); await p.waitForTimeout(600); await shot("#atlas", "map_1833_cum");
    await p.click('#modeRow [data-m="year"]'); await p.waitForTimeout(700); await shot("#atlas", "map_1833_year");
    console.log(nm, "side 1833:", (await p.textContent("#side")).slice(0, 160).replace(/\s+/g, " "));
    // play for two seconds, then pause: ships at sea
    await p.evaluate(() => setYear(1820)); await p.click("#play"); await p.waitForTimeout(2200); await shot("#atlas", "map_playing"); await p.click("#play");
    console.log(nm, "after play year:", await p.textContent("#yv"), "ships drawn:", await p.evaluate(() => map.getSource("ships")._data.features ? map.getSource("ships")._data.features.length : -1));
    await p.click('#modeRow [data-m="cum"]'); await p.evaluate(() => setYear(1868));
    // click a route near the Cape of Good Hope
    const box = await p.locator("#map").boundingBox();
    await p.evaluate(() => map.jumpTo({ center: [20, -40], zoom: 3 })); await p.waitForTimeout(900);
    const pt = await p.evaluate(() => { const r = SITE.routes[0]; const q = map.project([19.0, -41.0]); return q; });
    await p.mouse.click(box.x + pt.x, box.y + pt.y); await p.waitForTimeout(700); await shot("#atlas", "click_cape");
    console.log(nm, "popup:", (await p.evaluate(() => (document.querySelector(".maplibregl-popup-content") || {}).innerText || "none")).slice(0, 200).replace(/\n/g, " | "));
    await p.evaluate(() => { if (window.popup) popup.remove(); map.jumpTo({ center: [62, 4], zoom: innerWidth < 900 ? .15 : 1.05 }); });
    // search a ship
    await p.fill("#q", "Hougoumont"); await p.waitForTimeout(400); await p.keyboard.press("Enter"); await p.waitForTimeout(1600); await shot("#atlas", "search_hougoumont");
    console.log(nm, "ship panel:", (await p.textContent("#side")).slice(0, 140).replace(/\s+/g, " "));
    await p.fill("#q", "Mangles"); await p.waitForTimeout(400); await p.keyboard.press("Enter"); await p.waitForTimeout(1600); await shot("#atlas", "search_mangles");
    await p.click("#side .back"); await p.waitForTimeout(300);
    await p.click('#colRow .btn:nth-child(5)'); await p.waitForTimeout(700); await shot("#atlas", "map_wa_only"); await p.click('#colRow .btn:nth-child(2)');
    await p.click('#focusRow .btn:nth-child(4)'); await p.waitForTimeout(1600); await shot("#atlas", "map_australia");
    await p.click('#focusRow .btn:nth-child(3)'); await p.waitForTimeout(1600); await shot("#atlas", "map_british_isles");
    await p.click('#focusRow .btn:nth-child(2)'); await p.waitForTimeout(1400);
    await p.click(".lyrBtn"); await p.waitForTimeout(300); await shot("#map", "layers_panel");
    await p.click('.lyrPanel [data-k="stations"]'); await p.click('.lyrPanel [data-k="intra"]'); await p.click(".lyrBtn"); await p.waitForTimeout(700); await shot("#atlas", "map_layers_on");
    await p.click(".lyrBtn"); await p.click(".lyrPanel .reset"); await p.click(".lyrBtn");
    await p.click("#worldTable tr[data-i='3']"); await p.waitForTimeout(2200); await shot("#atlas", "world_guiana");
    console.log(nm, "world popup:", (await p.evaluate(() => (document.querySelector(".maplibregl-popup-content") || {}).innerText || "none")).slice(0, 160).replace(/\n/g, " | "));
    if (nm === "phone") {
      await p.click("#theme"); await p.waitForTimeout(1200); await shot("#atlas", "dark_map");
      await p.click("#theme");
    }
    await p.locator("#atlas").scrollIntoViewIfNeeded(); await p.click(".mfs-btn"); await p.waitForTimeout(1500); await p.screenshot({ path: `qa/${nm}_fullscreen.png` });
    console.log(nm, "fullscreen:", await p.evaluate(() => !!document.fullscreenElement || !!document.querySelector(".mfs-fake")));
    await p.click(".mfs-btn"); await p.waitForTimeout(500);
    const ov = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    console.log(nm, "horizontal overflow px:", ov);
    await p.close();
  }
  console.log("errors:", errs.length ? errs : "none");
  await b.close();
})();
