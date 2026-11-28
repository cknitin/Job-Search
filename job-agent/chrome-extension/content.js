/* Job Agent Copier.
 * Hover a job -> "Copy job" button -> check the details -> copy to clipboard -> paste into Job Agent.
 * It only reads what is already on your screen, and only when you click. It never clicks, scrolls, applies,
 * stores or sends anything.
 */
(() => {
  const host = location.hostname;
  const SITE = host.includes('linkedin') ? 'linkedin' : host.includes('naukri') ? 'naukri' : 'indeed';

  // The portals change their pages often. If a field comes out empty, select the text and use the panel.
  const SELECTORS = {
    linkedin: {
      card: 'li[data-occludable-job-id], div[data-job-id], .job-card-container, .base-search-card, a[href*="/jobs/view/"]',
      cardTitle: '.artdeco-entity-lockup__title a, a.job-card-container__link, .artdeco-entity-lockup__title, .base-search-card__title',
      cardCompany: '.artdeco-entity-lockup__subtitle, .job-card-container__primary-description, .base-search-card__subtitle',
      cardLocation: '.artdeco-entity-lockup__caption, .job-card-container__metadata-item, .job-search-card__location',
      title: '.job-details-jobs-unified-top-card__job-title, .top-card-layout__title',
      company: '.job-details-jobs-unified-top-card__company-name, .topcard__org-name-link',
      location: '.job-details-jobs-unified-top-card__primary-description-container span, .topcard__flavor--bullet',
      description: '#job-details, .jobs-description__content, .show-more-less-html__markup'
    },
    naukri: {
      card: '.srp-jobtuple-wrapper, article.jobTuple, .cust-job-tuple',
      cardTitle: 'a.title',
      cardCompany: 'a.comp-name, .comp-name, .companyInfo a',
      cardLocation: '.locWdth, .loc-wrap, .location',
      title: 'h1[class*="jd-header-title"]',
      company: '[class*="jd-header-comp-name"] a, [class*="jd-header-comp-name"]',
      location: '[class*="jhc__location"], [class*="jhc__loc"]',
      description: 'section[class*="job-desc-container"], [class*="JDC__dang-inner-html"]'
    },
    indeed: {
      card: '.job_seen_beacon, td.resultContent',
      cardTitle: 'h2.jobTitle',
      cardCompany: '[data-testid="company-name"]',
      cardLocation: '[data-testid="text-location"]',
      title: 'h2[data-testid="jobsearch-JobInfoHeader-title"], h1.jobsearch-JobInfoHeader-title, [data-testid="jobsearch-JobInfoHeader-title"]',
      company: '[data-testid="inlineHeader-companyName"]',
      location: '[data-testid="inlineHeader-companyLocation"], [data-testid="job-location"]',
      description: '#jobDescriptionText'
    }
  }[SITE];

  const clean = s => (s || '').replace(/\r/g, '').replace(/[ \t ]+/g, ' ').replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n').trim();
  const first = (root, selector) => root.querySelector(selector);
  const line = (root, selector) => {
    const el = first(root, selector);
    // Some titles are repeated for screen readers: keep the first line only.
    return el ? clean(el.innerText).split('\n')[0].replace(/\s*- job post$/i, '') : '';
  };

  // A short, shareable link without tracking parameters.
  function jobLink(href) {
    let url;
    try { url = new URL(href || location.href, location.href); } catch (e) { return location.href; }
    if (SITE === 'linkedin') {
      const id = url.searchParams.get('currentJobId') || (url.pathname.match(/\/jobs\/view\/(?:[^/]*?-)?(\d{6,})/) || [])[1];
      return id ? `https://www.linkedin.com/jobs/view/${id}/` : url.origin + url.pathname;
    }
    if (SITE === 'indeed') {
      const id = url.searchParams.get('jk') || url.searchParams.get('vjk');
      return id ? `${url.origin}/viewjob?jk=${id}` : url.href;
    }
    return url.origin + url.pathname;
  }

  // LinkedIn's newer layout has no stable class names, so fall back to the "About the job" heading.
  function aboutTheJob() {
    const heading = [...document.querySelectorAll('h2, h3')].find(h => /^about the job$/i.test(h.innerText.trim()));
    let box = heading && heading.parentElement;
    while (box && box.innerText.trim().length < 300 && box.parentElement !== document.body) box = box.parentElement;
    return box ? clean(box.innerText).replace(/^about the job\s*/i, '') : '';
  }

  function openJob() {
    const found = first(document, SELECTORS.description);
    const job = {
      title: line(document, SELECTORS.title), company: line(document, SELECTORS.company),
      location: line(document, SELECTORS.location), url: jobLink(),
      description: found ? clean(found.innerText) : ''
    };
    if (SITE === 'linkedin') {
      if (!job.description) job.description = aboutTheJob();
      const parts = document.title.replace(/^\(\d+\)\s*/, '').split(' | ');
      if (parts.length >= 3) { job.title = job.title || parts[0]; job.company = job.company || parts[1]; }
    }
    return job;
  }

  function fromCard(card) {
    const anchor = card.matches('a[href]') ? card : first(card, 'h2 a[href], a.title, a[href*="/jobs/view/"], a[href*="jk="], a[href]');
    const jk = SITE === 'indeed' && (first(card, '[data-jk]') || card.closest('[data-jk]'));
    const job = {
      title: line(card, SELECTORS.cardTitle) || (anchor ? clean(anchor.innerText).split('\n')[0] : ''),
      company: line(card, SELECTORS.cardCompany), location: line(card, SELECTORS.cardLocation),
      url: jobLink(jk ? `/viewjob?jk=${jk.getAttribute('data-jk')}` : anchor && anchor.getAttribute('href')),
      description: ''
    };
    const shown = openJob();
    // Use the description only if the job that is open on the page is this same job.
    if (shown.description && (shown.url === job.url || (shown.title === job.title && shown.company === job.company))) {
      job.description = shown.description;
    }
    return job;
  }

  const asText = j => `Title: ${j.title}\nCompany: ${j.company}\nLocation: ${j.location}\nURL: ${j.url}\n---\n${j.description}`;

  // ---------- interface (kept in a shadow root so the site's styles do not affect it) ----------
  const box = document.createElement('div');
  box.id = 'job-agent-copier';
  const root = box.attachShadow({ mode: 'open' });
  root.innerHTML = `<style>
    *{box-sizing:border-box;font-family:"Segoe UI",Arial,sans-serif}
    button{cursor:pointer;border:0;border-radius:99px;font-weight:700;font-size:13px;padding:9px 15px;color:#fff;
      background:linear-gradient(110deg,#7c3aed,#db2777 60%,#f97316);box-shadow:0 6px 18px #0004}
    #hover,#main{position:fixed;z-index:2147483646} #hover{display:none} #main{right:20px;bottom:20px}
    #panel{display:none;position:fixed;z-index:2147483647;right:20px;bottom:20px;width:370px;max-height:86vh;overflow:auto;
      background:#12121f;color:#f2f1fa;border:1px solid #ffffff26;border-radius:18px;padding:16px;box-shadow:0 20px 60px #0008}
    label{display:block;font-size:11px;font-weight:700;color:#a3a1bd;margin-top:8px}
    input,textarea{width:100%;font-size:13px;color:#f2f1fa;background:#ffffff10;border:1px solid #ffffff22;border-radius:10px;padding:8px}
    .row{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap} .plain{background:#ffffff1f;box-shadow:none}
    #note{font-size:12px;margin-top:10px;color:#fcd34d} h3{margin:0;font-size:15px}
  </style>
  <button id="hover" type="button">📋 Copy job</button>
  <button id="main" type="button">📋 Copy this job</button>
  <div id="panel" role="dialog" aria-label="Copy job">
    <h3>Check, then copy</h3>
    <label>Job title<input id="title"></label><label>Company<input id="company"></label>
    <label>Location<input id="location"></label><label>Link<input id="url"></label>
    <label>Description<textarea id="description" rows="8"></textarea></label>
    <div id="note" aria-live="polite"></div>
    <div class="row"><button id="copy" type="button">Copy for Job Agent</button>
      <button id="usesel" type="button" class="plain">Use selected text</button>
      <button id="close" type="button" class="plain">Close</button></div>
  </div>`;
  document.documentElement.appendChild(box);

  const $ = id => root.getElementById(id);
  const FIELDS = ['title', 'company', 'location', 'url', 'description'];
  const selected = () => clean(String(window.getSelection()));
  let card = null;

  function open(job) {
    const picked = selected();
    if (picked.split(/\s+/).length >= 30) job.description = picked;  // your selection wins
    FIELDS.forEach(f => { $(f).value = job[f]; });
    $('panel').style.display = 'block';
    $('hover').style.display = 'none';
    $('note').textContent = job.description ? ''
      : 'No description yet. Open this job and copy again, or select its text and click "Use selected text".';
  }

  // Pressing a button must not clear the text you selected on the page.
  root.addEventListener('mousedown', e => { if (e.target.tagName === 'BUTTON') e.preventDefault(); });
  $('main').onclick = () => open(openJob());
  $('hover').onclick = () => card && open(fromCard(card));
  $('close').onclick = () => { $('panel').style.display = 'none'; };
  $('usesel').onclick = () => {
    const picked = selected();
    if (picked) { $('description').value = picked; $('note').textContent = ''; }
    else $('note').textContent = 'Select the description on the page first.';
  };
  $('copy').onclick = async () => {
    const job = Object.fromEntries(FIELDS.map(f => [f, $(f).value.trim()]));
    try {
      await navigator.clipboard.writeText(asText(job));
      $('note').textContent = job.description ? 'Copied. In Job Agent click "Paste copied job".'
        : 'Copied without a description. It can only be recorded as already applied.';
    } catch (e) {
      $('note').textContent = 'The browser blocked copying. Click the page once and try again.';
    }
  };

  document.addEventListener('mouseover', event => {
    if (event.target === box) return;
    const target = event.target.closest && event.target.closest(SELECTORS.card);
    if (!target) return;
    card = target;
    const r = target.getBoundingClientRect();
    Object.assign($('hover').style, {
      display: 'block', top: `${Math.max(4, r.top + 6)}px`,
      left: `${Math.max(4, Math.min(r.right - 125, window.innerWidth - 135))}px`
    });
  });
  window.addEventListener('scroll', () => { $('hover').style.display = 'none'; }, true);
})();
