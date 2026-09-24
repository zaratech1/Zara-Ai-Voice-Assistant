(() => {
  const canvas = document.getElementById('waveCanvas');
  const ctx = canvas.getContext('2d');
  const mini = document.getElementById('miniWaveCanvas');
  const miniCtx = mini.getContext('2d');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let mode = 'IDLE', energy = .15, phase = 0;
  function resize(target, context) {
    const rect = target.getBoundingClientRect();
    const scale = Math.min(devicePixelRatio || 1, 2);
    target.width = Math.round(rect.width * scale);
    target.height = Math.round(rect.height * scale);
    context.setTransform(scale, 0, 0, scale, 0, 0);
  }
  new ResizeObserver(() => {resize(canvas,ctx);resize(mini,miniCtx)}).observe(canvas);
  resize(mini,miniCtx);
  const colors = ['#c3b6ff', '#9885ef', '#7666d6', '#5d87c4'];
  function draw() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const target = {IDLE:.15, WAKE_LISTENING:.2, WAKE_DETECTED:.82, LISTENING:.95, PROCESSING:.56, THINKING:.56, SPEAKING:.78, EXECUTING:.4, ERROR:.25}[mode] ?? .15;
    energy += (target - energy) * .055;
    phase += reduced.matches ? 0 : .009 + energy * .018;
    const cx=w/2, cy=h/2, base=Math.min(w,h)*.305;
    const halo=ctx.createRadialGradient(cx,cy,base*.15,cx,cy,base*1.65);
    halo.addColorStop(0,'rgba(119,96,231,.11)');halo.addColorStop(1,'rgba(119,96,231,0)');
    ctx.fillStyle=halo;ctx.beginPath();ctx.arc(cx,cy,base*1.65,0,Math.PI*2);ctx.fill();
    for(let layer=0;layer<4;layer++){
      ctx.beginPath();
      const points=190;
      for(let i=0;i<=points;i++){
        const a=i/points*Math.PI*2;
        const ripple=Math.sin(a*3+phase*(layer+1)*.8)*5+Math.sin(a*5-phase*1.3+layer)*4;
        const motion=ripple*energy*(layer===0?1:1.1);
        const radius=base+layer*7+motion;
        const x=cx+Math.cos(a)*radius,y=cy+Math.sin(a)*radius;
        if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
      }
      ctx.closePath();ctx.strokeStyle=colors[layer];ctx.globalAlpha=.72-layer*.12;ctx.lineWidth=layer===0?1.8:1.15;ctx.stroke();
    }
    ctx.globalAlpha=1;
    for(let i=0;i<34;i++){
      const a=i/34*Math.PI*2+phase*.35;
      const distance=base*1.27+Math.sin(i*5+phase)*energy*7;
      ctx.fillStyle=i%3===0?'#b8a4ff':'#796fb1';ctx.globalAlpha=.26+energy*.25;
      ctx.beginPath();ctx.arc(cx+Math.cos(a)*distance,cy+Math.sin(a)*distance,1.1,0,Math.PI*2);ctx.fill();
    }
    ctx.globalAlpha=1;
    const mw=mini.clientWidth,mh=mini.clientHeight;
    miniCtx.clearRect(0,0,mw,mh);
    for(let layer=0;layer<2;layer++){
      miniCtx.beginPath();
      for(let x=0;x<=mw;x++){
        const envelope=Math.sin(Math.PI*x/mw);
        const y=mh/2+Math.sin(x*.26+phase*3+layer)*envelope*(2+energy*8)+(layer?3:-3);
        if(x===0)miniCtx.moveTo(x,y);else miniCtx.lineTo(x,y);
      }
      miniCtx.strokeStyle=colors[layer];miniCtx.globalAlpha=.85-layer*.2;miniCtx.lineWidth=1.4;miniCtx.stroke();
    }
    miniCtx.globalAlpha=1;
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
  window.zaraWave = {setState(state){mode=state}};
})();
