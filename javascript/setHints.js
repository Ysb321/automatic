const localeData = {
  data: [],
  timeout: null,
  finished: false,
  type: 2,
  el: null,
};

function tooltipCreate() {
  localeData.el = document.createElement('div');
  localeData.el.className = 'tooltip';
  localeData.el.id = 'tooltip-container';
  localeData.el.innerText = 'this is a hint';
  gradioApp().appendChild(localeData.el);
  if (window.opts.tooltips === 'None') localeData.type = 0;
  if (window.opts.tooltips === 'Browser default') localeData.type = 1;
  if (window.opts.tooltips === 'UI tooltips') localeData.type = 2;
}

async function tooltipShow(e) {
  if (e.target.dataset.hint) {
    localeData.el.classList.add('tooltip-show');
    localeData.el.innerHTML = `<b>${e.target.textContent}</b><br>${e.target.dataset.hint}`;
  }
}

async function tooltipHide(e) {
  localeData.el.classList.remove('tooltip-show');
}

async function validateHints(elements, data) {
  let original = elements.map((e) => e.textContent.toLowerCase().trim()).sort((a, b) => a > b);
  original = [...new Set(original)];
  console.log('all hints:', original);
  console.log('hints-differences', { elements: original.length, hints: data.length });
  const current = data.map((e) => e.label.toLowerCase().trim()).sort((a, b) => a > b);
  let missing = [];
  for (let i = 0; i < original.length; i++) {
    if (!current.includes(original[i])) missing.push(original[i]);
  }
  console.log('missing in locale:', missing);
  missing = [];
  for (let i = 0; i < current.length; i++) {
    if (!original.includes(current[i])) missing.push(current[i]);
  }
  console.log('in locale but not ui:', missing);
}

async function setHints() {
  if (localeData.finished) return;
  if (localeData.data.length === 0) {
    const res = await fetch('/file=html/locale_en.json');
    const json = await res.json();
    localeData.data = Object.values(json).flat();
  }
  const elements = [
    ...Array.from(gradioApp().querySelectorAll('button')),
    ...Array.from(gradioApp().querySelectorAll('label > span')),
  ];
  if (elements.length === 0) return;
  if (Object.keys(opts).length === 0) return;
  if (!localeData.el) tooltipCreate();
  let localized = 0;
  let hints = 0;
  localeData.finished = true;
  const t0 = performance.now();
  for (const el of elements) {
    const found = localeData.data.find((l) => l.label === el.textContent.trim());
    if (found?.localized?.length > 0) {
      localized++;
      el.textContent = found.localized;
    }
    if (found?.hint?.length > 0) {
      hints++;
      if (localeData.type === 1) {
        el.title = found.hint;
      } else if (localeData.type === 2) {
        el.dataset.hint = found.hint;
        el.addEventListener('mouseover', tooltipShow);
        el.addEventListener('mouseout', tooltipHide);
      } else {
        // tooltips disabled
      }
    }
  }
  const t1 = performance.now();
  console.log('setHints', { type: localeData.type, elements: elements.length, localized, hints, data: localeData.data.length, time: t1 - t0 });
  removeSplash();
  // validateHints(elements, localeData.data)
}

onAfterUiUpdate(async () => {
  if (localeData.timeout) clearTimeout(localeData.timeout);
  localeData.timeout = setTimeout(setHints, 250);
});
