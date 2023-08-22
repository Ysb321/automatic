let dragDropInitialized = false;

async function initDragDrop() {
  if (dragDropInitialized) return;
  dragDropInitialized = true;
  console.log('initDragDrop');
  window.addEventListener('drop', (e) => {
    const target = e.composedPath()[0];
    if (!target.placeholder) return;
    if (target.placeholder.indexOf('Prompt') === -1) return;
    const promptTarget = get_tab_index('tabs') === 1 ? 'img2img_prompt_image' : 'txt2img_prompt_image';
    e.stopPropagation();
    e.preventDefault();
    const imgParent = gradioApp().getElementById(promptTarget);
    if (!imgParent) return;
    const { files } = e.dataTransfer;
    const fileInput = imgParent.querySelector('input[type="file"]');
    if (fileInput) {
      fileInput.files = files;
      fileInput.dispatchEvent(new Event('change'));
      console.log('dropEvent');
    }
  });
}

onAfterUiUpdate(initDragDrop);
