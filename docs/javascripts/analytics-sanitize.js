/* Runs before the tracker. Keep campaign codes; never send search text or contact values. */
(() => {
  const allowed = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'];
  window.fyBeforeSend = (_type, payload) => {
    if (!payload || typeof payload !== 'object') return false;
    try {
      const result = { ...payload };
      const url = new URL(result.url || window.location.pathname, window.location.origin);
      const params = new URLSearchParams();
      allowed.forEach(key => {
        const value = url.searchParams.get(key);
        if (value && /^[a-z][a-z0-9_-]{0,63}$/i.test(value)) params.set(key, value);
      });
      result.url = url.pathname + (params.size ? '?' + params.toString() : '');
      // Referrer query strings may contain search terms or identifiers.
      result.referrer = result.referrer ? new URL(result.referrer, window.location.origin).origin : '';
      return result;
    } catch (_) { return false; }
  };
})();
