(() => {
  "use strict";
  const target = new Date("2026-12-18T00:00:00+03:00").getTime();
  const fields = {
    days: document.getElementById("cosmic-days"),
    hours: document.getElementById("cosmic-hours"),
    minutes: document.getElementById("cosmic-minutes"),
    seconds: document.getElementById("cosmic-seconds")
  };
  if (Object.values(fields).some((field) => !field)) return;
  const pad = (value) => String(value).padStart(2, "0");
  function updateCountdown() {
    const remaining = Math.max(0, target - Date.now());
    const totalSeconds = Math.floor(remaining / 1000);
    fields.days.textContent = String(Math.floor(totalSeconds / 86400)).padStart(2, "0");
    fields.hours.textContent = pad(Math.floor((totalSeconds % 86400) / 3600));
    fields.minutes.textContent = pad(Math.floor((totalSeconds % 3600) / 60));
    fields.seconds.textContent = pad(totalSeconds % 60);
    if (remaining <= 0) {
      Object.values(fields).forEach((field) => { field.textContent = "00"; });
      window.clearInterval(countdownInterval);
    }
  }
  updateCountdown();
  const countdownInterval = window.setInterval(updateCountdown, 1000);

  const canvas = document.getElementById("cosmic-countdown-canvas");
  const section = document.getElementById("cosmic-countdown");
  const context = canvas && canvas.getContext("2d");
  if (!context || !section) return;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let width = 0, height = 0, frame = 0;
  let particles = [];
  function resize() {
    const rect = section.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = rect.width; height = rect.height;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.min(170, Math.max(65, Math.round(width * height / 5200)));
    particles = Array.from({ length: count }, (_, index) => ({
      x: Math.random() * width, y: Math.random() * height,
      size: Math.random() * 1.65 + .25,
      speed: Math.random() * .24 + .035,
      drift: (Math.random() - .5) * .16,
      alpha: Math.random() * .58 + .18,
      hue: [205, 238, 270, 335][index % 4],
      shard: Math.random() > .79,
      rotation: Math.random() * Math.PI,
      spin: (Math.random() - .5) * .006
    }));
  }
  function draw() {
    context.clearRect(0, 0, width, height);
    for (const p of particles) {
      if (!reducedMotion) {
        p.y -= p.speed;
        p.x += p.drift;
        p.rotation += p.spin;
        if (p.y < -16) { p.y = height + 12; p.x = Math.random() * width; }
        if (p.x < -16) p.x = width + 12;
        if (p.x > width + 16) p.x = -12;
      }
      context.save();
      context.translate(p.x, p.y);
      context.rotate(p.rotation);
      context.globalAlpha = p.alpha;
      context.strokeStyle = "hsla(" + p.hue + ", 95%, 82%, .82)";
      context.fillStyle = "hsla(" + p.hue + ", 90%, 72%, .12)";
      context.shadowColor = "hsla(" + p.hue + ", 100%, 75%, .8)";
      context.shadowBlur = p.shard ? 12 : 5;
      if (p.shard) {
        context.beginPath();
        context.moveTo(0, -p.size * 5);
        context.lineTo(p.size * 1.5, p.size * 2);
        context.lineTo(-p.size * 1.1, p.size * 4);
        context.closePath();
        context.fill();
        context.stroke();
      } else {
        context.beginPath();
        context.arc(0, 0, p.size, 0, Math.PI * 2);
        context.fillStyle = "#dce5ff";
        context.fill();
      }
      context.restore();
    }
    if (!reducedMotion) frame = window.requestAnimationFrame(draw);
  }
  resize();
  draw();
  if ("ResizeObserver" in window) new ResizeObserver(resize).observe(section);
  else window.addEventListener("resize", resize, { passive: true });
  if (reducedMotion) window.cancelAnimationFrame(frame);
})();