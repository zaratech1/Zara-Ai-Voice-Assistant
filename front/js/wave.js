(() => {
  const canvas = document.getElementById('waveCanvas');
  const mini = document.getElementById('miniWaveCanvas');
  const ctx = canvas.getContext('2d');
  const miniCtx = mini.getContext('2d');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const tau = Math.PI * 2;
  const levels = {IDLE:.13, WAKE_LISTENING:.25, WAKE_DETECTED:.9, LISTENING:.95, PROCESSING:.64, THINKING:.64, EXECUTING:.5, SPEAKING:.8, ERROR:.75};
  let mode = 'IDLE', energy = .13, phase = 0, frame = null, previous = 0, errorUntil = 0;
  let width = 0, height = 0, miniWidth = 0, miniHeight = 0, errorTimer;

  // Fibonacci distribution gives a dense sphere without creating DOM particles.
  const particles = Array.from({length:1100}, (_, i) => {
    const y = 1 - 2 * (i + .5) / 1100;
    const radius = Math.sqrt(1 - y * y);
    const angle = i * Math.PI * (3 - Math.sqrt(5));
    const shell = i % 5 === 0 ? .55 + (i % 17) / 40 : 1;
    return {x:Math.cos(angle)*radius*shell, y:y*shell, z:Math.sin(angle)*radius*shell, size:.45+(i%7)/14};
  });

  function resize() {
    const scale = Math.min(devicePixelRatio || 1, 1.75);
    for (const [target, context] of [[canvas,ctx],[mini,miniCtx]]) {
      const rect = target.getBoundingClientRect();
      target.width = Math.round(rect.width * scale);
      target.height = Math.round(rect.height * scale);
      context.setTransform(scale,0,0,scale,0,0);
      if (target === canvas) {width=rect.width;height=rect.height}
      else {miniWidth=rect.width;miniHeight=rect.height}
    }
    requestDraw();
  }

  function drawOrb(now) {
    if (!width || !height) return;
    ctx.clearRect(0,0,width,height);
    const cx=width/2, cy=height/2, unit=Math.min(width,height);
    const rhythm=mode==='SPEAKING' ? Math.sin(phase*8)*.5+Math.sin(phase*13)*.25 : Math.sin(phase*3)*.4;
    const base=unit*(.365+energy*.009*rhythm);
    const error=now<errorUntil;
    const halo=ctx.createRadialGradient(cx,cy,base*.64,cx,cy,unit*.5);
    halo.addColorStop(0,'rgba(50,20,255,0)');
    halo.addColorStop(.48,error?'rgba(190,35,98,.13)':'rgba(66,21,255,.14)');
    halo.addColorStop(1,'rgba(50,20,255,0)');
    ctx.fillStyle=halo;ctx.fillRect(0,0,width,height);

    // Draw a few broad translucent ribbons, then fine luminous filaments.
    ctx.save();ctx.globalCompositeOperation='lighter';
    for(let layer=0;layer<12;layer++) {
      ctx.beginPath();
      for(let i=0;i<=180;i++) {
        const a=i/180*tau;
        const flow=a+phase*(.22+energy*.16);
        const ripple=Math.sin(flow*3+layer*.16)*.033 + Math.sin(a*5-phase*.8+layer*.2)*.014 + Math.cos(a*7+phase*.5+layer*.15)*.009;
        const r=base*(1+ripple*(.7+energy))+(layer-5)*unit*.0019;
        const x=cx+Math.cos(a)*r, y=cy+Math.sin(a)*r;
        if(!i)ctx.moveTo(x,y);else ctx.lineTo(x,y);
      }
      ctx.closePath();
      ctx.strokeStyle=error?(layer%2?'#a73cff':'#ee427f'):['#3214ff','#4c1dff','#6c3cff','#7651ff'][layer%4];
      ctx.lineWidth=layer<3 ? unit*(.022-layer*.006) : .65+(layer%3)*.3;
      ctx.globalAlpha=layer<3 ? .07+energy*.035 : .25+(layer%3)*.12;
      ctx.stroke();
    }
    ctx.globalAlpha=.32+energy*.15;ctx.strokeStyle='#9373ff';ctx.lineWidth=.7;
    ctx.beginPath();ctx.ellipse(cx,cy,base*.81,base*.83,phase*.07,0,tau);ctx.stroke();
    ctx.restore();

    const core=base*.67;
    const sphere=ctx.createRadialGradient(cx-core*.2,cy-core*.2,0,cx,cy,core*1.13);
    sphere.addColorStop(0,'#0d0918');sphere.addColorStop(.75,'#06050c');sphere.addColorStop(1,'rgba(23,10,48,0)');
    ctx.fillStyle=sphere;ctx.beginPath();ctx.arc(cx,cy,core*1.13,0,tau);ctx.fill();
    const rotation=phase*.17, cos=Math.cos(rotation), sin=Math.sin(rotation);
    ctx.fillStyle='#e9e9ff';
    // Back-facing points are dimmer and smaller; perspective preserves the spherical core.
    for(let i=0;i<particles.length;i++) {
      const p=particles[i];
      const x=p.x*cos+p.z*sin, z=p.z*cos-p.x*sin;
      const y=p.y*.96-z*.14, depth=(z+1)/2;
      const perspective=1+z*.12;
      const drift=Math.sin(phase*2+i*.71)*energy*.9;
      const size=p.size*(unit/380)*(.55+depth*.65);
      ctx.globalAlpha=(.2+depth*.8)*(.88+Math.sin(i*.8+phase*1.2)*.1+energy*.1);
      ctx.beginPath();ctx.arc(cx+x*core*perspective+drift,cy+y*core*perspective,size,0,tau);ctx.fill();
    }
    // A sparse dust field ties the particle core to the energy shell.
    for(let i=0;i<48;i++) {
      const a=i*2.399+phase*.045, r=base*(.87+(i%9)*.035);
      ctx.globalAlpha=.12+(i%4)*.08;ctx.fillStyle=i%3?'#9f7cff':'#e1d6ff';
      ctx.beginPath();ctx.arc(cx+Math.cos(a)*r,cy+Math.sin(a)*r,.45+(i%3)*.2,0,tau);ctx.fill();
    }
    ctx.globalAlpha=1;
  }

  function drawMini() {
    if (!miniWidth || !miniHeight) return;
    miniCtx.clearRect(0,0,miniWidth,miniHeight);
    miniCtx.strokeStyle='#a487fa';miniCtx.lineWidth=1.3;miniCtx.beginPath();
    for(let x=0;x<=miniWidth;x++) {
      const y=miniHeight/2+Math.sin(x*.38+phase*4)*Math.sin(Math.PI*x/miniWidth)*(2+energy*6);
      if(!x)miniCtx.moveTo(x,y);else miniCtx.lineTo(x,y);
    }
    miniCtx.stroke();
  }

  function draw(now) {
    frame=null;
    if(document.hidden) {previous=0;return}
    // Cap at 30 fps; use elapsed time so motion is independent of display refresh rate.
    const elapsed=previous ? now-previous : 34;
    if(elapsed>=32 || reduced.matches) {
      previous=now;
      energy+=((now<errorUntil ? .75 : levels[mode]??.13)-energy)*.1;
      if(!reduced.matches) phase+=Math.min(elapsed,80)*(.00032+energy*.00065);
      drawOrb(now);drawMini();
    }
    if(!reduced.matches) requestDraw();
  }
  function requestDraw() {if(frame===null&&!document.hidden)frame=requestAnimationFrame(draw)}
  const observer=new ResizeObserver(resize);observer.observe(canvas);observer.observe(mini);
  document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=null;previous=0}else requestDraw()});
  reduced.addEventListener('change',()=>{previous=0;requestDraw()});
  window.zaraWave = {
    setState(state) {
      if (state === 'ERROR') {
        errorUntil = performance.now() + 850;
        clearTimeout(errorTimer);
        // Reduced-motion mode also clears the brief error tint, without a continuous loop.
        errorTimer = setTimeout(requestDraw, 900);
      } else mode = state;
      requestDraw();
    }
  };
  resize();
})();
