/**
 * 首页/案例库/大学分类页的"装饰性搜索框"代理。
 *
 * 这些搜索框只是视觉入口，真正的检索复用 mkdocs-material 自带的搜索面板。
 * 用户在装饰搜索框里按下回车后：
 *   1. 触发顶部搜索按钮 → 打开搜索面板
 *   2. 把关键词填进真实搜索框并聚焦 → 触发检索
 *
 * 适用元素：任何带 [data-fy-search-proxy] 属性的 <input>
 */
(function () {
  function handleEnter(event) {
    if (event.key !== "Enter") return;

    var query = event.currentTarget.value.trim();
    if (!query) return;

    var realInput = document.querySelector(".md-search__input");
    if (!realInput) return;

    var toggleLabel = document.querySelector("[for=__search]");
    if (toggleLabel) toggleLabel.click();

    realInput.value = query;
    realInput.focus();
    realInput.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
  }

  function bindAll() {
    var proxies = document.querySelectorAll("[data-fy-search-proxy]");
    proxies.forEach(function (input) {
      input.addEventListener("keydown", handleEnter);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindAll);
  } else {
    bindAll();
  }
})();
