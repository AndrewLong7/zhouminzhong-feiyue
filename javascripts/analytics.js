/* Optional Umami events. No tracker configured = no requests and no pretend statistics. */
(() => {
  const eventNames = new Set(['case_card_click', 'case_search', 'case_filter', 'case_engaged', 'contribute_start', 'questionnaire_click', 'community_open', 'qr_expand']);
  window.fyTrack = (name, data = {}) => {
    if (!eventNames.has(name) || !window.umami || typeof window.umami.track !== 'function') return false;
    if (navigator.doNotTrack === '1' || window.doNotTrack === '1') return false;
    const clean = {};
    if (/^[a-f0-9]{16}$/.test(data.case_id || '')) clean.case_id = data.case_id;
    if (typeof data.has_query === 'boolean') clean.has_query = data.has_query;
    for (const key of ['result_count', 'active_seconds', 'read_percent']) {
      if (Number.isFinite(data[key]) && data[key] >= 0) clean[key] = Math.round(data[key]);
    }
    if (/^(all|0|19\d{2}|20\d{2})$/.test(data.year || '')) clean.year = data.year;
    if (['all', '物理类', '历史类'].includes(data.group)) clean.group = data.group;
    if (['qq', 'wechat'].includes(data.platform)) clean.platform = data.platform;
    try {
      const result = window.umami.track(name, clean);
      if (result && typeof result.catch === 'function') result.catch(() => {});
      return true;
    } catch (_) { return false; }
  };

  function init() {
    document.addEventListener('click', event => {
      const element = event.target.closest('[data-fy-event]');
      if (element) window.fyTrack(element.dataset.fyEvent, { case_id: element.dataset.fyCase });
    });
    document.querySelectorAll('details[data-fy-qr]').forEach(details => {
      let counted = false;
      details.addEventListener('toggle', () => {
        if (details.open && !counted) counted = window.fyTrack('qr_expand', { platform: details.dataset.fyQr });
      });
    });
    const context = document.querySelector('[data-fy-case-id]');
    const article = document.querySelector('.md-content__inner');
    if (!context || !article) return;
    let visibleMs = 0, last = performance.now(), maxRead = 0;
    function updateRead() {
      const rect = article.getBoundingClientRect();
      if (document.visibilityState === 'visible' && rect.height > 0) {
        maxRead = Math.max(maxRead, Math.min(100, Math.max(0, (window.innerHeight - rect.top) / rect.height * 100)));
      }
    }
    function accountVisibleTime() {
      const now = performance.now();
      if (document.visibilityState === 'visible') visibleMs += Math.min(now - last, 1500);
      last = now;
    }
    document.addEventListener('visibilitychange', () => { last = performance.now(); });
    window.addEventListener('scroll', updateRead, { passive: true });
    const timer = setInterval(() => {
      accountVisibleTime(); updateRead();
      if (visibleMs >= 30000 && maxRead >= 50 && window.fyTrack('case_engaged', {
        case_id: context.dataset.fyCaseId, active_seconds: visibleMs / 1000, read_percent: maxRead,
      })) { clearInterval(timer); window.removeEventListener('scroll', updateRead); }
    }, 1000);
    updateRead();
    window.addEventListener('pagehide', () => clearInterval(timer), { once: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
