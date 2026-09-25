(async () => {
  const results=document.getElementById('results'),frame=document.getElementById('preview');
  const assert=(condition,message)=>{if(!condition)throw Error(message)};
  const until=async predicate=>{for(let i=0;i<100;i++){if(predicate())return;await new Promise(r=>setTimeout(r,20))}throw Error('Timed out waiting for UI')};
  const check=async(name,run)=>{const li=document.createElement('li');results.append(li);try{await run();li.className='pass';li.textContent='PASS — '+name}catch(error){li.className='fail';li.textContent='FAIL — '+name+': '+error.message;throw error}};
  let html=await (await fetch('../front/index.html')).text();
  html=html.replace(/(src|href)="(assets\/|css\/|js\/)([^"]+)"/g, '$1="/front/$2$3"').replace('<script src="/eel.js"></script>','<script src="/tests/ui-fixture.js"></script>');
  frame.srcdoc=html;
  await new Promise(resolve=>frame.onload=resolve);
  const win=frame.contentWindow,doc=frame.contentDocument,$=id=>doc.getElementById(id);
  const click=id=>$(id).click();
  const key=(key,extras={})=>doc.dispatchEvent(new win.KeyboardEvent('keydown',{key,bubbles:true,...extras}));
  const section=name=>doc.querySelector(`.settings-nav [data-section="${name}"]`).click();
  const called=name=>win.fixture.calls.filter(c=>c.name===name);
  await until(()=>called('set_active_chat').length);
  await check('Home, preserved selectors and no duplicate IDs',()=>{
    const ids=[...doc.querySelectorAll('[id]')].map(el=>el.id);assert(ids.length===new Set(ids).size,'Duplicate IDs');
    assert(!$('welcome').hidden&&$('sidebar').inert,'Home or closed drawer incorrect');
    assert($('heroStatus').textContent==='Hello sir!! how may I help you?','Greeting missing');
  });
  await check('1366 × 768, 1920 × 1080 and mobile fit without overflow',async()=>{
    for(const [w,h] of [[1366,768],[1920,1080],[390,844],[320,568]]){
      frame.style.maxWidth='none';frame.style.width=w+'px';frame.style.height=h+'px';
      await new Promise(resolve=>win.requestAnimationFrame(()=>win.requestAnimationFrame(resolve)));
      const orb=$('visualizer').getBoundingClientRect(),bar=$('composer').getBoundingClientRect();
      assert(doc.documentElement.scrollWidth===w&&doc.documentElement.scrollHeight===h,`${w}: page overflow`);
      assert($('conversationScroll').scrollHeight===$('conversationScroll').clientHeight,`${w}: hero overflow`);
      assert(bar.bottom<=h&&bar.left>=0&&bar.right<=w&&orb.bottom<bar.top,`${w}: clipped layout`);
      if(w===1366)assert(orb.width>=300&&orb.width<=380,'1366 orb sizing');
      if(w===1920)assert(orb.width>=430&&orb.width<=500,'1920 orb sizing');
    }
    frame.style.width='850px';frame.style.height='700px';frame.style.maxWidth='100%';
  });
  await check('History drawer, Escape, focus trapping and new chat',async()=>{
    click('menuBtn');assert(!$('sidebar').inert&&doc.querySelector('.workspace').inert,'Drawer not modal');
    $('settingsBtn').focus();key('Tab');assert(doc.activeElement===$('collapseBtn'),'Focus did not wrap');
    key('Escape');assert($('sidebar').inert&&doc.activeElement===$('menuBtn'),'Close did not restore focus');
    click('menuBtn');click('newChatBtn');await until(()=>called('create_chat').length&&$('sidebar').inert);
    assert($('chatList').querySelectorAll('.chat-row').length===2,'Chat not added');
  });
  await check('Enter and Send route all requested commands exactly once',async()=>{
    for(const [i,text] of ['hello','open calculator','open canva','play music on youtube'].entries()){
      $('messageInput').value=text;
      if(i%2)$('composer').dispatchEvent(new win.Event('submit',{bubbles:true,cancelable:true}));
      else $('messageInput').dispatchEvent(new win.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
      await until(()=>!$('sendBtn').disabled);
      assert(called('send_message').filter(c=>c.args[0]===text).length===1,'Duplicate or missing send');
    }
    assert($('messages').children.length===8&&$('welcome').hidden,'Chat view not rendered');
    const before=called('send_message').length;
    $('messageInput').dispatchEvent(new win.KeyboardEvent('keydown',{key:'Enter',shiftKey:true,bubbles:true}));
    assert(called('send_message').length===before,'Shift+Enter submitted');
  });
  await check('History rename, reload and delete preserve the existing APIs',async()=>{
    click('menuBtn');doc.querySelector('.chat-row.active .chat-menu').click();await until(()=>$('currentTitle').textContent==='Renamed verification chat');
    assert($('currentTitle').textContent==='Renamed verification chat','Rename not rendered');
    key('Escape');click('menuBtn');doc.querySelector('.chat-row.active .chat-entry').click();await until(()=>$('sidebar').inert);
    assert($('messages').children.length===8,'History not loaded');
    click('menuBtn');doc.querySelector('.chat-row.active .chat-menu:last-child').click();await until(()=>called('delete_chat').length&&$('sidebar').inert);
    assert(!$('welcome').hidden&&$('chatList').querySelectorAll('.chat-row').length===1,'Delete fallback failed');
  });
  await check('Mic start/stop and assistant state visuals',async()=>{
    click('micBtn');await until(()=>called('start_listening').length);assert($('micBtn').classList.contains('listening'),'Mic inactive');
    click('micBtn');await until(()=>called('stop_listening').length);assert(!$('micBtn').classList.contains('listening'),'Mic stuck');
    for(const state of ['WAKE_LISTENING','WAKE_DETECTED','LISTENING','PROCESSING','THINKING','EXECUTING','SPEAKING','ERROR','IDLE'])win.backend_event('state',{state,label:state});
    win.backend_event('wake_status',{status:'active'});assert($('wakeIndicator').textContent.includes('Hey Zara active'),'Wake status missing');
    win.backend_event('ai_status',{status:'connected'});assert($('aiIndicator').textContent.includes('AI online'),'AI status missing');
  });
  await check('All settings sections, registry and contact handlers',async()=>{
    click('mobileSettingsBtn');assert(!$('settingsModal').hidden&&$('appShell').inert,'Settings not modal');
    for(const name of ['general','voice','ai','wake','applications','websites','contacts','privacy','about']){
      section(name);assert(doc.querySelector(`.settings-section[data-section="${name}"]`).classList.contains('active'),'Section missing: '+name);
    }
    await until(()=>called('get_registry').length===2&&called('get_contacts').length===1);
    section('general');$('themeSelect').value='light';click('saveSettingsBtn');await until(()=>doc.documentElement.dataset.theme==='light');
    assert(called('update_settings').at(-1).args[0].ai_endpoint==='http://127.0.0.1:8080/v1','AI config lost on save');
    section('ai');click('testAiBtn');await until(()=>called('test_ai_connection').length);assert($('aiIndicator').dataset.status==='connected','AI test did not update header');
    section('voice');click('testVoiceBtn');await until(()=>called('test_voice').length);
    key('Escape');assert($('settingsModal').hidden&&!$('appShell').inert,'Settings did not close');
  });
  await check('WhatsApp confirmation buttons retain token routing (mock only)',async()=>{
    for(const approved of [false,true]){
      win.backend_event('whatsapp_confirmation',{token:'fixture-token',to:'Test contact',message:'Test only'});
      click(approved?'sendConfirmBtn':'cancelConfirmBtn');await until(()=>$('confirmModal').hidden);
      assert(called('confirm_whatsapp').at(-1).args[1]===approved,'Confirmation routing changed');
    }
  });
  await check('No JavaScript errors during interaction suite',()=>assert(win.fixture.errors.length===0,win.fixture.errors.join('\n')));
  document.title='PASS — ZARA UI smoke test';
})().catch(error=>{document.title='FAIL — ZARA UI smoke test';console.error(error)});
