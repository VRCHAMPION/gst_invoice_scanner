// Custom cursor
const cursor = document.getElementById('cursor');
const ring = document.getElementById('cursor-ring');
let mx = 0, my = 0, rx = 0, ry = 0;

document.addEventListener('mousemove', e => {
    mx = e.clientX; my = e.clientY;
    cursor.style.left = mx + 'px';
    cursor.style.top = my + 'px';
});

function animRing() {
    rx += (mx - rx) * 0.12;
    ry += (my - ry) * 0.12;
    ring.style.left = rx + 'px';
    ring.style.top = ry + 'px';
    requestAnimationFrame(animRing);
}
animRing();

document.querySelectorAll('a, button, .feat-card, .grade-pill, .check-row').forEach(el => {
    el.addEventListener('mouseenter', () => {
        cursor.style.width = '20px';
        cursor.style.height = '20px';
        ring.style.width = '52px';
        ring.style.height = '52px';
        ring.style.opacity = '0.8';
    });
    el.addEventListener('mouseleave', () => {
        cursor.style.width = '12px';
        cursor.style.height = '12px';
        ring.style.width = '36px';
        ring.style.height = '36px';
        ring.style.opacity = '0.5';
    });
});

const reveals = document.querySelectorAll('.reveal');
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.12 });
reveals.forEach(el => observer.observe(el));

function animateCounter(el, end, suffix = '') {
    let start = 0;
    const duration = 1800;
    const step = (timestamp) => {
        if (!start) start = timestamp;
        const progress = Math.min((timestamp - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * end) + suffix;
        if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

document.addEventListener('mousemove', e => {
    const x = (e.clientX / window.innerWidth - 0.5) * 30;
    const y = (e.clientY / window.innerHeight - 0.5) * 30;
    const blobs = document.querySelectorAll('.hero-blob, .hero-blob2');
    blobs[0] && (blobs[0].style.transform = `translate(${x * 0.5}px, ${y * 0.5}px)`);
    blobs[1] && (blobs[1].style.transform = `translate(${-x * 0.3}px, ${-y * 0.3}px)`);
});

document.querySelectorAll('.main-card').forEach(card => {
    card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `perspective(800px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) translateY(-6px)`;
    });
    card.addEventListener('mouseleave', () => {
        card.style.transform = '';
        card.style.transition = 'transform 0.5s ease';
    });
});

document.querySelectorAll('.feat-card').forEach(card => {
    card.addEventListener('click', e => {
        const ripple = document.createElement('span');
        const rect = card.getBoundingClientRect();
        ripple.style.cssText = `
            position:absolute;
            left:${e.clientX - rect.left}px;
            top:${e.clientY - rect.top}px;
            width:0; height:0;
            background: rgba(0,71,255,0.1);
            border-radius:50%;
            transform:translate(-50%,-50%);
            animation: rippleOut 0.6s ease-out forwards;
            pointer-events:none;
        `;
        card.appendChild(ripple);
        setTimeout(() => ripple.remove(), 700);
    });
});

// Ripple keyframe
const rippleStyle = document.createElement('style');
rippleStyle.textContent = '@keyframes rippleOut { to { width: 300px; height: 300px; opacity: 0; } }';
document.head.appendChild(rippleStyle);
