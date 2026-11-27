const $ = id => document.getElementById(id);
const state = { user:null, chats:[], chat:null, cid:null, tab:'all', query:'', messages:[], context:null, media:null, recording:null, socket:null, epoch:0 };
const kinds = { text:'Сообщение', voice:'Голосовое', circle:'Видеокружок', photo:'Фото', video:'Видео', file:'Файл', poll:'Опрос' };
const rights = { send_text:'Писать сообщения', send_media:'Отправлять медиа', send_poll:'Создавать опросы', invite:'Приглашать', pin:'Закреплять', manage:'Управлять группой', delete_others:'Удалять чужие сообщения' };
const roles = { owner:'Владелец', admin:'Администратор', member:'Участник' };
const emoji = ['👍','❤️','🔥','😂','🎉','👀'];
const clock = new Intl.DateTimeFormat('ru', {hour:'2-digit', minute:'2-digit'});
const date = new Intl.DateTimeFormat('ru', {day:'numeric', month:'long', year:'numeric'});
const desc = msg => msg?.body?.text || msg?.body?.question || (msg?.kind === 'file' && msg.body.name) || kinds[msg?.kind] || 'Пока нет сообщений';
const base = () => '/chats/' + state.cid;
const node = (tag, className, text) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text != null) element.textContent = text;
  return element;
};
const button = (label, handler, css='secondary') => {
  const element = node('button', css, label);
  element.type = 'button';
  element.onclick = () => run(handler);
  return element;
};
function avatar(element, label) {
  element.textContent = label.trim().split(/\s+/).slice(0,2).map(part => Array.from(part)[0]).join('').toUpperCase();
  element.style.setProperty('--hue', [...label].reduce((sum, char) => (sum * 31 + char.codePointAt(0)) % 360, 47));
}
let toastTimer;
function toast(text) {
  $('toast').textContent = text;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $('toast').hidden = true, 4000);
}
async function run(handler) {
  try { return await handler(); } catch (error) { toast(error.message); }
}
async function api(path, data) {
  const request = data === undefined ? {} : data instanceof FormData
    ? {method:'POST', body:data}
    : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)};
  const response = await fetch('/api' + path, request);
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    const error = new Error(typeof problem.detail === 'string' ? problem.detail :
      (problem.detail?.[0]?.msg || 'Ошибка запроса. Попробуйте ещё раз.'));
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? undefined : response.json();
}
function modal(title, ...items) {
  $('dialog-title').textContent = title;
  $('dialog-content').replaceChildren(...items);
  if (!$('modal').open) $('modal').showModal();
}
const close = () => $('modal').close();
$('close-dialog').onclick = close;
let register = false;
$('auth-switch').onclick = () => {
  register = !register;
  $('name-label').hidden = !register;
  $('auth').elements.name.required = register;
  $('auth-title').textContent = register ? 'Создать аккаунт' : 'Вход в Контур';
  $('auth-submit').textContent = register ? 'Зарегистрироваться' : 'Войти';
  $('auth-switch').textContent = register ? 'У меня есть аккаунт' : 'Создать аккаунт';
  $('auth').elements.password.autocomplete = register ? 'new-password' : 'current-password';
};
$('auth').onsubmit = event => {
  event.preventDefault();
  run(async () => {
    $('auth-submit').disabled = true;
    try {
      const data = Object.fromEntries(new FormData(event.currentTarget || $('auth')));
      if (!register) delete data.name;
      await enter(await api('/account/' + (register ? 'register' : 'login'), data));
      $('auth').reset();
    } finally { $('auth-submit').disabled = false; }
  });
};
async function enter(user) {
  state.user = user;
  $('login').hidden = true;
  $('app').hidden = false;
  $('profile-name').textContent = user.name;
  $('profile-handle').textContent = '@' + user.username;
  avatar($('profile-avatar'), user.name);
  await refresh();
  connect();
  run(inviteFromUrl);
}
function signedOut() {
  state.user = null;
  state.socket?.close();
  showList();
  $('login').hidden = false;
  $('app').hidden = true;
  state.chats = [];
}
$('logout').onclick = () => run(async () => { await api('/logout', {}); signedOut(); });
function connect() {
  if (!state.user) return;
  const socket = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/api/live');
  state.socket = socket;
  socket.onopen = schedule;
  socket.onmessage = schedule;
  socket.onclose = () => {
    if (state.user && state.socket === socket) setTimeout(() => {
      if (state.user && state.socket === socket) connect();
    }, 2200);
  };
}
let scheduled, refreshing = false, again = false;
function schedule() {
  clearTimeout(scheduled);
  scheduled = setTimeout(() => run(refresh), 180);
}
setInterval(() => { if (state.user && !document.hidden) schedule(); }, 7000);
document.addEventListener('visibilitychange', () => { if (state.user && !document.hidden) schedule(); });
async function refresh() {
  if (!state.user) return;
  if (refreshing) { again = true; return; }
  const started = state.user;
  refreshing = true;
  try {
    const chats = await api('/chats');
    if (started !== state.user) return;
    state.chats = chats;
    renderList();
    if (state.cid) {
      if (!chats.some(chat => chat.id === state.cid)) showList();
      else await loadThread(false);
    }
  } catch (error) {
    if (error.status === 401) signedOut();
    else throw error;
  } finally {
    refreshing = false;
    if (again) { again = false; schedule(); }
  }
}
function renderList() {
  const query = $('filter').value.toLowerCase().trim();
  const chats = state.chats.filter(chat => chat.title.toLowerCase().includes(query) &&
    (state.tab === 'all' || state.tab === (chat.direct ? 'direct' : chat.channel ? 'channel' : 'group')));
  $('chat-list').replaceChildren(...chats.map(chat => {
    const row = button('', () => selectChat(chat.id), 'chat-row' + (state.cid === chat.id ? ' selected' : ''));
    const icon = node('span', 'avatar'); avatar(icon, chat.title);
    const copy = node('span'); copy.append(node('strong','',chat.title),node('small','',desc(chat)));
    row.append(icon, copy);
    if (chat.unread) row.append(node('span','unread', String(chat.unread)));
    return row;
  }));
  if (!chats.length) $('chat-list').append(node('p','list-empty',query ? 'Чаты не найдены' : 'Здесь появятся ваши чаты'));
}
$('filter').oninput = renderList;
document.querySelectorAll('[data-tab]').forEach(tab => tab.onclick = () => {
  state.tab = tab.dataset.tab;
  document.querySelectorAll('[data-tab]').forEach(item => item.classList.toggle('active',item === tab));
  renderList();
});
function resetThread() {
  state.epoch++;
  state.chat = null;
  state.query = '';
  state.messages = [];
  state.signature = '';
  $('draft').value = '';
  $('find').hidden = true;
  $('query').value = '';
  $('messages').replaceChildren();
  $('pinned').hidden = true;
  $('older').hidden = true;
  clearContext();
  stopRecording(true);
  clearMedia();
}
function showList() {
  state.cid = null;
  resetThread();
  $('app').classList.remove('open');
  $('thread').hidden = true;
  $('welcome').hidden = false;
  renderList();
}
$('back').onclick = showList;
async function selectChat(cid) {
  if (state.cid === cid) return;
  resetThread();
  state.cid = cid;
  await loadThread(true);
  renderList();
}
async function loadThread(reset, before) {
  const epoch = state.epoch;
  const query = state.query;
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (before) params.set('before',before);
  let result;
  try { result = await api(base() + '?' + params); }
  catch (error) {
    if (error.status === 404 && epoch === state.epoch) { showList(); return; }
    throw error;
  }
  if (epoch !== state.epoch || query !== state.query) return;
  const history = $('history');
  const near = history.scrollHeight - history.scrollTop - history.clientHeight < 110;
  const height = history.scrollHeight;
  const oldScroll = history.scrollTop;
  if (reset) {
    state.more = result.more;
    state.messages = result.messages;
  } else if (before) {
    const ids = new Set(state.messages.map(msg => msg.seq));
    state.messages = [...result.messages.filter(msg => !ids.has(msg.seq)), ...state.messages];
    state.more = result.more;
  } else {
    // Keep opened history in sync with deletions and permission changes.
    if (state.messages.length > 50) {
      const oldest = state.messages[0].seq;
      const all = [...result.messages];
      let page = result;
      while (page.more && all.length && all[0].seq > oldest) {
        const olderParams = new URLSearchParams(params);
        olderParams.set('before',all[0].seq);
        page = await api(base() + '?' + olderParams);
        if (epoch !== state.epoch || query !== state.query) return;
        if (!page.messages.length) break;
        all.unshift(...page.messages);
      }
      state.messages = all.filter(msg => msg.seq >= oldest);
      state.more = page.more || all.some(msg => msg.seq < oldest);
    } else {
      state.messages = result.messages;
      state.more = result.more;
    }
  }
  state.chat = result;
  const signature = JSON.stringify([result.title,result.members,result.permissions,result.pinned,state.messages,state.more,state.query]);
  if (state.signature !== signature) {
    state.signature = signature;
    renderThread();
    if (before) history.scrollTop = oldScroll + history.scrollHeight - height;
    else if (query && reset) history.scrollTop = 0;
    else if (reset || near) history.scrollTop = history.scrollHeight;
    else history.scrollTop = oldScroll;
  }
  if (!query && !document.hidden && (reset || near) && state.messages.length) {
    const seq = state.messages.at(-1).seq;
    const seen = result.members.find(member => member.id === state.user.id)?.seen || 0;
    if (seq > seen) await api(base() + '/read',{seq});
  }
}
function jump(seq) {
  const message = $('m-' + seq);
  if (message) { message.scrollIntoView({block:'center', behavior:'smooth'}); message.animate([{opacity:.4},{opacity:1}], 550); }
  else toast('Загрузите более ранние сообщения, чтобы перейти к записи');
}
function renderThread() {
  const chat = state.chat;
  $('app').classList.add('open');
  $('thread').hidden = false;
  $('welcome').hidden = true;
  $('title').textContent = chat.title;
  const peer = chat.members.find(person => person.id !== state.user.id);
  $('subtitle').textContent = chat.saved ? 'Ваши заметки и файлы' : chat.direct ? '@' + (peer?.username || '') : (chat.channel ? 'Канал' : 'Группа') + ' · ' + chat.members.length + ' · ' + roles[chat.role];
  avatar($('thread-avatar'),chat.title);
  $('pinned').hidden = !chat.pinned.length;
  $('pinned').replaceChildren(...chat.pinned.map(msg => button('⌖ ' + desc(msg), () => jump(msg.seq),'plain')));
  $('older').hidden = !state.more;
  $('voice').disabled = $('circle').disabled = $('attach').disabled = !chat.permissions.send_media;
  $('poll').disabled = !chat.permissions.send_poll;
  $('draft').disabled = $('send').disabled = !chat.permissions.send_text;
  $('draft').placeholder = chat.permissions.send_text ? 'Написать сообщение…' : 'Отправка текста ограничена';
  const output = $('messages');
  const elements = [];
  let previous;
  for (const msg of state.messages) {
    const day = date.format(new Date(msg.created));
    if (day !== previous) elements.push(node('div','date',day));
    previous = day;
    const old = $('m-' + msg.seq);
    const read = chat.direct && peer?.seen >= msg.seq;
    const signature = JSON.stringify([msg,chat.direct,read,desc(state.messages.find(item => item.seq === msg.reply))]);
    if (old?.dataset.signature === signature) elements.push(old);
    else {
      const fresh = messageView(msg,read);
      fresh.dataset.signature = signature;
      elements.push(fresh);
    }
  }
  if (!elements.length) elements.push(node('div','date',state.query ? 'Ничего не найдено' : 'История пуста'));
  // Preserve DOM nodes for media playback when only other messages change.
  let current = output.firstChild;
  for (const item of elements) {
    if (current === item) current = current.nextSibling;
    else output.insertBefore(item,current);
  }
  while (current) {
    const next = current.nextSibling;
    current.remove();
    current = next;
  }
}
function messageView(msg, read) {
  const mine = msg.author === state.user.id;
  const block = node('article','message' + (mine ? ' own' : ''));
  block.id = 'm-' + msg.seq;
  if (!mine && !state.chat.direct) block.append(node('strong','sender',msg.name));
  if (msg.body.forwarded) block.append(node('small','sender','Пересланное сообщение'));
  if (msg.reply) {
    const original = state.messages.find(item => item.seq === msg.reply);
    block.append(button('↳ ' + (original ? desc(original).slice(0,100) : 'Ответ на сообщение № ' + msg.reply),
      () => jump(msg.reply),'quote'));
  }
  const bytes = '/api' + base() + '/media/' + msg.seq;
  if (msg.kind === 'poll') {
    block.append(node('strong','',msg.body.question));
    const options = node('div','poll-options');
    msg.body.options.forEach((option,i) => {
      const selected = (msg.my_vote || []).includes(i);
      const count = msg.votes.filter(vote => vote.includes(i)).length;
      const vote = button('', () => {
        const current = state.messages.find(item => item.seq === msg.seq)?.my_vote || [];
        const choices = current.includes(i) ? current.filter(index => index !== i) :
          msg.body.multiple ? [...current,i] : [i];
        return messageAction(msg,'vote',{options:choices});
      }, selected ? 'chosen' : '');
      vote.append(node('span','',option),node('small','',String(count)));
      vote.disabled = msg.body.closed;
      options.append(vote);
    });
    block.append(options,node('small','',msg.body.closed ? 'Опрос завершён' : msg.body.multiple ? 'Несколько ответов' : 'Один ответ'));
  } else {
    if (msg.kind === 'photo') {
      const image = node('img'); image.src = bytes; image.alt = msg.body.name; image.loading = 'lazy';
      block.append(image);
    } else if (['voice','video','circle'].includes(msg.kind)) {
      const media = node(msg.kind === 'voice' ? 'audio' : 'video',msg.kind);
      media.src = bytes;
      media.controls = true;
      media.preload = 'metadata';
      media.playsInline = true;
      block.append(media);
    } else if (msg.kind === 'file') {
      const link = node('a','',msg.body.name);
      link.href = bytes; link.download = msg.body.name;
      block.append(link,node('small','',' · ' + (msg.body.bytes / 1024).toFixed(1) + ' КБ'));
    }
    if (msg.body.text) block.append(node('p','',msg.body.text));
  }
  if (Object.keys(msg.reactions).length) {
    const reactions = node('div');
    for (const [reaction,count] of Object.entries(msg.reactions)) reactions.append(button(reaction + ' ' + count,
      () => messageAction(msg,'react',{text:reaction}),'reaction'));
    block.append(reactions);
  }
  const meta = node('div','meta');
  const menu = button('⋯',() => messageMenu(msg),'');
  menu.setAttribute('aria-label','Действия с сообщением');
  meta.append(node('span','',(msg.pinned ? '⌖ ' : '') + (msg.edited && msg.kind !== 'poll' ? 'изм. ' : '') +
    clock.format(new Date(msg.created)) + (mine ? (read ? ' ✓✓' : ' ✓') : '')),menu);
  block.append(meta);
  return block;
}
async function messageAction(msg,action,data={}) {
  const cid = state.cid;
  await api(base() + '/messages/' + msg.seq + '/' + action,data);
  if (state.cid === cid) await loadThread(false);
  schedule();
}
async function chatAction(action,data={}) {
  return api(base() + '/' + action,data);
}
function messageMenu(msg) {
  const chat = state.chat;
  const mine = msg.author === state.user.id;
  const actions = node('div','dialog-actions');
  actions.append(button('Ответить',() => { setContext('reply',msg); close(); }));
  actions.append(button('Переслать',() => forwardDialog(msg)));
  if (mine && msg.kind !== 'poll' && chat.permissions.send_text) actions.append(button('Редактировать',() => { setContext('edit',msg); close(); }));
  if (chat.direct || chat.permissions.pin) actions.append(button(msg.pinned ? 'Открепить' : 'Закрепить',
    async () => { await messageAction(msg,'pin',{flag:!msg.pinned}); close(); }));
  if (mine && msg.kind === 'poll' && !msg.body.closed) actions.append(button('Завершить опрос',
    async () => { await messageAction(msg,'close'); close(); }));
  actions.append(button('Удалить у себя',() => confirmAction('Удалить сообщение у себя?',() => messageAction(msg,'hide')),'plain danger'));
  if (mine || chat.direct || chat.permissions.delete_others) actions.append(button('Удалить у всех',
    () => confirmAction('Удалить сообщение у всех?',() => messageAction(msg,'delete')),'plain danger'));
  const reactions = node('div','dialog-actions');
  for (const reaction of emoji) reactions.append(button(reaction,async () => { await messageAction(msg,'react',{text:reaction}); close(); }));
  reactions.append(button('Снять реакцию',async () => { await messageAction(msg,'react',{text:''}); close(); },'plain'));
  modal('Сообщение',actions,reactions);
}
function forwardDialog(msg) {
  const source = state.cid;
  const id = requestId();
  const send = async cid => {
    await api('/chats/' + cid + '/forward',{source,seq:msg.seq,request_id:id});
    close();
    toast('Сообщение переслано');
    await refresh();
  };
  modal('Куда переслать?',
    button('В избранное',async () => send((await api('/saved',{})).id),'primary'),
    ...state.chats.filter(chat => !chat.saved).map(chat =>
      button(chat.title,() => send(chat.id),'secondary person')));
}
function confirmAction(title,action) {
  modal(title,button('Удалить',async () => { await action(); close(); },'secondary danger'),button('Отмена',close,'plain'));
}
function setContext(mode,msg) {
  state.context = {mode,msg};
  $('context').hidden = false;
  $('context-text').textContent = (mode === 'edit' ? 'Редактирование · ' : 'Ответ · ') + desc(msg).slice(0,100);
  if (mode === 'edit') $('draft').value = msg.body.text || '';
  setTimeout(() => $('draft').focus(),0);
}
function clearContext() {
  if (state.context?.mode === 'edit') $('draft').value = '';
  state.context = null;
  $('context').hidden = true;
}
$('cancel-context').onclick = clearContext;
$('message-search').onclick = () => { $('find').hidden = false; $('query').focus(); };
$('find').onsubmit = event => {
  event.preventDefault();
  state.query = $('query').value.trim();
  run(() => loadThread(true));
};
$('close-search').onclick = () => {
  $('find').hidden = true;
  $('query').value = '';
  state.query = '';
  run(() => loadThread(true));
};
$('older').onclick = () => run(async () => {
  $('older').disabled = true;
  try { await loadThread(false,state.messages[0]?.seq); } finally { $('older').disabled = false; }
});
$('history').addEventListener('scroll',() => {
  const history = $('history');
  const last = state.messages.at(-1)?.seq;
  if (!state.query && last && state.chat && history.scrollHeight-history.scrollTop-history.clientHeight < 40) {
    const current = state.chat.members.find(member => member.id === state.user?.id);
    if (current && current.seen < last && !current.pending) {
      current.pending = true;
      run(async () => {
        try { await chatAction('read',{seq:last}); current.seen = last; }
        finally { current.pending = false; }
      });
    }
  }
});
let pendingText;
const requestId = () => crypto.randomUUID();
async function postMessage(payload) {
  const cid = state.cid;
  await api(base() + '/messages',payload);
  if (cid === state.cid) {
    clearContext();
    if (state.query) {
      state.query = '';
      $('find').hidden = true;
    }
    await loadThread(true);
  }
  schedule();
}
$('compose').onsubmit = event => {
  event.preventDefault();
  run(async () => {
    const text = $('draft').value.trim();
    const context = state.context;
    if ((!text && !(context?.mode === 'edit' && context.msg.kind !== 'text')) || $('send').disabled) return;
    const cid = state.cid;
    $('send').disabled = true;
    try {
      if (context?.mode === 'edit') await messageAction(context.msg,'edit',{text});
      else {
        const key = JSON.stringify([cid,text,context?.msg.seq]);
        if (pendingText?.key !== key) pendingText = {key,id:requestId()};
        await postMessage({request_id:pendingText.id,kind:'text',text,reply:context?.msg.seq});
        pendingText = null;
      }
      if (cid === state.cid) { $('draft').value = ''; clearContext(); }
    } finally { $('send').disabled = !state.chat?.permissions.send_text; }
  });
};
$('draft').onkeydown = event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $('compose').requestSubmit();
  }
};
$('poll').onclick = () => {
  const question = node('input'); question.placeholder = 'Вопрос'; question.maxLength = 300;
  const choices = node('div','stack');
  function add() {
    if (choices.children.length === 10) return;
    const option = node('input'); option.placeholder = 'Вариант ' + (choices.children.length + 1); option.maxLength = 100;
    choices.append(option);
    return option;
  }
  add(); add();
  const multiple = node('input'); multiple.type = 'checkbox';
  const toggle = node('label','row','Несколько ответов'); toggle.prepend(multiple);
  const id = requestId();
  modal('Новый опрос',question,choices,button('Добавить вариант',() => add()?.focus(),'plain'),toggle,
    button('Опубликовать',async () => {
      const options = [...choices.children].map(input => input.value.trim()).filter(Boolean);
      await postMessage({request_id:id,kind:'poll',question:question.value,options,multiple:multiple.checked,
        reply: state.context?.mode === 'reply' ? state.context.msg.seq : null});
      close();
    },'primary'));
};
function filePreview(file,kind,duration=null) {
  clearMedia();
  const url = URL.createObjectURL(file);
  state.media = {file,kind,duration,url,id:requestId()};
  const content = $('preview-media');
  if (['voice','circle','video'].includes(kind)) {
    const player = node(kind === 'voice' ? 'audio' : 'video',kind);
    player.src = url; player.controls = true; player.playsInline = true;
    content.append(player);
  } else content.append(node('span','',file.name));
  $('preview').hidden = false;
}
function clearMedia() {
  if (state.media) URL.revokeObjectURL(state.media.url);
  state.media = null;
  $('preview').hidden = true;
  $('preview-media').replaceChildren();
}
$('attach').onclick = () => $('file').click();
$('file').onchange = () => {
  const input = $('file');
  const file = input.files[0];
  input.value = '';
  if (!file) return;
  if (file.size > 25 * 1024 * 1024) { toast('Максимальный размер вложения 25 МБ'); return; }
  let kind = 'file';
  if (/^image\/(jpeg|png|gif|webp|avif)$/.test(file.type)) kind = 'photo';
  else if (/^video\/(webm|mp4|quicktime|ogg)$/.test(file.type)) kind = 'video';
  filePreview(file,kind);
};
$('cancel-media').onclick = clearMedia;
$('send-media').onclick = () => run(async () => {
  const current = state.media;
  if (!current) return;
  const cid = state.cid;
  $('send-media').disabled = true;
  const draft = $('draft').value.trim();
  try {
    const data = new FormData();
    data.set('file',current.file);
    data.set('kind',current.kind);
    data.set('request_id',current.id);
    if (draft && state.context?.mode !== 'edit') data.set('text',draft);
    if (current.duration != null) data.set('duration',current.duration);
    if (state.context?.mode === 'reply') data.set('reply',state.context.msg.seq);
    await api(base() + '/media',data);
    if (cid === state.cid && current === state.media) {
      $('draft').value = '';
      clearContext();
      clearMedia();
      state.query = '';
      $('find').hidden = true;
      await loadThread(true);
    }
    schedule();
  } finally { $('send-media').disabled = false; }
});
let awaitingDevices = false;
async function record(kind) {
  if (state.recording || awaitingDevices) return;
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    throw new Error('Для записи откройте приложение через HTTPS или localhost в браузере с поддержкой MediaRecorder');
  }
  const cid = state.cid;
  const video = kind === 'circle';
  awaitingDevices = true;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio:true, video:video ? {width:{ideal:480},height:{ideal:480},facingMode:'user'} : false,
    });
    try {
      if (cid !== state.cid) { stream.getTracks().forEach(track => track.stop()); return; }
      const variants = video ? ['video/webm;codecs=vp8,opus','video/webm','video/mp4'] :
        ['audio/webm;codecs=opus','audio/webm','audio/mp4','audio/ogg'];
      const mimeType = variants.find(type => MediaRecorder.isTypeSupported(type));
      if (!mimeType) throw new Error('Браузер не поддерживает нужный формат записи');
      const recorder = new MediaRecorder(stream,{mimeType,videoBitsPerSecond:1000000});
      const session = {recorder,stream,parts:[],started:Date.now(),cancelled:false};
      recorder.ondataavailable = event => { if (event.data.size) session.parts.push(event.data); };
      recorder.onerror = () => { if (state.recording === session) stopRecording(true); toast('Запись прервалась'); };
      recorder.onstop = () => {
        if (session.cancelled || cid !== state.cid || !session.parts.length) return;
        const mime = recorder.mimeType.split(';')[0];
        const name = (video ? 'Видеокружок.' : 'Голосовое.') + mime.split('/')[1];
        filePreview(new File(session.parts,name,{type:mime}),kind,Math.round((Date.now()-session.started)/1000));
      };
      clearMedia();
      recorder.start(300);
      state.recording = session;
      $('recording').hidden = false;
      $('record-camera').hidden = !video;
      $('record-camera').srcObject = video ? stream : null;
      const max = video ? 60 : 300;
      const tick = () => {
        const elapsed = Math.floor((Date.now()-session.started)/1000);
        $('record-status').textContent = (video ? 'Видеокружок · ' : 'Голосовое · ') + elapsed + ' с';
        if (elapsed >= max) stopRecording(false);
      };
      tick();
      session.timer = setInterval(tick,250);
    } catch (error) {
      stream.getTracks().forEach(track => track.stop());
      throw error;
    }
  } finally { awaitingDevices = false; }
}
function stopRecording(cancelled) {
  const session = state.recording;
  if (!session) return;
  state.recording = null;
  session.cancelled = cancelled;
  clearInterval(session.timer);
  if (session.recorder.state !== 'inactive') session.recorder.stop();
  session.stream.getTracks().forEach(track => track.stop());
  $('record-camera').srcObject = null;
  $('recording').hidden = true;
}
$('voice').onclick = () => run(() => record('voice'));
$('circle').onclick = () => run(() => record('circle'));
$('stop-record').onclick = () => stopRecording(false);
$('cancel-record').onclick = () => stopRecording(true);
function peopleSearch(select,excluded=[]) {
  const panel = node('div','stack');
  const search = node('input');
  search.type = 'search'; search.placeholder = 'Имя или логин'; search.maxLength = 60;
  const results = node('div','stack');
  let timer;
  search.oninput = () => {
    clearTimeout(timer);
    const query = search.value.trim().replace(/^@/,'');
    results.replaceChildren();
    if (!query) return;
    timer = setTimeout(() => run(async () => {
      const people = (await api('/people?q=' + encodeURIComponent(query))).filter(person => !excluded.includes(person.id));
      if (query !== search.value.trim().replace(/^@/,'')) return;
      results.replaceChildren(...people.map(person => button(person.name+' · @'+person.username,
        () => select(person),'secondary person')));
      if (!people.length) results.append(node('small','','Пользователи не найдены'));
    }),200);
  };
  panel.append(search,results);
  return panel;
}
async function newChat(title,people,channel=false) {
  const chat = await api('/chats',{title,people,channel});
  await refresh();
  await selectChat(chat.id);
  close();
}
function createDialog() {
  modal('Новый чат',
    button('Личный чат',() => modal('Найти собеседника',peopleSearch(person => newChat(null,[person.id])))),
    button('Новая группа',() => groupDialog(false),'primary'),
    button('Новый канал',() => groupDialog(true)),
    button('Избранное',async () => {
      const saved = await api('/saved',{});
      await refresh();
      await selectChat(saved.id);
      close();
    }));
}
function groupDialog(channel) {
  const title = node('input'); title.placeholder = channel ? 'Название канала' : 'Название группы'; title.maxLength = 80;
  const chosen = new Map();
  const selected = node('div','dialog-actions');
  const search = peopleSearch(person => {
    chosen.set(person.id,person.name);
    render();
  });
  function render() {
    selected.replaceChildren(...[...chosen].map(([id,name]) =>
      button(name+' ×',() => { chosen.delete(id); render(); },'secondary')));
  }
  modal(channel ? 'Новый канал' : 'Новая группа',title,search,selected,button(channel ? 'Создать канал' : 'Создать группу',
    () => newChat(title.value,[...chosen.keys()],channel),'primary'));
}
$('new-chat').onclick = $('welcome-create').onclick = createDialog;
function checklist(values, triState=false) {
  const panel = node('div','checklist');
  const fields = {};
  for (const [key,title] of Object.entries(rights)) {
    const label = node('label','',title);
    let input;
    if (triState) {
      input = node('select');
      for (const [value,text] of [['','По роли'],['true','Да'],['false','Нет']]) {
        const option = node('option','',text); option.value = value; input.append(option);
      }
      input.value = key in values ? String(values[key]) : '';
    } else {
      input = node('input'); input.type = 'checkbox'; input.checked = values[key];
    }
    label.prepend(input); panel.append(label); fields[key] = input;
  }
  return [panel,() => Object.fromEntries(Object.entries(fields)
    .filter(([,field]) => !triState || field.value !== '')
    .map(([key,field]) => [key,triState ? field.value === 'true' : field.checked]))];
}
async function applySettings(action,data) {
  await chatAction(action,data);
  await refresh();
  if (state.chat) settings();
  else close();
}
function memberSettings(member) {
  const role = node('select'); role.setAttribute('aria-label','Роль');
  for (const key of ['admin','member']) {
    const option = node('option','',roles[key]); option.value = key; role.append(option);
  }
  role.value = member.role;
  const [panel,values] = checklist(member.overrides,true);
  modal(member.name,role,panel,
    button('Сохранить права',() => applySettings('member',{user_id:member.id,role:role.value,permissions:values()}),'primary'),
    button('Передать владение',() => modal('Передать владение группе?',node('p','',member.name+' получит права владельца.'),
      button('Передать',() => applySettings('transfer',{user_id:member.id}),'secondary danger')),'plain'));
}
async function inviteFromUrl() {
  const match = /^#invite\/([A-Za-z0-9_-]{20,128})$/.exec(location.hash);
  if (!match || !state.user) return;
  const token = match[1];
  history.replaceState(null,'',location.pathname + location.search);
  const target = await api('/invite',{token});
  modal('Приглашение',node('p','','Вам предложили вступить: ' + target.title),
    button('Вступить',async () => {
      const joined = await api('/invite',{token,join:true});
      await refresh();
      await selectChat(joined.id);
      close();
    },'primary'));
}
window.addEventListener('hashchange',() => run(inviteFromUrl));
async function showInvite() {
  const {token} = await chatAction('invite-link',{});
  const link = node('input');
  link.readOnly = true;
  link.value = location.origin + '/#invite/' + token;
  link.setAttribute('aria-label','Ссылка для приглашения');
  modal('Ссылка-приглашение',node('small','','Действует семь дней.'),link,
    button('Копировать',async () => {
      if (!navigator.clipboard) { link.select(); return; }
      await navigator.clipboard.writeText(link.value);
      toast('Ссылка скопирована');
    },'primary'));
}
function settings() {
  const chat = state.chat;
  if (!chat) return;
  const actions = node('div','dialog-actions');
  actions.append(button('Удалить чат у себя',() => confirmAction('Удалить чат у себя?',async () => {
    await chatAction('clear',{}); showList(); await refresh();
  }),'plain danger'));
  if (!chat.saved && (chat.direct || chat.role === 'owner')) actions.append(button(chat.direct ? 'Удалить чат у обоих' : 'Удалить историю у всех',
    () => confirmAction('Удалить историю для всех участников?',async () => {
      await chatAction('revoke',{}); showList(); await refresh();
    }),'plain danger'));
  if (chat.direct) { modal(chat.title,actions); return; }
  if (chat.role !== 'owner') actions.append(button('Покинуть группу',() => modal('Покинуть группу?',
    button('Покинуть',async () => { await chatAction('leave',{}); showList(); await refresh(); close(); },'secondary danger')),'plain danger'));
  const tools = node('div','dialog-actions');
  if (chat.permissions.invite) tools.append(button('Пригласить',() => modal('Добавить участника',
    peopleSearch(person => applySettings('invite',{user_id:person.id}),chat.members.map(member => member.id)))));
  if (chat.permissions.invite) tools.append(button('Ссылка-приглашение',showInvite));
  if (chat.role === 'owner') tools.append(button('Отключить ссылки',() => modal('Отключить все ссылки?',
    button('Отключить',async () => { await chatAction('invite-link',{flag:true}); settings(); },'secondary danger')),'plain'));
  if (chat.permissions.manage) tools.append(button('Переименовать',() => {
    const title = node('input'); title.value = chat.title;
    modal('Название группы',title,button('Сохранить',() => applySettings('rename',{text:title.value}),'primary'));
  }));
  if (chat.role === 'owner') tools.append(button('Права группы',() => {
    const [panel,values] = checklist(chat.defaults);
    modal('Права участников по умолчанию',panel,button('Сохранить',() => applySettings('defaults',{permissions:values()}),'primary'));
  }));
  const members = node('div','stack');
  members.append(node('strong','','Участники'));
  for (const member of chat.members) {
    const row = node('div','row panel');
    const name = node('div','grow');
    name.append(node('strong','',member.name + ' '),node('small','','· '+roles[member.role]));
    row.append(name);
    if (member.id !== state.user.id && member.role !== 'owner') {
      if (chat.role === 'owner') row.append(button('Права',() => memberSettings(member),'plain'));
      if (chat.permissions.manage && (chat.role === 'owner' || member.role === 'member')) row.append(button('Удалить',
        () => confirmAction('Удалить участника из группы?',() => applySettings('remove',{user_id:member.id})),'plain danger'));
    }
    members.append(row);
  }
  modal(chat.title,tools,members,actions);
}
$('chat-settings').onclick = settings;
api('/me').then(enter).catch(error => { if (error.status !== 401) toast(error.message); });
