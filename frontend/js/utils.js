/**
 * utils.js — Shared frontend utilities.
 * Loaded before auth.js and analytics.js in every HTML page.
 * Eliminates duplicate definitions of formatCurrency, formatDate, animateCounter.
 */

// ── Format Indian Currency ────────────────────────────────────────────
function formatCurrency(amount) {
    if (amount === undefined || amount === null) return '₹0.00';
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 2}).format(amount);
}

// ── Format Date ───────────────────────────────────────────────────────
function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        if (isNaN(date)) return dateString;
        return date.toLocaleDateString('en-IN', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'});
    } catch (e) {
        return dateString;
    }
}

// ── Counter Animation ─────────────────────────────────────────────────
function animateCounter(el, target) {
    const duration = 1500;
    const start = performance.now();

    const update = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const value = Math.floor(progress * target);

        if (el.dataset.type === 'currency') {
            el.textContent = formatCurrency(value);
        } else {
            el.textContent = value;
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            el.textContent = el.dataset.type === 'currency'
                ? formatCurrency(target)
                : target;
        }
    };

    requestAnimationFrame(update);
}

// ── Animate currency counter by element ID ────────────────────────────
function animateCounterValue(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    el.dataset.type = 'currency';
    animateCounter(el, target);
}
