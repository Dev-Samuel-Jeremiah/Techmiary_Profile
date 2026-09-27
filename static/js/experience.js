/* Site-wide motion — a small, dependency-free 3D layer.
   - Canvas point scenes (globe, ring, cube lattice, wave field, helix) for
     the hero, page banners and CTA, projected by hand (no WebGL, no library)
     and paused when off-screen.
   - Pointer parallax, 3D tilt cards, magnetic buttons, count-up figures,
     split-word headings, a sticky project stack and a drawn process line.
   With prefers-reduced-motion the scenes render one still frame and every
   other effect is skipped, leaving the finished page. */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  var root = document.body;
  if (!root) return;

  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, t) { return a + (b - a) * t; }

  /* ---- Shared scroll loop ------------------------------------------------ */
  var scrollTasks = [];
  var scrollQueued = false;
  var lastScrollY = window.scrollY;
  var scrollVelocity = 0;
  function runScrollTasks() {
    scrollQueued = false;
    for (var i = 0; i < scrollTasks.length; i++) scrollTasks[i]();
  }
  function queueScroll() {
    scrollVelocity += (window.scrollY - lastScrollY);
    lastScrollY = window.scrollY;
    if (!scrollQueued) { scrollQueued = true; window.requestAnimationFrame(runScrollTasks); }
  }
  window.addEventListener("scroll", queueScroll, { passive: true });
  window.addEventListener("resize", queueScroll);

  /* ---- Scroll progress bar ---------------------------------------------- */
  var progressBar = root.querySelector(".scroll-progress");
  if (progressBar) {
    scrollTasks.push(function () {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      progressBar.style.setProperty("--progress", max > 0 ? (window.scrollY / max).toFixed(4) : 0);
    });
  }

  /* ---- 3D point scenes ---------------------------------------------------- */
  function makeSprite(rgb) {
    var c = document.createElement("canvas");
    c.width = c.height = 64;
    var g = c.getContext("2d");
    var grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, "rgba(255,255,255,1)");
    grad.addColorStop(0.18, "rgba(" + rgb + ",0.95)");
    grad.addColorStop(0.5, "rgba(" + rgb + ",0.25)");
    grad.addColorStop(1, "rgba(" + rgb + ",0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 64, 64);
    return c;
  }
  var SPRITES = {
    teal: makeSprite("25,211,197"),
    violet: makeSprite("138,116,255"),
    blue: makeSprite("93,135,255")
  };

  function fibonacciSphere(n) {
    var pts = [];
    var golden = Math.PI * (3 - Math.sqrt(5));
    for (var i = 0; i < n; i++) {
      var y = 1 - (i / (n - 1)) * 2;
      var r = Math.sqrt(1 - y * y);
      var t = golden * i;
      pts.push({ x: Math.cos(t) * r, y: y, z: Math.sin(t) * r });
    }
    return pts;
  }

  function torus(nu, nv, R, r) {
    var pts = [];
    for (var i = 0; i < nu; i++) {
      var u = (i / nu) * Math.PI * 2;
      for (var j = 0; j < nv; j++) {
        var v = (j / nv) * Math.PI * 2 + (i % 2) * (Math.PI / nv);
        pts.push({
          x: (R + r * Math.cos(v)) * Math.cos(u),
          y: r * Math.sin(v),
          z: (R + r * Math.cos(v)) * Math.sin(u)
        });
      }
    }
    return pts;
  }

  function cubeLattice(n, size) {
    var pts = [], step = (size * 2) / (n - 1);
    for (var i = 0; i < n; i++) for (var j = 0; j < n; j++) for (var k = 0; k < n; k++) {
      var onSurface = i === 0 || j === 0 || k === 0 || i === n - 1 || j === n - 1 || k === n - 1;
      if (onSurface) pts.push({ x: -size + i * step, y: -size + j * step, z: -size + k * step });
    }
    pts.step = step;
    return pts;
  }

  function wavePlane(cols, rows) {
    var pts = [];
    for (var i = 0; i < cols; i++) for (var j = 0; j < rows; j++) {
      var x = (i / (cols - 1)) * 2.6 - 1.3, z = (j / (rows - 1)) * 2 - 1;
      pts.push({ x: x, y: 0, z: z, bx: x, bz: z });
    }
    return pts;
  }

  function helix(n) {
    var pts = [];
    for (var i = 0; i < n; i++) {
      var y = (i / (n - 1)) * 2.2 - 1.1, a = y * 3.4;
      pts.push({ x: Math.cos(a) * 0.46, y: y, z: Math.sin(a) * 0.46 });
      pts.push({ x: Math.cos(a + Math.PI) * 0.46, y: y, z: Math.sin(a + Math.PI) * 0.46 });
    }
    return pts;
  }

  function nearestLinks(pts, k, maxDist) {
    var links = [];
    var seen = {};
    for (var i = 0; i < pts.length; i++) {
      var best = [];
      for (var j = 0; j < pts.length; j++) {
        if (i === j) continue;
        var dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y, dz = pts[i].z - pts[j].z;
        var d = dx * dx + dy * dy + dz * dz;
        if (d > maxDist * maxDist) continue;
        best.push([d, j]);
      }
      best.sort(function (a, b) { return a[0] - b[0]; });
      for (var m = 0; m < Math.min(k, best.length); m++) {
        var a = Math.min(i, best[m][1]), b = Math.max(i, best[m][1]);
        var key = a * 10000 + b;
        if (!seen[key]) { seen[key] = 1; links.push([a, b]); }
      }
    }
    return links;
  }

  function slerp(a, b, t) {
    var dot = clamp(a.x * b.x + a.y * b.y + a.z * b.z, -1, 1);
    var om = Math.acos(dot);
    if (om < 1e-4) return { x: a.x, y: a.y, z: a.z };
    var s = Math.sin(om);
    var wa = Math.sin((1 - t) * om) / s, wb = Math.sin(t * om) / s;
    return { x: a.x * wa + b.x * wb, y: a.y * wa + b.y * wb, z: a.z * wa + b.z * wb };
  }

  function Scene(canvas, kind) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.kind = kind;
    this.visible = true;
    this.rotY = 0;
    this.tiltX = kind === "ring" ? 1.2 : 0.32;
    this.pointer = { x: 0, y: 0 };
    this.eased = { x: 0, y: 0 };
    this.arcs = [];
    this.nextArc = 0;
    var small = window.innerWidth < 768;
    if (kind === "globe") {
      this.points = fibonacciSphere(small ? 260 : 460);
      this.links = nearestLinks(this.points, 3, small ? 0.36 : 0.27);
      this.satellites = [
        { tilt: 1.15, spin: 0.2, radius: 1.3, phase: 0, speed: 0.00042, sprite: SPRITES.teal },
        { tilt: 1.15, spin: 0.2, radius: 1.3, phase: Math.PI, speed: 0.00042, sprite: SPRITES.teal },
        { tilt: -0.9, spin: -0.5, radius: 1.18, phase: 1.3, speed: -0.00055, sprite: SPRITES.violet },
        { tilt: -0.9, spin: -0.5, radius: 1.18, phase: 4.2, speed: -0.00055, sprite: SPRITES.violet }
      ];
    } else if (kind === "cube") {
      this.points = cubeLattice(small ? 5 : 7, 0.62);
      this.links = nearestLinks(this.points, 4, this.points.step * 1.02);
      this.tiltX = 0.55;
      this.satellites = [];
    } else if (kind === "wave") {
      this.points = wavePlane(small ? 26 : 38, small ? 16 : 22);
      this.links = [];
      this.tiltX = 0.62;
      this.satellites = [];
    } else if (kind === "helix") {
      this.points = helix(small ? 34 : 52);
      this.links = [];
      for (var h = 0; h < this.points.length; h += 6) this.links.push([h, h + 1]);
      for (h = 0; h + 2 < this.points.length; h++) this.links.push([h, h + 2]);
      this.tiltX = 0.18;
      this.satellites = [];
    } else {
      this.points = torus(small ? 110 : 200, small ? 10 : 14, 1, 0.2);
      this.links = [];
      this.satellites = [];
    }
    this.resize();
  }

  Scene.prototype.resize = function () {
    var rect = this.canvas.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.w = Math.max(1, rect.width);
    this.h = Math.max(1, rect.height);
    this.canvas.width = Math.round(this.w * dpr);
    this.canvas.height = Math.round(this.h * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var m = Math.min(this.w, this.h);
    this.radius = {
      globe: m * 0.34, cube: m * 0.34, wave: m * 0.3, helix: m * 0.38,
      // Square banner canvases need a smaller ring than the wide CTA band.
      ring: this.w / this.h < 1.4 ? m * 0.3 : Math.min(this.w * 0.36, this.h * 0.95)
    }[this.kind];
  };

  // Rotate a unit-space point by the scene's current Y spin and X tilt, then
  // project with a simple perspective divide.
  Scene.prototype.project = function (p, out) {
    var spin = this.kind === "wave" ? Math.sin(this.rotY * 0.6) * 0.5 : this.rotY;
    var ay = spin + this.eased.x * 0.6;
    var ax = this.tiltX + this.eased.y * 0.35;
    var cy = Math.cos(ay), sy = Math.sin(ay), cx = Math.cos(ax), sx = Math.sin(ax);
    var x = p.x * cy - p.z * sy;
    var z = p.x * sy + p.z * cy;
    var y = p.y * cx - z * sx;
    z = p.y * sx + z * cx;
    var fov = 3.2;
    var scale = fov / (fov - z);
    out.x = this.w / 2 + x * this.radius * scale;
    out.y = this.h / 2 + y * this.radius * scale;
    out.z = z;
    out.s = scale;
    return out;
  };

  Scene.prototype.spawnArc = function (now) {
    var pts = this.points;
    for (var tries = 0; tries < 12; tries++) {
      var a = pts[(Math.random() * pts.length) | 0];
      var b = pts[(Math.random() * pts.length) | 0];
      var dot = a.x * b.x + a.y * b.y + a.z * b.z;
      if (dot < 0.6 && dot > -0.4) {
        this.arcs.push({ a: a, b: b, start: now, life: 2400, lift: 0.18 + Math.random() * 0.2 });
        return;
      }
    }
  };

  Scene.prototype.draw = function (now, dt) {
    var ctx = this.ctx;
    var w = this.w, h = this.h;
    ctx.clearRect(0, 0, w, h);

    this.eased.x = lerp(this.eased.x, this.pointer.x, 0.06);
    this.eased.y = lerp(this.eased.y, this.pointer.y, 0.06);
    var boost = clamp(Math.abs(scrollVelocity) * 0.00004, 0, 0.004);
    this.rotY += dt * (0.00016 + boost);
    if (this.kind === "wave") {
      var t0 = now * 0.0011;
      for (var w0 = 0; w0 < this.points.length; w0++) {
        var wp = this.points[w0];
        wp.y = 0.16 * Math.sin(wp.bx * 2.4 + t0) * Math.cos(wp.bz * 2.1 + t0 * 0.8);
      }
    } else if (this.kind === "cube") {
      this.tiltX = 0.55 + Math.sin(now * 0.00035) * 0.35;
    }

    var proj = this._proj || (this._proj = this.points.map(function () { return {}; }));
    for (var i = 0; i < this.points.length; i++) this.project(this.points[i], proj[i]);

    // Back hemisphere first, dim, so the front reads as solid.
    var isRing = this.kind !== "globe";
    ctx.fillStyle = isRing ? "rgba(150,170,255,0.35)" : "rgba(120,140,220,0.35)";
    for (i = 0; i < proj.length; i++) {
      var q = proj[i];
      if (q.z >= 0) continue;
      var r0 = (isRing ? 1.1 : 1.05) * q.s;
      ctx.globalAlpha = 0.25 + (q.z + 1) * 0.25;
      ctx.fillRect(q.x - r0 / 2, q.y - r0 / 2, r0, r0);
    }
    ctx.globalAlpha = 1;

    // Mesh links, strongest on the near side.
    if (this.links.length) {
      ctx.lineWidth = 0.7;
      for (i = 0; i < this.links.length; i++) {
        var p1 = proj[this.links[i][0]], p2 = proj[this.links[i][1]];
        var depth = (p1.z + p2.z) / 2;
        if (depth < -0.35) continue;
        ctx.strokeStyle = "rgba(140,170,255," + (0.08 + (depth + 0.35) * 0.22).toFixed(3) + ")";
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }
    }

    // Front points.
    for (i = 0; i < proj.length; i++) {
      q = proj[i];
      if (q.z < 0) continue;
      var t = q.z;
      var rad = (isRing ? 1.1 + t * 0.9 : 1.25 + t * 1.1) * q.s;
      ctx.fillStyle = isRing
        ? "rgba(" + ((150 + t * 105) | 0) + "," + ((190 + t * 65) | 0) + ",255," + (0.6 + t * 0.4).toFixed(2) + ")"
        : "rgba(" + ((190 + t * 65) | 0) + "," + ((205 + t * 50) | 0) + ",255," + (0.55 + t * 0.45).toFixed(2) + ")";
      ctx.beginPath();
      ctx.arc(q.x, q.y, rad, 0, 6.2832);
      ctx.fill();
    }

    // Data arcs travelling between nodes over the surface.
    if (this.kind === "globe") {
      if (now > this.nextArc && this.arcs.length < 5) {
        this.spawnArc(now);
        this.nextArc = now + 700 + Math.random() * 900;
      }
      var tmp = {};
      for (var k = this.arcs.length - 1; k >= 0; k--) {
        var arc = this.arcs[k];
        var life = (now - arc.start) / arc.life;
        if (life >= 1) { this.arcs.splice(k, 1); continue; }
        var head = clamp(life * 1.6, 0, 1);
        var tail = clamp(life * 1.6 - 0.55, 0, 1);
        var fade = life > 0.75 ? 1 - (life - 0.75) / 0.25 : 1;
        var steps = 30;
        ctx.beginPath();
        var started = false;
        for (var s = 0; s <= steps; s++) {
          var u = tail + (head - tail) * (s / steps);
          var m = slerp(arc.a, arc.b, u);
          var lift = 1 + arc.lift * Math.sin(Math.PI * u);
          m.x *= lift; m.y *= lift; m.z *= lift;
          this.project(m, tmp);
          if (!started) { ctx.moveTo(tmp.x, tmp.y); started = true; } else { ctx.lineTo(tmp.x, tmp.y); }
        }
        var g = ctx.createLinearGradient(0, 0, w, h);
        g.addColorStop(0, "rgba(25,211,197," + (0.9 * fade).toFixed(2) + ")");
        g.addColorStop(1, "rgba(138,116,255," + (0.9 * fade).toFixed(2) + ")");
        ctx.strokeStyle = g;
        ctx.lineWidth = 1.6;
        ctx.stroke();
        if (head < 1) {
          var hs = 18 * tmp.s;
          ctx.globalAlpha = fade;
          ctx.drawImage(SPRITES.teal, tmp.x - hs / 2, tmp.y - hs / 2, hs, hs);
          ctx.globalAlpha = 1;
        }
      }
    }

    // Satellites on tilted orbits, occluded by the globe when behind it.
    for (var n = 0; n < this.satellites.length; n++) {
      var sat = this.satellites[n];
      var ang = sat.phase + now * sat.speed;
      var ox = Math.cos(ang) * sat.radius, oz = Math.sin(ang) * sat.radius;
      var ct = Math.cos(sat.tilt), st = Math.sin(sat.tilt), cs = Math.cos(sat.spin), ss = Math.sin(sat.spin);
      var p = { x: ox * cs, y: -oz * st, z: oz * ct };
      p = { x: p.x, y: p.y + ox * ss * 0.3, z: p.z };
      var sp = this.project(p, {});
      var behind = sp.z < 0 && Math.hypot(sp.x - w / 2, sp.y - h / 2) < this.radius * 0.95;
      if (behind) continue;
      var size = 26 * sp.s;
      ctx.drawImage(sat.sprite, sp.x - size / 2, sp.y - size / 2, size, size);
    }

    // Soft core glow.
    if (this.kind === "globe") {
      var cg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, this.radius * 1.25);
      cg.addColorStop(0, "rgba(61,107,255,0.16)");
      cg.addColorStop(1, "rgba(61,107,255,0)");
      ctx.fillStyle = cg;
      ctx.fillRect(0, 0, w, h);
    }
  };

  var scenes = [];
  Array.prototype.forEach.call(root.querySelectorAll("canvas[data-scene]"), function (canvas) {
    if (!canvas.getContext) return;
    var scene = new Scene(canvas, canvas.getAttribute("data-scene"));
    scenes.push(scene);
    var host = canvas.closest("[data-hero]") || canvas.parentElement;
    if (!reduceMotion && finePointer && host) {
      host.addEventListener("pointermove", function (e) {
        var r = host.getBoundingClientRect();
        scene.pointer.x = ((e.clientX - r.left) / r.width - 0.5) * 2;
        scene.pointer.y = ((e.clientY - r.top) / r.height - 0.5) * 2;
      });
      host.addEventListener("pointerleave", function () { scene.pointer.x = 0; scene.pointer.y = 0; });
    }
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        scene.visible = entries[0].isIntersecting;
      }, { rootMargin: "80px" }).observe(canvas);
    }
  });

  var resizeTimer;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () { scenes.forEach(function (s) { s.resize(); if (reduceMotion) s.draw(0, 0); }); }, 120);
  });

  if (scenes.length) {
    if (reduceMotion) {
      scenes.forEach(function (s) { s.rotY = 0.6; s.draw(0, 0); });
    } else {
      var last = performance.now();
      var frame = function (now) {
        var dt = Math.min(now - last, 50);
        last = now;
        scrollVelocity *= 0.9;
        if (!document.hidden) {
          for (var i = 0; i < scenes.length; i++) if (scenes[i].visible) scenes[i].draw(now, dt);
        }
        window.requestAnimationFrame(frame);
      };
      window.requestAnimationFrame(frame);
    }
  }

  if (reduceMotion) return;

  /* ---- Hero: spotlight, parallax floats, scroll lift ---------------------- */
  var hero = root.querySelector("[data-hero]");
  if (hero) {
    var floats = hero.querySelectorAll("[data-depth]");
    var copy = hero.querySelector("[data-hero-copy]");
    if (finePointer) {
      hero.addEventListener("pointermove", function (e) {
        var r = hero.getBoundingClientRect();
        var nx = (e.clientX - r.left) / r.width, ny = (e.clientY - r.top) / r.height;
        hero.style.setProperty("--mx", (nx * 100).toFixed(1) + "%");
        hero.style.setProperty("--my", (ny * 100).toFixed(1) + "%");
        Array.prototype.forEach.call(floats, function (el) {
          var d = parseFloat(el.getAttribute("data-depth")) || 1;
          el.style.setProperty("--px", (-(nx - 0.5) * 36 * d).toFixed(1) + "px");
          el.style.setProperty("--py", (-(ny - 0.5) * 28 * d).toFixed(1) + "px");
        });
      });
    }
    if (copy) {
      scrollTasks.push(function () {
        var h = hero.offsetHeight || 1;
        var p = clamp(window.scrollY / h, 0, 1);
        copy.style.transform = "translate3d(0," + (-p * 60).toFixed(1) + "px,0)";
        copy.style.opacity = (1 - p * 0.7).toFixed(3);
      });
    }
  }

  /* ---- Count-up figures -------------------------------------------------- */
  var counters = root.querySelectorAll("[data-count]");
  if (counters.length && "IntersectionObserver" in window) {
    var countObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        countObserver.unobserve(entry.target);
        var el = entry.target;
        var target = parseInt(el.getAttribute("data-count"), 10) || 0;
        var start = performance.now();
        var dur = 1600;
        (function tick(now) {
          var t = clamp((now - start) / dur, 0, 1);
          var eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
          el.textContent = Math.round(target * eased);
          if (t < 1) window.requestAnimationFrame(tick);
        })(start);
      });
    }, { threshold: 0.6 });
    Array.prototype.forEach.call(counters, function (el) { el.textContent = "0"; countObserver.observe(el); });
  }

  /* ---- Split-word headings ---------------------------------------------- */
  var headings = root.querySelectorAll(".section-heading h2, h2.lx-split");
  if (headings.length && "IntersectionObserver" in window) {
    var splitObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        splitObserver.unobserve(entry.target);
      });
    }, { threshold: 0.3 });
    Array.prototype.forEach.call(headings, function (h2) {
      if (h2.children.length) return; // only plain-text headings
      var words = h2.textContent.trim().split(/\s+/);
      h2.setAttribute("aria-label", h2.textContent.trim());
      h2.textContent = "";
      words.forEach(function (word, i) {
        var outer = document.createElement("span");
        outer.className = "lx-sw";
        outer.setAttribute("aria-hidden", "true");
        var inner = document.createElement("span");
        inner.textContent = word;
        inner.style.setProperty("--i", i);
        outer.appendChild(inner);
        h2.appendChild(outer);
        if (i < words.length - 1) h2.appendChild(document.createTextNode(" "));
      });
      h2.classList.add("lx-split", "is-armed");
      splitObserver.observe(h2);
    });
  }

  /* ---- 3D tilt cards with glare ------------------------------------------ */
  if (finePointer) {
    Array.prototype.forEach.call(root.querySelectorAll(".card, .lx-feature"), function (card) {
      if (card.querySelector("form, input, textarea, select") || card.closest("[data-no-tilt]")) return;
      card.classList.add("card--tilt");
      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
        card.classList.add("is-tilting");
        card.style.transform = "perspective(1000px) rotateX(" + ((0.5 - py) * 10).toFixed(2) + "deg) rotateY(" + ((px - 0.5) * 12).toFixed(2) + "deg) translate3d(0,-6px,0)";
        card.style.setProperty("--gx", (px * 100).toFixed(1) + "%");
        card.style.setProperty("--gy", (py * 100).toFixed(1) + "%");
      });
      card.addEventListener("pointerleave", function () {
        card.classList.remove("is-tilting");
        card.style.transform = "";
      });
    });

    /* ---- Magnetic buttons ------------------------------------------------ */
    Array.prototype.forEach.call(root.querySelectorAll("[data-magnetic]"), function (btn) {
      btn.addEventListener("pointermove", function (e) {
        var r = btn.getBoundingClientRect();
        var dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2);
        btn.style.transform = "translate3d(" + (dx * 0.18).toFixed(1) + "px," + (dy * 0.3).toFixed(1) + "px,0)";
      });
      btn.addEventListener("pointerleave", function () { btn.style.transform = ""; });
    });
  }

  /* ---- Sticky project stack: earlier cards recede as the next arrives ---- */
  var stack = root.querySelector("[data-stack]");
  var wide = window.matchMedia("(min-width: 992px)");
  if (stack) {
    var items = Array.prototype.slice.call(stack.querySelectorAll(".lx-stack__item"));
    scrollTasks.push(function () {
      for (var i = 0; i < items.length; i++) {
        var card = items[i].firstElementChild;
        if (!wide.matches || i === items.length - 1) {
          card.style.removeProperty("--s"); card.style.removeProperty("--rx"); card.style.removeProperty("--b");
          continue;
        }
        var a = items[i].getBoundingClientRect(), b = items[i + 1].getBoundingClientRect();
        var cover = clamp((a.bottom - b.top) / a.height, 0, 1);
        card.style.setProperty("--s", (1 - cover * 0.07).toFixed(4));
        card.style.setProperty("--rx", (cover * 7).toFixed(2) + "deg");
        card.style.setProperty("--b", (1 - cover * 0.1).toFixed(3));
      }
    });
  }

  /* ---- Process line drawn by scroll -------------------------------------- */
  var process = root.querySelector("[data-process] .lx-steps");
  if (process) {
    scrollTasks.push(function () {
      var r = process.getBoundingClientRect();
      var vh = window.innerHeight;
      process.style.setProperty("--line", clamp((vh * 0.85 - r.top) / (r.height + vh * 0.35), 0, 1).toFixed(3));
    });
  }

  runScrollTasks();
})();
