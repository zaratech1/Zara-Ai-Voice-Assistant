(() => {
  const $ = id => document.getElementById(id);
  const shell = $('appShell');
  let activeChat = null, chats = [], settings = {}, voices = [], busy = false, listening = false, pendingToken = null;
  let toastTimer, settingsOpener;
  function showConversation(hasMessages) {
    $('welcome').hidden = hasMessages;
    shell.classList.toggle('chat-mode', hasMessages);
  }
  function setDrawer(open, restoreFocus = true) {
    shell.classList.toggle('drawer-open', open);
    $('sidebar').inert = !open;
    $('sidebar').setAttribute('aria-hidden', String(!open));
    $('sidebar').setAttribute('role', 'dialog');
    $('sidebar').setAttribute('aria-modal', String(open));
    document.querySelector('.workspace').inert = open;
    $('drawerBackdrop').hidden = !open;
    $('menuBtn').setAttribute('aria-expanded', String(open));
    $('menuBtn').setAttribute('aria-label', open ? 'Close chat history' : 'Open chat history');
    if (open && $('settingsModal').hidden) $('newChatBtn').focus();
    else if (restoreFocus) $('menuBtn').focus();
  }
  function updateAiStatus(status) {
    $('aiIndicator').dataset.status = status;
    $('aiIndicator').textContent = {connected:'● AI online',offline:'○ AI offline',disabled:'○ AI off',unknown:'○ AI not tested'}[status] || '○ AI not tested';
  }

  async function api(name, ...args) {
    if (!window.eel || typeof eel[name] !== 'function') throw new Error('Assistant connection is unavailable. Start ZARA with main.py.');
    const response = await eel[name](...args)();
    if (!response || !response.ok) throw new Error(response?.error || 'The request failed.');
    return response.data;
  }
  function notice(message) {
    $('toast').textContent = message;
    $('toast').hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $('toast').hidden = true, 4200);
  }
  function state(name, label) {
    $('topStatus').textContent = label || name;
    const heroLabel = ['IDLE','WAKE_LISTENING'].includes(name) ? 'Hello sir!! how may I help you?' : label || name;
    if ($('heroStatus').textContent !== heroLabel) {
      $('heroStatus').textContent = heroLabel;
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
        $('heroStatus').animate([{opacity:.35},{opacity:1}], {duration:240});
      }
    }
    $('statusDot').classList.toggle('active', name !== 'IDLE');
    $('heroStatusDot').classList.toggle('active', name !== 'IDLE');
    $('micBtn').classList.toggle('listening', name === 'LISTENING');
    $('micBtn').setAttribute('aria-label', name === 'LISTENING' ? 'Stop listening' : 'Start listening');
    $('micBtn').title = name === 'LISTENING' ? 'Stop listening' : 'Start listening';
    $('thinkingRow').hidden = !['PROCESSING','EXECUTING'].includes(name) || !$('welcome').hidden;
    window.zaraWave?.setState(name);
  }
  function setBusy(value) {busy=value;$('sendBtn').disabled=value}
  function dateGroup(value) {
    const date=new Date(value.replace(' ','T')+'Z'), now=new Date();
    const today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
    const yesterday=new Date(today);yesterday.setDate(today.getDate()-1);
    if(date>=today)return 'Today';if(date>=yesterday)return 'Yesterday';
    if(date>=new Date(today.getTime()-6*86400000))return 'Previous 7 days';return 'Older';
  }
  function renderChats() {
    const list=$('chatList');list.replaceChildren();let group='';
    for(const chat of chats){
      const next=dateGroup(chat.updated_at);
      if(next!==group){group=next;const heading=document.createElement('div');heading.className='chat-group-title';heading.textContent=group;list.append(heading)}
      const row=document.createElement('div');row.className='chat-row'+(chat.id===activeChat?' active':'');
      const open=document.createElement('button');open.className='chat-entry';open.textContent=chat.title;open.title=chat.title;open.onclick=()=>selectChat(chat.id);
      const rename=document.createElement('button');rename.className='chat-menu';rename.textContent='✎';rename.title='Rename chat';rename.setAttribute('aria-label','Rename '+chat.title);rename.onclick=()=>renameChat(chat);
      const remove=document.createElement('button');remove.className='chat-menu';remove.textContent='×';remove.title='Delete chat';remove.setAttribute('aria-label','Delete '+chat.title);remove.onclick=()=>deleteChat(chat);
      row.append(open,rename,remove);list.append(row);
    }
  }
  function renderMessage(message) {
    if(message.role==='assistant'){setBusy(false);$('thinkingRow').hidden=true}
    if(message.session_id!==activeChat)return;
    showConversation(true);
    const row=document.createElement('article');row.className='message '+message.role+(message.message_type==='error'?' error':'');
    if(message.role==='assistant'){const avatar=document.createElement('div');avatar.className='message-avatar';avatar.textContent='Z';row.append(avatar)}
    const content=document.createElement('div');content.className='message-content';
    const meta=document.createElement('div');meta.className='message-meta';meta.textContent=message.role==='user'?'YOU':'ZARA';
    const body=document.createElement('div');body.className='message-body';body.textContent=message.content;
    content.append(meta,body);row.append(content);$('messages').append(row);
    $('conversationScroll').scrollTop=$('conversationScroll').scrollHeight;
  }
  async function selectChat(id) {
    try{
      const messages=await api('get_chat_history',id);
      await api('set_active_chat',id);
      activeChat=id;$('messages').replaceChildren();showConversation(messages.length>0);
      for(const message of messages)renderMessage(message);
      $('currentTitle').textContent=chats.find(chat=>chat.id===id)?.title||'New chat';
      renderChats();setDrawer(false, false);$('messageInput').focus();
    }catch(error){notice(error.message)}
  }
  async function createChat(){try{const chat=await api('create_chat');chats.unshift(chat);await selectChat(chat.id)}catch(error){notice(error.message)}}
  async function renameChat(chat){const title=prompt('Rename conversation',chat.title);if(title===null)return;try{const changed=await api('rename_chat',chat.id,title);chats=chats.map(row=>row.id===chat.id?changed:row);if(activeChat===chat.id)$('currentTitle').textContent=changed.title;renderChats()}catch(error){notice(error.message)}}
  async function deleteChat(chat){if(!confirm(`Delete “${chat.title}” and all its messages?`))return;try{await api('delete_chat',chat.id);chats=chats.filter(row=>row.id!==chat.id);if(activeChat===chat.id){if(chats.length)await selectChat(chats[0].id);else await createChat()}else renderChats()}catch(error){notice(error.message)}}
  async function submit(text){
    text=text.trim();if(!text||busy)return;
    if(!activeChat){await createChat();if(!activeChat)return}
    setBusy(true);state('PROCESSING','Thinking...');
    try{const result=await api('send_message',text,activeChat);if(!result.accepted)throw new Error(result.message);$('messageInput').value='';$('messageInput').style.height='';$('messageInput').focus()}
    catch(error){setBusy(false);state('IDLE','Ready');notice(error.message)}
  }
  async function toggleMic(){
    try{
      if(listening){await api('stop_listening');return}
      if(!activeChat)await createChat();
      listening=true;state('LISTENING','Listening...');
      const result=await api('start_listening',activeChat);if(!result.accepted)throw new Error(result.message);
    }catch(error){listening=false;state('IDLE','Ready');notice(error.message)}
  }
  function onEvent(event,data){
    if(event==='state'){state(data.state,data.label);return}
    if(event==='message'){renderMessage(data);return}
    if(event==='history_updated'){chats=data.chats;renderChats();$('currentTitle').textContent=chats.find(c=>c.id===activeChat)?.title||'New chat';return}
    if(event==='listening_started'){listening=true;state('LISTENING','Listening...');return}
    if(event==='listening_stopped'){listening=false;return}
    if(event==='recognized'){notice(`Heard: ${data.text}`);return}
    if(event==='wake_detected'){notice('Hey Zara detected');return}
    if(event==='whatsapp_confirmation'){pendingToken=data.token;$('confirmTo').textContent=data.to;$('confirmMessage').textContent=data.message;$('confirmModal').hidden=false;setBusy(false);$('sendConfirmBtn').focus();return}
    if(event==='ai_test'){updateAiStatus(data.success?'connected':'offline');$('aiFeedback').textContent=data.message;$('aiFeedback').dataset.status=data.success?'connected':'offline';return}
    if(event==='ai_status'){updateAiStatus(data.status);$('aiFeedback').textContent=data.status==='connected'?'● Connected':'○ Offline';$('aiFeedback').dataset.status=data.status;return}
    if(event==='wake_status'){const labels={active:'● Hey Zara active',starting:'◌ Wake word starting',paused:'○ Wake word paused',detected:'● Hey Zara detected',error:'! Wake word unavailable',off:'○ Wake word off'};$('wakeIndicator').textContent=labels[data.status]||labels.off;$('wakeIndicator').dataset.status=data.status;if(data.message&&data.status==='error')notice(data.message);return}
    if(event==='error'||event==='status'){if(event==='error')window.zaraWave?.setState('ERROR');notice(data.message);setBusy(false);return}
    if(event==='command_failed'){window.zaraWave?.setState('ERROR');notice(data.message);setBusy(false)}
  }
  window.backend_event=onEvent;
  if(window.eel)eel.expose(window.backend_event,'backend_event');

  function openSettings(){settingsOpener=document.activeElement;setDrawer(false,false);fillSettings();$('settingsModal').hidden=false;shell.inert=true;$('closeSettingsBtn').focus()}
  function closeSettings(){if($('settingsModal').hidden)return;$('settingsModal').hidden=true;shell.inert=false;if(shell.classList.contains('drawer-open')){$('newChatBtn').focus();return}if(settingsOpener===$('settingsBtn'))$('mobileSettingsBtn').focus();else (settingsOpener||$('mobileSettingsBtn')).focus()}
  function fillSettings(){
    $('themeSelect').value=settings.theme;$('launchBehavior').value=settings.launch_behavior;$('sidebarSetting').checked=settings.sidebar_collapsed;
    $('voiceEnabled').checked=settings.voice_enabled;$('speechRate').value=settings.speech_rate;$('speechVolume').value=settings.speech_volume;
    $('voiceSelect').replaceChildren(new Option('System default',''));for(const voice of voices)$('voiceSelect').add(new Option(voice.name,voice.id));$('voiceSelect').value=settings.selected_voice;
    $('aiEnabled').checked=settings.ai_enabled;$('aiEndpoint').value=settings.ai_endpoint;$('aiModel').value=settings.ai_model;$('aiTemperature').value=settings.ai_temperature;$('aiContext').value=settings.ai_max_context;$('aiTimeout').value=settings.ai_timeout;$('aiSystemPrompt').value=settings.ai_system_prompt;$('speakAiResponses').checked=settings.speak_ai_responses;$('aiSpeechMaxChars').value=settings.ai_speech_max_chars;
    $('wakeEnabled').checked=settings.wake_word_enabled;$('wakeProvider').value=settings.wake_word_provider;$('wakeModelPath').value=settings.wake_word_model_path;$('wakeSensitivity').value=settings.wake_word_sensitivity;$('activationSound').checked=settings.activation_sound;$('activationResponse').value=settings.activation_response;
    updateRangeLabels();
  }
  function updateRangeLabels(){$('rateValue').textContent=$('speechRate').value+' words/min';$('volumeValue').textContent=Math.round($('speechVolume').value*100)+'%';$('temperatureValue').textContent=$('aiTemperature').value;$('contextValue').textContent=$('aiContext').value;$('wakeSensitivityValue').textContent=$('wakeSensitivity').value}
  async function saveSettings(){
    const values={theme:$('themeSelect').value,launch_behavior:$('launchBehavior').value,sidebar_collapsed:$('sidebarSetting').checked,voice_enabled:$('voiceEnabled').checked,
      selected_voice:$('voiceSelect').value,speech_rate:Number($('speechRate').value),speech_volume:Number($('speechVolume').value),
      ai_enabled:$('aiEnabled').checked,ai_endpoint:$('aiEndpoint').value.trim(),ai_model:$('aiModel').value.trim(),
      ai_temperature:Number($('aiTemperature').value),ai_max_context:Number($('aiContext').value),ai_timeout:Number($('aiTimeout').value),ai_system_prompt:$('aiSystemPrompt').value,speak_ai_responses:$('speakAiResponses').checked,ai_speech_max_chars:Number($('aiSpeechMaxChars').value),wake_word_enabled:$('wakeEnabled').checked,wake_word_provider:$('wakeProvider').value,wake_word_model_path:$('wakeModelPath').value.trim(),wake_word_sensitivity:Number($('wakeSensitivity').value),activation_sound:$('activationSound').checked,activation_response:$('activationResponse').value};
    try{settings=await api('update_settings',values);document.documentElement.dataset.theme=settings.theme;setDrawer(!settings.sidebar_collapsed,false);shell.inert=true;$('saveSettingsBtn').focus();updateAiStatus(settings.ai_enabled?'unknown':'disabled');$('aiFeedback').textContent='○ Not tested';$('aiFeedback').dataset.status='unknown';$('settingsFeedback').textContent='Saved';setTimeout(()=>$('settingsFeedback').textContent='',2500);return true}catch(error){$('settingsFeedback').textContent=error.message;return false}
  }
  function registryItem(item,kind){
    const row=document.createElement('div');row.className='registry-item'+(!item.enabled?' disabled':'');
    const label=document.createElement('span');label.textContent=item.name;const sub=document.createElement('small');sub.textContent=item.builtin?'Built in':item.aliases||'Custom';label.append(sub);row.append(label);
    if(!item.builtin){const edit=document.createElement('button');edit.textContent='Edit';edit.onclick=()=>fillMapping(kind,item);const remove=document.createElement('button');remove.textContent='Delete';remove.onclick=()=>removeMapping(kind,item);row.append(edit,remove)}
    return row;
  }
  async function loadRegistry(kind){try{const rows=await api('get_registry',kind);const list=$(kind+'List');list.replaceChildren(...rows.map(row=>registryItem(row,kind)))}catch(error){notice(error.message)}}
  function fillMapping(kind,item){const prefix=kind==='applications'?'application':'website';$(prefix+'Id').value=item.id;$(prefix+'Name').value=item.name;$(prefix+'Aliases').value=item.aliases;$(prefix+'Enabled').checked=!!item.enabled;$(prefix+(kind==='applications'?'Path':'Url')).value=item.path||item.url;$(prefix+'FormTitle').textContent='Edit '+item.name}
  function resetMapping(kind){const prefix=kind==='applications'?'application':'website';$(prefix+'Form').reset();$(prefix+'Id').value='';$(prefix+'FormTitle').textContent='Add '+prefix}
  async function saveMapping(event,kind){event.preventDefault();const prefix=kind==='applications'?'application':'website';const data={id:$(prefix+'Id').value||null,name:$(prefix+'Name').value,aliases:$(prefix+'Aliases').value,enabled:$(prefix+'Enabled').checked};data[kind==='applications'?'path':'url']=$(prefix+(kind==='applications'?'Path':'Url')).value;try{await api('save_mapping',kind,data);resetMapping(kind);await loadRegistry(kind);notice('Mapping saved')}catch(error){notice(error.message)}}
  async function removeMapping(kind,item){if(!confirm(`Delete ${item.name}?`))return;try{await api('delete_mapping',kind,item.id);await loadRegistry(kind);notice('Mapping deleted')}catch(error){notice(error.message)}}
  async function loadContacts(){try{const rows=await api('get_contacts');const list=$('contactsList');list.replaceChildren();for(const item of rows){const row=document.createElement('div');row.className='registry-item';const label=document.createElement('span');label.textContent=item.name;const remove=document.createElement('button');remove.textContent='Delete';remove.onclick=async()=>{if(!confirm(`Delete contact ${item.name}?`))return;try{await api('delete_contact',item.id);await loadContacts()}catch(error){notice(error.message)}};row.append(label,remove);list.append(row)}}catch(error){notice(error.message)}}
  async function saveContact(event){event.preventDefault();try{await api('save_contact',$('contactName').value,$('contactPhone').value,$('contactAliases').value);$('contactForm').reset();await loadContacts();notice('Contact saved')}catch(error){notice(error.message)}}
  async function confirmWhatsApp(approved){const token=pendingToken;if(!token)return;pendingToken=null;$('confirmModal').hidden=true;try{const response=await api('confirm_whatsapp',token,approved);if(!response.accepted)throw new Error(response.message);if(approved){setBusy(true);state('EXECUTING','Sending message...')}else state('IDLE','Ready')}catch(error){if(approved){pendingToken=token;$('confirmModal').hidden=false}notice(error.message)}}
  async function bootstrap(){try{const data=await api('bootstrap');chats=data.chats;settings=data.settings;voices=data.voices;document.documentElement.dataset.theme=settings.theme;updateAiStatus(settings.ai_enabled?'unknown':'disabled');if(!chats.length||(settings.launch_behavior==='new_chat'&&!sessionStorage.getItem('zaraLaunched')))await createChat();else await selectChat(chats[0].id);sessionStorage.setItem('zaraLaunched','1');renderChats();fillSettings();if($('welcome').hidden&&!settings.sidebar_collapsed)setDrawer(true)}catch(error){notice(error.message);$('topStatus').textContent='Disconnected';$('heroStatus').textContent='Assistant disconnected';updateAiStatus('offline')}}

  $('composer').onsubmit=event=>{event.preventDefault();submit($('messageInput').value)};
  $('messageInput').onkeydown=event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();submit($('messageInput').value)}};
  $('messageInput').oninput=()=>{const input=$('messageInput');input.style.height='auto';input.style.height=Math.min(input.scrollHeight,140)+'px'};
  $('micBtn').onclick=toggleMic;$('newChatBtn').onclick=createChat;
  $('collapseBtn').onclick=()=>setDrawer(false);
  $('menuBtn').onclick=()=>setDrawer(!shell.classList.contains('drawer-open'));
  $('drawerBackdrop').onclick=()=>setDrawer(false);
  $('settingsBtn').onclick=openSettings;$('mobileSettingsBtn').onclick=openSettings;$('closeSettingsBtn').onclick=closeSettings;$('saveSettingsBtn').onclick=saveSettings;
  $('settingsModal').onclick=event=>{if(event.target===$('settingsModal'))closeSettings()};
  $('settingsNav').onclick=event=>{const tab=event.target.closest('button[data-section]');if(!tab)return;document.querySelectorAll('.settings-nav button,.settings-section').forEach(node=>node.classList.toggle('active',node.dataset.section===tab.dataset.section));if(tab.dataset.section==='applications')loadRegistry('applications');if(tab.dataset.section==='websites')loadRegistry('websites');if(tab.dataset.section==='contacts')loadContacts()};
  for(const id of ['speechRate','speechVolume','aiTemperature','aiContext','wakeSensitivity'])$(id).oninput=updateRangeLabels;
  $('testVoiceBtn').onclick=async()=>{if(!await saveSettings())return;try{await api('test_voice')}catch(error){notice(error.message)}};
  $('testAiBtn').onclick=async()=>{if(!await saveSettings())return;try{$('aiFeedback').textContent='Testing...';await api('test_ai_connection')}catch(error){$('aiFeedback').textContent=error.message}};
  $('applicationForm').onsubmit=event=>saveMapping(event,'applications');$('websiteForm').onsubmit=event=>saveMapping(event,'websites');$('contactForm').onsubmit=saveContact;
  $('resetApplication').onclick=()=>resetMapping('applications');$('resetWebsite').onclick=()=>resetMapping('websites');
  $('cancelConfirmBtn').onclick=()=>confirmWhatsApp(false);$('sendConfirmBtn').onclick=()=>confirmWhatsApp(true);
  document.onkeydown=event=>{
    if(event.key==='Escape'){
      if(!$('confirmModal').hidden)confirmWhatsApp(false);
      else if(!$('settingsModal').hidden)closeSettings();
      else setDrawer(false);
      return;
    }
    const dialog=!$('confirmModal').hidden ? $('confirmModal') : !$('settingsModal').hidden ? $('settingsModal') : shell.classList.contains('drawer-open') ? $('sidebar') : null;
    if(event.key==='Tab'&&dialog){
      const items=[...dialog.querySelectorAll('button,input,select,textarea,[tabindex="0"]')].filter(node=>!node.disabled&&node.getClientRects().length);
      const first=items[0],last=items[items.length-1];
      if(event.shiftKey&&(document.activeElement===first||!dialog.contains(document.activeElement))){event.preventDefault();last?.focus()}
      else if(!event.shiftKey&&(document.activeElement===last||!dialog.contains(document.activeElement))){event.preventDefault();first?.focus()}
    }
    if(event.ctrlKey&&event.key.toLowerCase()==='n'&&$('settingsModal').hidden&&$('confirmModal').hidden){event.preventDefault();createChat()}
  };
  bootstrap();
})();
