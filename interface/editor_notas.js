'use strict';
// Vditor edits Markdown; the existing field remains the persistence boundary.
window.EditorNotas=class {
  constructor(onInput){
    this.field=document.getElementById('apuracao-texto');
    this.host=document.getElementById('apuracao-vditor');
    this.onInput=onInput;
    this.ready=false;
    this.locked=false;
    this.field.addEventListener('input',onInput);
    this.host.addEventListener('input',event=>{
      if(this.locked||!event.target.matches('.vditor-sv,[contenteditable="true"]'))return;
      this.edited=true;
      this.onInput();
    });
  }
  open(text){
    this.field.value=text;
    this.edited=false;
    if(this.ready){this.instance.setValue(text,true);return;}
    if(this.instance||this.failed)return;
    try{
      if(!window.Vditor||!window.Lute||!window.VditorI18n)throw new Error('Arquivos do editor indisponíveis.');
      this.instance=new Vditor(this.host,{
        cdn:'/vendor/vditor',lang:'pt_BR',i18n:{...window.VditorI18n,wysiwyg:'Edição visual',splitView:'Markdown e prévia'},
        mode:'wysiwyg',value:text,cache:{enable:false},
        minHeight:360,height:520,placeholder:'Escreva sua nota…',
        toolbar:['headings','bold','italic','strike','link','|','list','ordered-list','check','quote','line','table','|','undo','redo','edit-mode'],
        toolbarConfig:{pin:false},
        link:{isOpen:false},image:{isPreview:false},hint:{parse:false},
        preview:{
          delay:150,actions:[],mode:'both',hljs:{enable:false},
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
        after:()=>{
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
      });
    }catch(failure){
      this.failed=true;this.host.hidden=true;
      document.getElementById('apuracao-texto-alternativo').hidden=false;
      const notice=document.getElementById('apuracao-editor-aviso');
      notice.textContent='O editor visual não carregou. Você pode editar e salvar o Markdown abaixo.';
      notice.hidden=false;
    }
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
