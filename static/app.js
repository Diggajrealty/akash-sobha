const $ = selector => document.querySelector(selector);
const form = $('#generator'), button = $('#generate'), status = $('#status'), download = $('#download');
const combined = $('#include-owners');
let currentUrl, lookupSequence = 0, lookupTimer;
let activeQuery = '', activePage = 1, searchSequence = 0;
function showTab(name) {
  for (const tabName of ['studio', 'owners']) {
    const selected = name === tabName;
    $(`#${tabName}-panel`).hidden = !selected;
    $(`#${tabName}-tab`).classList.toggle('active', selected);
    $(`#${tabName}-tab`).setAttribute('aria-selected', String(selected));
    $(`#${tabName}-tab`).tabIndex = selected ? 0 : -1;
  }
}
for (const name of ['studio', 'owners']) {
  $(`#${name}-tab`).addEventListener('click', () => showTab(name));
  $(`#${name}-tab`).addEventListener('keydown', event => {
    if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      const target = event.key === 'Home' ? 'studio' : event.key === 'End' ? 'owners' : name === 'studio' ? 'owners' : 'studio';
      showTab(target); $(`#${target}-tab`).focus();
    }
  });
}
async function post(url, data) {
  const response = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.error || 'The request could not be completed. Please try again.');
  }
  return response;
}
function errorText(error) {
  return error instanceof TypeError ? 'Connection interrupted. Check your connection and try again.' : error.message;
}
function setCombined(group, selected = false) {
  const allowed = group && group.can_combine;
  $('#combined-option').hidden = !allowed;
  combined.checked = Boolean(allowed && selected);
  combined.disabled = !allowed;
  $('#combined-hint').textContent = allowed ? `${group.records.length} applicant record(s) found. Adds all their sheet details after the three-page brochure.` : '';
}
setCombined(null);
$('#unit').addEventListener('input', () => {
  clearTimeout(lookupTimer);
  const sequence = ++lookupSequence;
  setCombined(null);
  const unit = $('#unit').value.trim();
  if (!/^[0-9]{4,5}$/.test(unit)) return;
  lookupTimer = setTimeout(async () => {
    try {
      const response = await post('/api/owners/unit', {unit});
      const group = await response.json();
      if (sequence === lookupSequence) setCombined(group);
    } catch { /* Brochure generation remains available without a directory match. */ }
  }, 400);
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  button.disabled = true;
  button.firstElementChild.textContent = 'Creating your brochure…';
  status.className = 'working'; status.textContent = 'Reading the unit details and preparing your PDF…';
  download.hidden = true;
  if (currentUrl) { URL.revokeObjectURL(currentUrl); currentUrl = undefined; }
  const payload = {...Object.fromEntries(new FormData(form)), negotiable: $('#negotiable').checked, add_diggaj_watermark: $('#add-diggaj-watermark').checked, add_my_details: $('#add-my-details').checked, include_owners: !combined.disabled && combined.checked};
  try {
    const response = await post('/api/generate', payload);
    if (!response.headers.get('Content-Type')?.includes('application/pdf')) throw new Error('An unexpected response was received. Please try again.');
    currentUrl = URL.createObjectURL(await response.blob()); download.href = currentUrl;
    download.download = `Sobha_Neopolis_Unit_${payload.unit.trim()}${payload.include_owners ? '_With_Owner_Records' : ''}_Diggaj_Realty.pdf`;
    download.hidden = false; download.click();
    status.className = 'success';
    status.textContent = `Your ${payload.include_owners ? 'combined PDF' : 'brochure'} for unit ${payload.unit.trim()} is ready. If the download hasn’t started, use the link below.`;
  } catch (error) {
    status.className = 'error'; status.textContent = errorText(error);
  } finally {
    button.disabled = false; button.firstElementChild.textContent = 'Generate & download PDF';
  }
});
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function renderGroup(group) {
  const card = el('article', 'owner-card'), heading = el('div', 'result-heading'), title = el('div');
  title.append(el('span', 'eyebrow', group.records[0].Project || 'CLIENT RECORD'));
  title.append(el('h3', '', group.unit ? `Unit ${group.unit}` : group.records[0].Unit || 'Unmatched unit'));
  title.append(el('p', '', `${group.records.length} applicant record(s) · ${group.records[0].Configuration || 'Configuration not listed'} · ${group.records[0].SBA || '—'} sq ft`));
  heading.append(title);
  if (group.can_combine) {
    const action = el('button', 'secondary', 'Combine with brochure ↗');
    action.addEventListener('click', () => {
      ++lookupSequence; clearTimeout(lookupTimer);
      $('#unit').value = group.unit; $('#facing').value = ''; $('#price').value = '';
      setCombined(group, true); showTab('studio');
      status.textContent = `Unit ${group.unit} selected with all ${group.records.length} applicant record(s). Add facing and price if known, then generate.`;
      status.className = 'success'; download.hidden = true;
      $('#facing').focus(); window.scrollTo({top: 180, behavior: 'smooth'});
    });
    heading.append(action);
  } else heading.append(el('span', 'unavailable', 'No matching generator plan'));
  card.append(heading);
  group.records.forEach((row, index) => {
    const details = el('details', 'applicant'); details.open = index === 0;
    const summary = el('summary', '', `${row['Applicant Name'] || 'Unnamed applicant'} · ${row['Applicant Number'] || 'Applicant'}`);
    const fields = el('dl', 'record-fields');
    for (const [key, value] of Object.entries(row)) {
      const cell = el('div'); cell.append(el('dt', '', key), el('dd', '', value || '—')); fields.append(cell);
    }
    details.append(summary, fields); card.append(details);
  });
  return card;
}
async function search(query, page) {
  const sequence = ++searchSequence;
  $('#search-button').disabled = true; $('#previous').disabled = true; $('#next').disabled = true;
  $('#search-status').className = ''; $('#search-status').textContent = 'Searching your client sheet and checking available floor plans…';
  $('#owner-results').replaceChildren(); $('#pagination').hidden = true;
  try {
    const response = await post('/api/owners/search', {query, page}), data = await response.json();
    if (sequence !== searchSequence) return;
    activeQuery = query; activePage = page;
    $('#search-status').textContent = data.total_units ? `${data.total_units} matching unit(s). Showing all applicants for each matched unit.` : 'No matching records. Try a different name, unit, phone number or email.';
    for (const group of data.results) $('#owner-results').append(renderGroup(group));
    $('#pagination').hidden = data.pages <= 1;
    $('#page-label').textContent = `Page ${page} of ${data.pages}`;
    $('#previous').disabled = page <= 1; $('#next').disabled = page >= data.pages;
  } catch (error) {
    if (sequence === searchSequence) { $('#search-status').textContent = errorText(error); $('#search-status').className = 'error'; }
  } finally {
    if (sequence === searchSequence) $('#search-button').disabled = false;
  }
}
$('#owner-search').addEventListener('submit', event => {
  event.preventDefault(); if ($('#owner-search').reportValidity()) search($('#query').value.trim(), 1);
});
$('#previous').addEventListener('click', () => search(activeQuery, activePage - 1));
$('#next').addEventListener('click', () => search(activeQuery, activePage + 1));
