/* Static HTML keeps all stories available; JS progressively adds filtering and paging. */
(() => {
  function init() {
    const root = document.querySelector('[data-fy-explorer]');
    if (!root || root.dataset.initialized) return;
    root.dataset.initialized = 'true';
    const query = root.querySelector('#fy-case-query');
    const year = root.querySelector('#fy-case-year');
    const group = root.querySelector('#fy-case-group');
    const count = root.querySelector('#fy-case-count');
    const more = root.querySelector('#fy-case-more');
    const empty = root.querySelector('#fy-case-empty');
    const cards = Array.from(root.querySelectorAll('[data-case-id]'));
    let limit = 12, searchTimer;
    const addOptions = (select, values, label) => values.forEach(value => {
      const option = document.createElement('option');
      option.value = value; option.textContent = label(value); select.appendChild(option);
    });
    addOptions(year, [...new Set(cards.map(c => c.dataset.caseYear))].filter(v => Number(v) > 0).sort((a, b) => Number(b) - Number(a)), v => v + ' 届');
    if (cards.some(c => c.dataset.caseYear === '0')) addOptions(year, ['0'], () => '届数未提供');
    addOptions(group, [...new Set(cards.map(c => c.dataset.caseGroup))].filter(Boolean).sort(), v => v);
    query.value = (new URLSearchParams(window.location.search).get('q') || '').slice(0, 100);
    function render() {
      const terms = query.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
      let matched = 0;
      cards.forEach(card => {
        const valid = terms.every(term => card.dataset.caseSearch.toLocaleLowerCase().includes(term)) && (!year.value || card.dataset.caseYear === year.value) && (!group.value || card.dataset.caseGroup === group.value);
        if (valid) matched++;
        card.hidden = !valid || matched > limit;
      });
      count.textContent = '找到 ' + matched + ' 份案例 · 已显示 ' + Math.min(limit, matched) + ' 份';
      more.hidden = matched <= limit; empty.hidden = matched !== 0;
      return matched;
    }
    const track = (name, resultCount) => {
      if (typeof window.fyTrack === 'function') window.fyTrack(name, { result_count: resultCount, has_query: Boolean(query.value.trim()), year: year.value || 'all', group: group.value || 'all' });
    };
    query.addEventListener('input', () => {
      limit = 12; const result = render(); clearTimeout(searchTimer);
      searchTimer = setTimeout(() => { if (query.value.trim()) track('case_search', result); }, 700);
    });
    root.querySelector('form').addEventListener('submit', event => {
      event.preventDefault(); clearTimeout(searchTimer); limit = 12; track('case_search', render());
    });
    [year, group].forEach(select => select.addEventListener('change', () => { clearTimeout(searchTimer); limit = 12; track('case_filter', render()); }));
    root.querySelector('#fy-case-reset').addEventListener('click', () => {
      clearTimeout(searchTimer); query.value = ''; year.value = ''; group.value = ''; limit = 12; render(); query.focus();
    });
    more.addEventListener('click', () => {
      const previousVisible = cards.filter(card => !card.hidden).length;
      limit += 12; render(); const next = cards.filter(card => !card.hidden)[previousVisible];
      if (next) next.querySelector('a').focus();
    });
    root.querySelector('[data-fy-js-controls]').hidden = false; render();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
