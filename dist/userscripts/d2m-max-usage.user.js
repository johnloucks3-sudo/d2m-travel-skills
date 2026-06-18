// ==UserScript==
// @name         D2M · MAX Usage → Cost Dashboard
// @namespace    d2mluxury
// @version      1.0
// @description  Auto-push claude.ai MAX (20x) session/weekly usage to costs.d2mluxury.quest every 60s
// @match        https://claude.ai/settings/usage*
// @grant        GM_xmlhttpRequest
// @connect      costs.d2mluxury.quest
// @run-at       document-idle
// ==/UserScript==
(function () {
  'use strict';
  function pushUsage() {
    try {
      var L = document.body.innerText.split('\n').map(function(s){return s.trim();}).filter(Boolean);
      var f = function(a){ var i = L.findIndex(function(s){return s.toLowerCase().startsWith(a);}); return i<0?[]:L.slice(i+1,i+5); };
      var pct = function(A){ for (var k=0;k<A.length;k++){ var m=A[k].match(/(\d+)%\s*used/i); if(m) return +m[1]; } return null; };
      var rs  = function(A){ for (var k=0;k<A.length;k++){ if(/^resets\b/i.test(A[k])) return A[k]; } return null; };
      var tier = (L.find(function(s){return /max\s*\(\d+x\)/i.test(s);}) || 'Max');
      var se = f('current session'), al = f('all models'), so = f('sonnet only');
      var p = { plan_tier: tier,
                session_pct: pct(se), session_reset: rs(se),
                weekly_all_pct: pct(al), weekly_all_reset: rs(al),
                weekly_sonnet_pct: pct(so), weekly_sonnet_reset: rs(so) };
      if (p.session_pct == null && p.weekly_all_pct == null) return; // page not rendered yet
      GM_xmlhttpRequest({
        method: 'POST',
        url: 'https://costs.d2mluxury.quest/api/plan?token=yoda-grandeur',
        headers: { 'Content-Type': 'application/json' },
        data: JSON.stringify(p)
      });
    } catch (e) { /* silent */ }
  }
  setTimeout(pushUsage, 4000);    // first push after the page renders
  setInterval(pushUsage, 60000);  // then every 60 seconds
})();
