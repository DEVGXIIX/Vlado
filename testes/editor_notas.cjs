// Drive the real Vditor UI; persisted Markdown remains observable in the backing field.
async function mode(page,name){
  await page.locator('#apuracao-vditor .vditor-toolbar').waitFor();
  await page.locator('#apuracao-vditor button[data-type="edit-mode"]').click();
  await page.locator(`#apuracao-vditor button[data-mode="${name}"]`).click();
}
async function write(page,text){
  if(!await page.locator('#apuracao-vditor .vditor-sv').isVisible())await mode(page,'sv');
  await page.locator('#apuracao-vditor .vditor-sv').fill(text);
  await page.waitForFunction(text=>document.querySelector('#apuracao-texto').value.trim()===text.trim(),text);
}
const read=page=>page.locator('#apuracao-texto').inputValue();
module.exports={mode,write,read};
