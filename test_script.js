
    function toggleChatWindow() {
        const win = document.getElementById('floating-chat-window');
        if (win.classList.contains('hidden')) {
            win.classList.remove('hidden');
            setTimeout(() => {
                win.classList.remove('scale-95', 'opacity-0');
                win.classList.add('scale-100', 'opacity-100');
            }, 10);
            document.getElementById('chat-input').focus();
        } else {
            win.classList.remove('scale-100', 'opacity-100');
            win.classList.add('scale-95', 'opacity-0');
            setTimeout(() => {
                win.classList.add('hidden');
            }, 300);
        }
    }
    
    // Draggable Logic
    const header = document.getElementById('floating-chat-header');
    const widget = document.getElementById('floating-chat-widget');
    let isDragging = false;
    let offsetX, offsetY;
    
    header.addEventListener('mousedown', (e) => {
        isDragging = true;
        const rect = widget.getBoundingClientRect();
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;
        widget.style.bottom = 'auto';
        widget.style.right = 'auto';
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        widget.style.left = (e.clientX - offsetX) + 'px';
        widget.style.top = (e.clientY - offsetY) + 'px';
    });
    
    document.addEventListener('mouseup', () => {
        isDragging = false;
    });
