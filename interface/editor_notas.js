'use strict';
// Vditor (about 4 MB) is fetched from this same origin only when the notebook editor
// first opens; every other area loads without it. Ids match the ones Vditor checks
// before adding its own copies of Lute and the icon sprite.
window.CarregadorVditor = (() => {
  // Same as vendor/vditor/manifesto.json (a test keeps them equal). Versioned URLs let the
  // server cache these files as immutable; a new Vditor version means new URLs.
  const VERSAO = '4.0.1';
  const base = '/vendor/vditor/dist';
  const versioned = file => `${base}${file}?v=${VERSAO}`;
  // The content theme carries Vditor's own id, so Vditor does not add an unversioned copy.
  const sheets = [[versioned('/index.css')], [versioned('/css/content-theme/light.css'), 'vditorContentTheme']];
  const scripts = [[versioned('/index.min.js')], [versioned('/js/lute/lute.min.js'), 'vditorLuteScript'],
    [versioned('/js/i18n/pt_BR.js')], [versioned('/js/icons/ant.js'), 'vditorIconScript']];
  const requests = new Map();
  let pending = null;
  const ready = () => Boolean(window.Vditor && window.Lute && window.VditorI18n);
  function addSheet([href, id]) {
    if (document.querySelector(`link[href="${href}"]`)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet'; link.href = href;
    if (id) link.id = id;
    // Keep the application's stylesheet last, as when both were static.
    const app = document.querySelector('link[href^="/style.css"]');
    if (app) app.before(link); else document.head.append(link);
  }
  function addScript([src, id]) {
    return new Promise((resolve, reject) => {
      const tag = document.createElement('script');
      tag.src = src; tag.async = false;
      if (id) tag.id = id;
      tag.addEventListener('load', resolve);
      tag.addEventListener('error', () => { tag.remove(); reject(new Error(`Falha ao carregar ${src}.`)); });
      document.head.append(tag);
    });
  }
  // A retry re-requests only what failed; loaded or in-flight files are reused.
  function request(entry) {
    const [src] = entry;
    if (!requests.has(src)) requests.set(src, addScript(entry).catch(error => { requests.delete(src); throw error; }));
    return requests.get(src);
  }
  function load() {
    if (ready()) return Promise.resolve();
    if (!pending) {
      sheets.forEach(addSheet);
      pending = Promise.all(scripts.map(request))
        .then(() => { if (!ready()) throw new Error('Arquivos do editor indisponíveis.'); })
        .finally(() => { pending = null; });
    }
    return pending;
  }
  return {load, ready};
})();

// Vditor edits Markdown; the existing field remains the persistence boundary.
window.EditorNotas=class {
  constructor(onInput){
    this.field=document.getElementById('apuracao-texto');
    this.host=document.getElementById('apuracao-vditor');
    this.notice=document.getElementById('apuracao-editor-aviso');
    this.retryButton=document.getElementById('apuracao-editor-tentar');
    this.fallbackLabel=document.getElementById('apuracao-texto-alternativo');
    this.onInput=onInput;
    this.ready=false;
    this.locked=false;
    this.field.addEventListener('input',onInput);
    this.host.addEventListener('input',event=>{
      if(this.locked||!event.target.matches('.vditor-sv,[contenteditable="true"]'))return;
      this.edited=true;
      this.onInput();
    });
    this.retryButton.addEventListener('click',()=>this.start());
    // Notes may be prefetched while the notebook is hidden; the editor waits until it is shown.
    window.addEventListener('apuracao-abrir',()=>{if(this.wanted&&!this.instance&&!this.failed)this.start();});
  }
  open(text){
    this.field.value=text;
    this.edited=false;
    if(this.ready){this.instance.setValue(text,true);return;}
    this.wanted=true;
    if(!this.instance&&!this.failed&&!this.host.closest('[hidden]'))this.start();
  }
  status(message,retry=false){
    this.notice.textContent=message;this.notice.hidden=!message;this.retryButton.hidden=!retry;
  }
  start(){
    if(this.loading||this.instance)return;
    this.loading=true;this.failed=false;
    this.status('Carregando o editor de notas…');
    window.CarregadorVditor.load()
      .then(()=>{this.loading=false;this.create();})
      .catch(()=>{this.loading=false;this.fallback();});
  }
  fallback(){
    // The Markdown field keeps editing and saving while the visual editor is missing.
    this.failed=true;this.host.hidden=true;this.fallbackLabel.hidden=false;
    this.status('O editor visual não carregou. Você pode editar e salvar o Markdown abaixo ou tentar de novo.',true);
  }
  create(){
    try{
      if(!window.CarregadorVditor.ready())throw new Error('Arquivos do editor indisponíveis.');
      this.host.hidden=false;this.fallbackLabel.hidden=true;this.status('');
      this.instance=new Vditor(this.host,{
        cdn:'/vendor/vditor',lang:'pt_BR',i18n:{...window.VditorI18n,wysiwyg:'Edição visual',splitView:'Markdown e prévia'},
        mode:'wysiwyg',value:this.field.value,cache:{enable:false},
        minHeight:360,height:520,placeholder:'Escreva sua nota…',
        toolbar:['headings','bold','italic','strike','link','|','list','ordered-list','check','quote','line','table','|','undo','redo','edit-mode'],
        toolbarConfig:{pin:false},
        link:{isOpen:false},image:{isPreview:false},hint:{parse:false},
        preview:{
          delay:150,actions:[],mode:'both',hljs:{enable:false},
          // The versioned content theme is already on the page; an empty theme stops Vditor adding its own.
          theme:{current:'',path:''},
          markdown:{sanitize:true,autoSpace:false,fixTermTypo:false,codeBlockPreview:false,mathBlockPreview:false,inlineMath:false},
          render:{media:{enable:false}},
          // Display diagram/formula code literally, without optional renderers or services.
          transform:html=>{
            const template=document.createElement('template');template.innerHTML=html;
            for(const block of template.content.querySelectorAll('[class*="language-"]')){
              if(block.tagName==='CODE'){block.removeAttribute('class');continue;}
              const pre=document.createElement('pre'),code=document.createElement('code');
              code.textContent=block.textContent;pre.append(code);block.replaceWith(pre);
            }
            return template.innerHTML;
          }
        },
        input:value=>{
          if(!this.ready||this.locked)return;
          this.edited=true;
          this.field.value=value;
          this.onInput();
        },
        after:()=>this.connected()
      });
    }catch(failure){
      this.instance=null;this.fallback();
    }
  }
  connected(){
    this.ready=true;
    // Initialization may finish after another note/case has been selected.
    this.instance.setValue(this.field.value,true);
    for(const field of this.host.querySelectorAll('[contenteditable],textarea')){
      field.setAttribute('aria-label','Texto da nota');
      field.setAttribute('aria-describedby','apuracao-editor-ajuda');
      if(field.hasAttribute('contenteditable')){
        field.setAttribute('role','textbox');field.setAttribute('aria-multiline','true');
      }
    }
    const buttonTypes=()=>{for(const button of this.host.querySelectorAll('button:not([type])'))button.type='button';};
    buttonTypes();
    this.buttons=new MutationObserver(buttonTypes);
    this.buttons.observe(this.host,{childList:true,subtree:true});
    this.disabled(this.locked);
  }
  flush(){
    // Read pending browser input before locking the editor for a save.
    // Untouched notes retain their original Markdown, including whitespace.
    if(this.ready&&this.edited)this.field.value=this.instance.getValue();
  }
  disabled(value){
    if(this.locked===value&&this.appliedLock===value)return;
    this.locked=value;
    this.host.inert=value;
    this.host.setAttribute('aria-busy',String(value));
    if(this.ready){
      if(value)this.instance.disabled();else this.instance.enable();
      this.appliedLock=value;
    }
  }
};
