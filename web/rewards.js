"use strict";
// Presentation only. Award values come from saved, account-scoped API receipts.
window.AscendRewards = (() => {
  const remembered = new Map();
  const kinds = new Set(['answer', 'challenge', 'milestone', 'example']);
  let answerToast = null, answerTimeout;
  function element(tag, className, text) {
    const node = document.createElement(tag); node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function svgElement(tag, attributes) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    return node;
  }
  function scene(kind, positive = true) {
    const host = element('span', 'reward-visual'); host.setAttribute('aria-hidden', 'true');
    if (kind === 'answer' || kind === 'example' || !positive) {
      host.append(window.AscendFeedback.mark(positive ? 'success' : 'info'));
      return host;
    }
    const art = svgElement('svg', {viewBox: '0 0 144 132', fill: 'none', class: 'reward-scene'});
    art.append(svgElement('ellipse', {cx: 72, cy: 118, rx: 48, ry: 9, fill: 'var(--reward-ground)'}));
    if (kind === 'milestone') {
      const medal = svgElement('g', {class: 'reward-medal'});
      medal.append(svgElement('path', {d: 'm20 72-7 43 14-6 10 10 8-43', fill: '#9c78dc', stroke: 'var(--reward-ink)', 'stroke-width': 2}), svgElement('circle', {cx: 31, cy: 69, r: 20, fill: '#ffd458', stroke: 'var(--reward-ink)', 'stroke-width': 2}), svgElement('circle', {cx: 31, cy: 69, r: 14, fill: '#ffedb1', stroke: 'var(--reward-ink)', 'stroke-width': 1}), svgElement('path', {d: 'm23 69 5 5 11-12', stroke: 'var(--reward-ink)', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round'}));
      art.append(medal);
    }
    const companion = svgElement('g', {class: 'reward-companion'});
    companion.append(
      svgElement('path', {d: 'M55 99v14m29-14v14M49 114h10m22 0h10', stroke: 'var(--reward-ink)', 'stroke-width': 7, 'stroke-linecap': 'round'}),
      svgElement('rect', {x: 41, y: 37, width: 59, height: 63, rx: 19, fill: 'var(--reward-body)', stroke: 'var(--reward-ink)', 'stroke-width': 2}),
      svgElement('path', {d: 'M71 37V24', stroke: 'var(--reward-ink)', 'stroke-width': 3, 'stroke-linecap': 'round'}),
      svgElement('circle', {cx: 71, cy: 20, r: 5, fill: 'var(--reward-flag)', stroke: 'var(--reward-ink)', 'stroke-width': 2}),
      svgElement('rect', {x: 51, y: 50, width: 39, height: 27, rx: 10, fill: 'var(--reward-ink)'}),
      svgElement('path', {d: 'M61 60v4m19-4v4m-16 5q7 4 13 0', stroke: 'var(--reward-eye)', 'stroke-width': 3, 'stroke-linecap': 'round'}),
      svgElement('path', {d: 'm41 66-9 16 7 8', stroke: 'var(--reward-body)', 'stroke-width': 7, 'stroke-linecap': 'round'}),
      svgElement('path', {d: 'm98 65 10 11 11-13', stroke: 'var(--reward-body)', 'stroke-width': 7, 'stroke-linecap': 'round'})
    );
    art.append(companion);
    const flag = svgElement('g', {class: 'reward-flag'});
    flag.append(
      svgElement('path', {d: 'M118 70V29', stroke: 'var(--reward-ink)', 'stroke-width': 3, 'stroke-linecap': 'round'}),
      svgElement('path', {d: 'M119 29h21l-5 10 5 10h-21z', fill: 'var(--reward-flag)', stroke: 'var(--reward-ink)', 'stroke-width': 1.5}),
      svgElement('path', {d: 'm123 39 4 4 6-8', stroke: 'var(--reward-ink)', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round'})
    );
    art.append(flag);
    for (const [x, y, size] of [[19, 47, 6], [103, 18, 5], [23, 96, 4]]) {
      art.append(svgElement('path', {d: `M${x} ${y-size}l${size/2} ${size/2} ${size/2} ${size/2}-${size/2} ${size/2}-${size/2} ${size/2}-${size/2}-${size/2}-${size/2}-${size/2} ${size/2}-${size/2}z`, fill: 'var(--reward-flag)', stroke: 'var(--reward-ink)', 'stroke-width': 1, class: 'reward-star'}));
    }
    host.append(art); return host;
  }
  function validXp(value) { return Number.isSafeInteger(value) && value >= 0 ? value : null; }
  function practiceText(receipt) {
    if (!receipt) return '';
    if (validXp(receipt.points) > 0) return `+${receipt.points.toLocaleString()} Practice points`;
    return receipt.reason === 'daily-cap' ? 'Practice points limit reached for this day' : 'Practice credit already recorded for this day';
  }
  function decorate(panel, {kind = 'challenge', xp = null, practice = null, evidence = '', receiptId = '', positive = true} = {}) {
    if (!panel || !kinds.has(kind)) return panel;
    panel.dataset.rewardKind = kind;
    panel.dataset.rewardReceipt = receiptId;
    const previous = panel.querySelector(':scope > .reward-visual, :scope > .feedback-mark, :scope > .completion-mark');
    const visual = scene(kind, positive);
    if (previous) previous.replaceWith(visual); else panel.prepend(visual);
    const copy = panel.querySelector('.feedback-copy, .celebration-copy') || panel;
    copy.querySelector(':scope > .reward-receipt')?.remove();
    const receipt = element('div', 'reward-receipt');
    if (practice) receipt.append(element('span', 'reward-practice', practiceText(practice)));
    const points = validXp(xp);
    if (points !== null) {
      const amount = element('span', 'reward-xp', points ? `+${points.toLocaleString()} XP` : 'No XP awarded');
      amount.setAttribute('aria-label', points ? `${points} XP recorded for this result` : 'No XP awarded for this result');
      receipt.append(amount);
      if (points) receipt.append(element('span', 'reward-scope', 'Scored result'));
    }
    if (evidence) receipt.append(element('p', 'reward-evidence', evidence));
    if (receipt.childNodes.length) copy.append(receipt);
    return panel;
  }
  function inlineAnswer(panel, {title = 'Correct.', explanation = '', xp = null, practice = null} = {}) {
    panel.classList.remove('feedback-state', 'feedback-compact');
    panel.classList.add('answer-inline-result'); panel.dataset.feedback = 'success';
    delete panel.dataset.rewardKind; delete panel.dataset.rewardFresh;
    panel.setAttribute('role', 'status'); panel.setAttribute('aria-atomic', 'true');
    const copy = element('div', 'feedback-copy'); copy.append(element('strong', 'answer-inline-title', title));
    const recorded = [];
    if (validXp(xp) !== null) recorded.push(`${xp.toLocaleString()} XP recorded`);
    if (validXp(practice?.points) > 0) recorded.push(`${practice.points.toLocaleString()} Practice points`);
    if (recorded.length) copy.append(element('p', 'answer-inline-scope', recorded.join(' · ')));
    if (explanation) {
      const why = element('details', 'answer-explanation'); why.append(element('summary', '', 'Why this answer?'), element('p', '', explanation)); copy.append(why);
    }
    panel.replaceChildren(copy); return panel;
  }
  function dismissAnswer() {
    clearTimeout(answerTimeout); answerToast?.remove(); answerToast = null;
  }
  function answer({account, receiptId, title = 'Correct answer', message = 'Your result is saved.', xp = null, practice = null} = {}) {
    if (!claim(account, receiptId)) return null;
    // The inline receipt remains available if the page is hidden or an error
    // needs attention. A success toast must never replace an unresolved error.
    if (document.hidden || document.querySelector('#notice[data-kind="error"]:not([hidden])')) return null;
    dismissAnswer();
    const toast = element('section', 'answer-reward-toast'); toast.setAttribute('role', 'status'); toast.setAttribute('aria-live', 'polite'); toast.setAttribute('aria-atomic', 'true');
    const copy = element('div', 'feedback-copy'); copy.append(element('strong', 'answer-toast-title', title));
    if (message) copy.append(element('p', 'answer-toast-detail', message));
    const previousFocus = document.activeElement;
    const close = element('button', 'answer-toast-close', '×'); close.type = 'button'; close.setAttribute('aria-label', 'Dismiss answer feedback'); close.addEventListener('click', () => {
      dismissAnswer();
      if (previousFocus?.isConnected && !previousFocus.disabled) previousFocus.focus({preventScroll: true});
    });
    toast.append(copy, close);
    decorate(toast, {kind: 'answer', xp: validXp(xp) > 0 ? xp : null, practice: validXp(practice?.points) > 0 ? practice : null, receiptId});
    document.body.append(toast); answerToast = toast;
    window.AscendMotion?.feedback?.(toast, 'reward-answer');
    const retire = () => { clearTimeout(answerTimeout); answerTimeout = setTimeout(dismissAnswer, 8000); };
    toast.addEventListener('mouseenter', () => clearTimeout(answerTimeout)); toast.addEventListener('focusin', () => clearTimeout(answerTimeout));
    toast.addEventListener('mouseleave', retire); toast.addEventListener('focusout', retire); retire();
    return toast;
  }
  function medal() {
    const art = svgElement('svg', {viewBox: '0 0 48 58', fill: 'none', 'aria-hidden': 'true', class: 'earned-medal'});
    art.append(svgElement('path', {d: 'm12 30-6 24 12-5 6 7 6-26', fill: '#9c78dc', stroke: 'currentColor', 'stroke-width': 1.5}), svgElement('path', {d: 'm26 29 8 25 5-7 7 2-7-23', fill: '#f4a17a', stroke: 'currentColor', 'stroke-width': 1.5}), svgElement('circle', {cx: 24, cy: 23, r: 20, fill: '#ffd458', stroke: 'currentColor', 'stroke-width': 1.5}), svgElement('circle', {cx: 24, cy: 23, r: 14, fill: '#ffedb1', stroke: 'currentColor', 'stroke-width': 1}), svgElement('path', {d: 'm16 23 5 5 11-12', stroke: 'currentColor', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round'}));
    return art;
  }
  function overview(data) {
    if (!data?.practice || !data?.milestones) return null;
    const section = element('section', 'rewards-overview'); section.setAttribute('aria-label', 'Your rewards');
    section.append(element('h2', '', 'Three ways your work adds up'));
    const cards = element('div', 'rewards-wallet');
    for (const [kind, amount, title, description] of [
      ['practice', data.practice.total, 'Practice points', `${data.practice.today} of ${data.practice.daily_cap} earned today · effort and reflection`],
      ['xp', data.xp.total, 'XP', 'Scored results from practice and assessments'],
      ['milestone', data.milestones.total, 'Milestones', 'Completed track stages, with their evidence']
    ]) {
      const card = element('div', `reward-balance reward-balance-${kind}`);
      card.append(element('strong', '', amount.toLocaleString()), element('h3', '', title), element('p', '', description)); cards.append(card);
    }
    section.append(cards, element('p', 'reward-rules', `${data.practice.per_activity} Practice points per distinct activity per learning day, up to ${data.practice.daily_cap}. Finish an example, submit a complete answer, or explicitly save a reflection of at least 20 characters. Autosaves, opening a task and replaying an animation add no points. Points do not buy access or prove skill.`));
    const history = element('details', 'reward-history'); history.append(element('summary', '', 'Practice points history'));
    if (!data.recent.length) history.append(element('p', '', 'Your first recorded practice reward will appear here.'));
    else {
      const list = element('ol', 'reward-ledger');
      for (const item of data.recent) {
        const row = element('li', ''); row.append(element('span', '', item.title), element('small', '', item.day), element('strong', '', item.points ? `+${item.points}` : item.reason === 'daily-cap' ? 'Daily limit' : 'Already counted')); list.append(row);
      }
      history.append(list);
    }
    section.append(history); return section;
  }
  function claim(account, receiptId) {
    if (!account || !receiptId) return false;
    const key = `ascend-rewards-seen:${encodeURIComponent(account)}`;
    const seen = remembered.get(account) || new Set();
    try {
      const stored = JSON.parse(localStorage.getItem(key) || '[]');
      if (Array.isArray(stored)) for (const id of stored) if (typeof id === 'string') seen.add(id);
    } catch { /* The current tab still deduplicates when storage is unavailable. */ }
    remembered.set(account, seen);
    if (seen.has(receiptId)) return false;
    seen.add(receiptId);
    try { localStorage.setItem(key, JSON.stringify([...seen])); } catch { /* No learning data or XP is stored here. */ }
    return true;
  }
  function play(panel, {account, receiptId, kind = panel?.dataset.rewardKind} = {}) {
    if (!panel?.isConnected || !kinds.has(kind) || !claim(account, receiptId)) return false;
    panel.dataset.rewardFresh = 'true';
    window.AscendMotion?.feedback?.(panel, `reward-${kind}`);
    return true;
  }
  function replay(panel) {
    // An explicit viewing action: no network request, award, or display counter.
    if (panel?.isConnected && kinds.has(panel.dataset.rewardKind)) window.AscendMotion?.feedback?.(panel, `reward-${panel.dataset.rewardKind}`);
  }
  function addReplay(panel, host) {
    if (!panel || !host || host.querySelector('.reward-replay')) return;
    const action = element('button', 'text-button reward-replay', 'Replay celebration'); action.type = 'button';
    action.setAttribute('aria-label', 'Replay celebration; recorded XP stays the same');
    action.addEventListener('click', () => replay(panel)); host.append(action);
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) dismissAnswer(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') dismissAnswer(); });
  window.addEventListener('hashchange', dismissAnswer);
  return {decorate, play, replay, addReplay, overview, medal, practiceText, inlineAnswer, answer, dismissAnswer};
})();
