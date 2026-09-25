// Test-only Eel boundary. Loaded by ui-smoke.html, never by the production page.
(() => {
  const settings = {theme:'dark',launch_behavior:'last_chat',sidebar_collapsed:true,voice_enabled:true,speech_rate:174,speech_volume:1,selected_voice:'',ai_enabled:true,ai_endpoint:'http://127.0.0.1:8080/v1',ai_model:'',ai_temperature:.7,ai_max_context:12,ai_timeout:35,ai_system_prompt:'',speak_ai_responses:true,ai_speech_max_chars:500,wake_word_enabled:false,wake_word_provider:'openwakeword',wake_word_model_path:'',wake_word_sensitivity:.5,activation_sound:false,activation_response:'none'};
  let chats=[{id:1,title:'Saved conversation',updated_at:'2026-09-25 08:00:00'}], next=1;
  const history={1:[]}, calls=[], errors=[];
  const emit=(event,data)=>window.backend_event(event,data);
  window.addEventListener('error',event=>errors.push(event.message));
  window.addEventListener('unhandledrejection',event=>errors.push(String(event.reason)));
  window.prompt=()=> 'Renamed verification chat';window.confirm=()=>true;
  const handlers={
    bootstrap:()=>({settings,chats:[...chats],voices:[]}),
    get_chat_history:id=>history[id],set_active_chat:()=>true,
    create_chat:()=>{const chat={id:++next,title:'New chat',updated_at:'2026-09-25 09:00:00'};chats.unshift(chat);history[chat.id]=[];return chat},
    rename_chat:(id,title)=>{const chat=chats.find(c=>c.id===id);chat.title=title;return chat},
    delete_chat:id=>{chats=chats.filter(c=>c.id!==id);delete history[id];return true},
    update_settings:values=>Object.assign(settings,values),
    get_registry:()=>[{id:1,name:'Fixture app',enabled:true,builtin:true}],get_contacts:()=>[],
    save_mapping:()=>true,delete_mapping:()=>true,save_contact:()=>true,delete_contact:()=>true,
    start_listening:()=>{emit('listening_started',{});return {accepted:true}},
    stop_listening:()=>{emit('listening_stopped',{});emit('state',{state:'IDLE',label:'Ready'});return true},
    test_voice:()=>{emit('state',{state:'SPEAKING',label:'Speaking...'});return true},
    test_ai_connection:()=>{emit('ai_test',{success:true,message:'Connected'});return true},
    confirm_whatsapp:()=>({accepted:true}),
    send_message:(text,id)=>{
      setTimeout(()=>{
        const messages=[{session_id:id,role:'user',content:text},{session_id:id,role:'assistant',content:'Fixture response: '+text}];
        history[id].push(...messages);messages.forEach(m=>emit('message',m));emit('state',{state:'IDLE',label:'Ready'});
      },10);
      return {accepted:true};
    }
  };
  window.fixture={calls,errors,settings};
  window.eel={expose(){}};
  for(const [name,handler] of Object.entries(handlers))window.eel[name]=(...args)=>async()=>{calls.push({name,args});return {ok:true,data:handler(...args)}};
})();
