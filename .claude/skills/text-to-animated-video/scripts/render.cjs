// Render a deterministic scene.html (window.renderAt(t), optional window.ready) to stills or MP4.
// node render.cjs stills scene.html 0.5,2,4 outDir/ [W H]
// node render.cjs video  scene.html T0 T1 out.mp4 [FPS] [W H]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path'), fs = require('fs');
(async () => {
  const [mode, scene, ...a] = process.argv.slice(2);
  let W = 1920, H = 1080;
  const vp = (w, h) => { if (w && h) { W = +w; H = +h; } };
  if (mode === 'stills') vp(a[2], a[3]); else vp(a[4], a[5]);
  const br = await chromium.launch();
  const pg = await br.newPage({ viewport: { width: W, height: H } });
  pg.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await pg.goto('file://' + path.resolve(scene));
  await pg.evaluate(() => window.ready || document.fonts.ready);
  const shot = async (opts) => {
    const el = await pg.$('canvas');
    return el ? el.screenshot(opts) : pg.screenshot({ ...opts, clip: { x: 0, y: 0, width: W, height: H } });
  };
  if (mode === 'stills') {
    const [times, outDir] = a; fs.mkdirSync(outDir, { recursive: true });
    for (const t of times.split(',')) {
      await pg.evaluate(t => window.renderAt(t), +t);
      await shot({ path: path.join(outDir, `s_${t}.png`) });
    }
  } else if (mode === 'video') {
    const [t0, t1, out, fpsS] = a; const fps = +(fpsS || 30);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '' + fps, '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const f0 = Math.round(+t0 * fps), f1 = Math.round(+t1 * fps);
    for (let f = f0; f < f1; f++) {
      await pg.evaluate(t => window.renderAt(t), f / fps);
      const buf = await shot({ type: 'jpeg', quality: 92 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((f - f0) % (fps * 2) === 0) process.stdout.write(`\r${((f - f0) / (f1 - f0) * 100).toFixed(0)}%`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('\rdone', out);
  } else { console.error('mode must be stills or video'); process.exit(1); }
  await br.close();
})();
