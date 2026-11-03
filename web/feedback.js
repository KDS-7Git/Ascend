"use strict";
// Shared outcome treatment. Restoring a saved result never replays its motion.
window.AscendFeedback = (() => {
  const labels = {success: 'Done', complete: 'Complete', error: 'Needs attention', warning: 'Keep going', info: 'Update', start: 'Session started', streak: 'Streak extended', reminder: 'Time check'};
  const kinds = {complete: 'success', streak: 'success', start: 'info', reminder: 'warning'};
  function element(tag, className, text) {
    const node = document.createElement(tag); node.className = className;
    if (text) node.textContent = text;
    return node;
  }
  function mark(kind) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    for (const [key, value] of Object.entries({viewBox: '0 0 48 48', fill: 'none', 'aria-hidden': 'true', class: 'feedback-mark'})) svg.setAttribute(key, value);
    const add = (tag, attrs) => {
      const item = document.createElementNS(svg.namespaceURI, tag);
      for (const [key, value] of Object.entries(attrs)) item.setAttribute(key, value);
      svg.append(item);
    };
    add('circle', {cx: 24, cy: 24, r: 18, class: 'feedback-mark-ring', pathLength: 1});
    const paths = {success: 'm15 24 6 6 12-13', error: 'm19 19 10 10m0-10L19 29', warning: 'M24 15v12m0 5v1', info: 'M24 33V22m0-7v1'};
    add('path', {d: paths[kinds[kind] || kind] || paths.info, class: 'feedback-mark-stroke', pathLength: 1});
    return svg;
  }
  function paint(node, kind) {
    node.dataset.feedback = kinds[kind] || kind;
    node.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    node.setAttribute('aria-atomic', 'true');
  }
  function set(node, {kind = 'info', title, message, label, compact = false}) {
    node.classList.add('feedback-state'); node.classList.toggle('feedback-compact', compact); paint(node, kind);
    const copy = element('div', 'feedback-copy');
    if (label) copy.append(element('p', 'eyebrow', label));
    copy.append(element(compact ? 'strong' : 'h2', 'feedback-title', title || labels[kind]));
    if (message) copy.append(element('p', 'feedback-detail', message));
    node.replaceChildren(mark(kind), copy);
    return node;
  }
  function create(options) { return set(element('section', ''), options); }
  function notice(node, {kind = 'info', title, event} = {}) {
    paint(node, kind);
    const copy = node.querySelector('.notice-message'), message = copy.textContent;
    copy.replaceChildren(element('strong', 'notice-title', title || labels[kind]), element('span', 'notice-detail', message));
    node.querySelector('.notice-symbol').replaceChildren(mark(kind));
    window.AscendMotion?.feedback?.(node, event || kind);
  }
  return {create, set, mark, notice};
})();
