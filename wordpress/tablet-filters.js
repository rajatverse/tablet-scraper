/**
 * tablet-filters.js — TopTablets Spec-Hub Interactive Logic
 *
 * Handles:
 *  1. Sticky buy-bar scroll visibility (triggers at 380px)
 *  2. Spec category tab switching (.tt-tab buttons with data-tab-cat)
 *  3. Live search filtering on #tt-spec-search input
 *
 * This file is enqueued via functions.php (wp_enqueue_script) so that it
 * loads in the footer AFTER the DOM is painted. It must NEVER be placed
 * inside a Gutenberg "Custom HTML" block -- WordPress KSES strips <script>
 * tags from content, causing the raw JS to display as visible page text.
 */

(function () {
  'use strict';

  /* 1. Sticky Buy Bar - scroll trigger at 380px */
  var bar = document.getElementById('tt-sticky-buy-bar');
  if (bar) {
    window.addEventListener('scroll', function () {
      bar.style.display = window.scrollY > 380 ? 'flex' : 'none';
    }, { passive: true });
  }

  /* 2. Spec Tab Switching
     Buttons carry  data-tab-cat="tab-all|tab-display|tab-perf|tab-battery"
     Active button gets bg:#2563eb / color:#fff */
  var activeSpecCategory = 'tab-all';

  function applySpecFilter(cat, query) {
    var items = document.querySelectorAll('.tt-spec-grid .tt-spec-item');
    var visibleCount = 0;
    items.forEach(function (it) {
      var itemCat = it.getAttribute('data-category');
      var catMatches = (cat === 'tab-all' || itemCat === cat);
      var textMatches = true;
      if (query) {
        var itemText = (it.textContent || '').toLowerCase();
        textMatches = itemText.indexOf(query) !== -1;
      }
      if (catMatches && textMatches) {
        it.style.display = 'flex';
        visibleCount++;
      } else {
        it.style.display = 'none';
      }
    });
    
    var emptyMsg = document.getElementById('tt-spec-empty');
    if (emptyMsg) {
      emptyMsg.style.display = visibleCount === 0 ? 'block' : 'none';
    }
  }

  function switchSpecTab(cat) {
    activeSpecCategory = cat;
    var tabs = document.querySelectorAll('.tt-spec-pills .tt-tab');
    tabs.forEach(function (t) {
      var isActive = (t.getAttribute('data-tab-cat') === cat);
      t.classList.toggle('active', isActive);
      t.style.background  = isActive ? '#2563eb' : 'transparent';
      t.style.color       = isActive ? '#ffffff' : '#475569';
      t.style.borderColor = isActive ? '#2563eb' : 'transparent';
      t.style.fontWeight  = isActive ? '700'     : '600';
    });
    var searchInput = document.getElementById('tt-spec-search');
    var query = searchInput ? (searchInput.value || '').trim().toLowerCase() : '';
    applySpecFilter(cat, query);
  }

  /* Event delegation on the pill container */
  var pillContainer = document.querySelector('.tt-spec-pills');
  if (pillContainer) {
    pillContainer.addEventListener('click', function (e) {
      var btn = e.target.closest('.tt-tab');
      if (!btn) return;
      e.preventDefault();
      switchSpecTab(btn.getAttribute('data-tab-cat') || 'tab-all');
    });
  }

  /* 3. Live Spec Search - bound via addEventListener, no oninput="" inline handler */
  var searchInput = document.getElementById('tt-spec-search');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      applySpecFilter(activeSpecCategory, (this.value || '').trim().toLowerCase());
    });
  }

})();
