document.addEventListener('DOMContentLoaded', () => {
    // Inject cursor elements if they don't exist
    if (!document.getElementById('cursor')) {
        const c = document.createElement('div');
        c.id = 'cursor';
        document.body.appendChild(c);
    }
    if (!document.getElementById('cursor-ring')) {
        const cr = document.createElement('div');
        cr.id = 'cursor-ring';
        document.body.appendChild(cr);
    }

    const cursor = document.getElementById('cursor');
    const ring = document.getElementById('cursor-ring');
    let mx = 0, my = 0, rx = 0, ry = 0;

    document.addEventListener('mousemove', e => {
        mx = e.clientX; 
        my = e.clientY;
        cursor.style.left = mx + 'px';
        cursor.style.top = my + 'px';
    });

    // Ring follows with lag
    function animRing() {
        rx += (mx - rx) * 0.12;
        ry += (my - ry) * 0.12;
        ring.style.left = rx + 'px';
        ring.style.top = ry + 'px';
        requestAnimationFrame(animRing);
    }
    animRing();

    // Cursor expand on hover
    function bindHover() {
        const targets = document.querySelectorAll('a, button, input, select, .drop-zone, th, .card, .stat-card, .grade-pill, .check-row');
        targets.forEach(el => {
            // avoid rebinding if already bound
            if(el.dataset.cursorBound) return;
            el.dataset.cursorBound = "true";

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
    }

    bindHover();
    
    // Allow re-binding if dynamic content is loaded (e.g. results tables)
    window.bindCursorHover = bindHover;
});
