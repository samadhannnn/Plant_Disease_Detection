// ============================================
// FIXED JAVASCRIPT WITH OPENCV CAMERA
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupParticleCanvas();
    setupMethodSelector();
    setupFileUpload();
    setupCamera();
    setupAnimations();
}

// ============================================
// PARTICLE CANVAS ANIMATION
// ============================================
function setupParticleCanvas() {
    const canvas = document.getElementById('particleCanvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const particles = [];
    const particleCount = 50;
    
    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 3 + 1;
            this.speedX = Math.random() * 2 - 1;
            this.speedY = Math.random() * 2 - 1;
            this.opacity = Math.random() * 0.5 + 0.2;
            this.color = Math.random() > 0.5 ? '#00ff88' : '#00d4ff';
        }
        
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            
            if (this.x > canvas.width) this.x = 0;
            if (this.x < 0) this.x = canvas.width;
            if (this.y > canvas.height) this.y = 0;
            if (this.y < 0) this.y = canvas.height;
        }
        
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = this.color;
            ctx.globalAlpha = this.opacity;
            ctx.fill();
            
            // Draw connections
            particles.forEach(particle => {
                const dx = this.x - particle.x;
                const dy = this.y - particle.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < 150) {
                    ctx.beginPath();
                    ctx.moveTo(this.x, this.y);
                    ctx.lineTo(particle.x, particle.y);
                    ctx.strokeStyle = this.color;
                    ctx.globalAlpha = (150 - distance) / 150 * 0.2;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            });
        }
    }
    
    for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(particle => {
            particle.update();
            particle.draw();
        });
        requestAnimationFrame(animate);
    }
    
    animate();
    
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

// ============================================
// METHOD SELECTOR
// ============================================
function setupMethodSelector() {
    const methodBtns = document.querySelectorAll('.method-btn');
    const methodContents = document.querySelectorAll('.method-content');
    
    methodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const method = btn.dataset.method;
            
            // Update buttons
            methodBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Update content
            methodContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${method}Method`) {
                    content.classList.add('active');
                }
            });
            
            // Stop camera if switching away
            if (method !== 'camera' && cameraActive) {
                stopCamera();
            }
        });
    });
}

// ============================================
// FILE UPLOAD
// ============================================
function setupFileUpload() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const uploadForm = document.getElementById('uploadForm');
    const uploadSubmit = document.getElementById('uploadSubmit');
    
    if (!uploadZone || !fileInput) return;
    
    // Drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
            uploadZone.classList.add('dragover');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
            uploadZone.classList.remove('dragover');
        });
    });
    
    uploadZone.addEventListener('drop', handleDrop);
    
    fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0]);
    });
    
    uploadForm.addEventListener('submit', (e) => {
        if (!fileInput.files.length) {
            e.preventDefault();
            showNotification('Please select an image file', 'error');
            return false;
        }
        
        uploadSubmit.classList.add('loading');
        uploadSubmit.disabled = true;
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
        document.getElementById('fileInput').files = files;
        handleFileSelect(files[0]);
    }
}

function handleFileSelect(file) {
    if (!file) return;
    
    const filePreview = document.getElementById('filePreview');
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    if (file.size > maxSize) {
        showNotification('File size exceeds 10MB', 'error');
        return;
    }
    
    if (!file.type.startsWith('image/')) {
        showNotification('Please select a valid image file', 'error');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
        filePreview.innerHTML = `
            <div style="display: flex; align-items: center; gap: 1rem;">
                <i class="fas fa-check-circle" style="color: #00ff88; font-size: 1.5rem;"></i>
                <div>
                    <strong>${file.name}</strong>
                    <p style="margin: 0; color: #a0a0b0;">${formatFileSize(file.size)}</p>
                </div>
            </div>
        `;
        filePreview.classList.add('show');
    };
    reader.readAsDataURL(file);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ============================================
// OPENCV CAMERA FUNCTIONALITY (SERVER-SIDE)
// ============================================
let cameraActive = false;
let videoFeedImg = null;

function setupCamera() {
    const startBtn = document.getElementById('startCameraBtn');
    const captureBtn = document.getElementById('captureBtn');
    const closeBtn = document.getElementById('closeCameraBtn');
    const retakeBtn = document.getElementById('retakeBtn');
    const analyzeBtn = document.getElementById('analyzeCameraBtn');
    
    if (startBtn) {
        startBtn.addEventListener('click', startCamera);
    }
    
    if (captureBtn) {
        captureBtn.addEventListener('click', captureImage);
    }
    
    if (closeBtn) {
        closeBtn.addEventListener('click', stopCamera);
    }
    
    if (retakeBtn) {
        retakeBtn.addEventListener('click', retakePhoto);
    }
    
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeCapturedImage);
    }
}

async function startCamera() {
    const container = document.getElementById('cameraContainer');
    const placeholder = document.getElementById('cameraPlaceholder');
    const startBtn = document.getElementById('startCameraBtn');
    
    // Disable button
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';
    }
    
    try {
        showNotification('Initializing camera...', 'info');
        
        // Start camera on server
        const response = await fetch('/start_camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ camera_index: 1 }) // Use index 1 for Mac
        });
        
        const data = await response.json();
        console.log('Camera start response:', data);
        
        if (data && data.status === 'success') {
            // Wait a moment for server to be ready
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // Create or get video feed image element
            let videoFeed = document.getElementById('opencv-video-feed');
            if (!videoFeed) {
                // Create img element for video feed
                videoFeed = document.createElement('img');
                videoFeed.id = 'opencv-video-feed';
                videoFeed.style.width = '100%';
                videoFeed.style.height = 'auto';
                videoFeed.style.borderRadius = '12px';
                
                // Insert into camera container (replace video element)
                const videoElement = document.getElementById('videoElement');
                if (videoElement && videoElement.parentNode) {
                    videoElement.parentNode.replaceChild(videoFeed, videoElement);
                } else {
                    container.appendChild(videoFeed);
                }
            }
            
            // Set video source with cache busting
            videoFeed.src = '/video_feed?t=' + new Date().getTime();
            videoFeed.onerror = function() {
                console.error('Video feed error');
                showNotification('Video feed error. Retrying...', 'error');
                // Retry after a moment
                setTimeout(() => {
                    videoFeed.src = '/video_feed?t=' + new Date().getTime();
                }, 1000);
            };
            
            videoFeedImg = videoFeed;
            cameraActive = true;
            
            placeholder.style.display = 'none';
            container.classList.add('active');
            
            showNotification('Camera started successfully! 📸', 'success');
            
            if (startBtn) {
                startBtn.disabled = false;
                startBtn.innerHTML = '<i class="fas fa-play"></i> <span>Start Camera</span>';
            }
        } else {
            throw new Error(data.message || 'Failed to start camera');
        }
    } catch (error) {
        console.error('Error starting camera:', error);
        showNotification('Unable to start camera: ' + error.message, 'error');
        
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.innerHTML = '<i class="fas fa-play"></i> <span>Start Camera</span>';
        }
    }
}

async function stopCamera() {
    if (!cameraActive) return;
    
    try {
        // Stop video feed
        if (videoFeedImg) {
            videoFeedImg.src = '';
        }
        
        // Stop camera on server
        await fetch('/stop_camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        cameraActive = false;
        
        const container = document.getElementById('cameraContainer');
        const placeholder = document.getElementById('cameraPlaceholder');
        const preview = document.getElementById('cameraPreview');
        
        if (container) container.classList.remove('active');
        if (placeholder) placeholder.style.display = 'block';
        if (preview) preview.style.display = 'none';
        
        showNotification('Camera stopped', 'info');
    } catch (error) {
        console.error('Error stopping camera:', error);
    }
}

async function captureImage() {
    if (!cameraActive) {
        showNotification('Please start the camera first', 'error');
        return;
    }
    
    try {
        showNotification('Capturing image...', 'info');
        
        // Capture frame on server
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/capture_frame';
        document.body.appendChild(form);
        form.submit();
        
    } catch (error) {
        console.error('Error capturing image:', error);
        showNotification('Failed to capture image: ' + error.message, 'error');
    }
}

function retakePhoto() {
    const preview = document.getElementById('cameraPreview');
    const container = document.getElementById('cameraContainer');
    
    if (preview) preview.style.display = 'none';
    if (container) container.classList.add('active');
}

async function analyzeCapturedImage() {
    // This will be called if using client-side capture
    // For server-side OpenCV, just submit the form
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/capture_frame';
    document.body.appendChild(form);
    form.submit();
}

// ============================================
// ANIMATIONS
// ============================================
function setupAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.upload-card, .camera-card, .result-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function showNotification(message, type = 'info') {
    // Remove any existing notifications
    const existing = document.querySelectorAll('.notification-toast');
    existing.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification-toast ${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        padding: 1rem 1.5rem;
        background: ${type === 'error' ? '#ff4444' : type === 'success' ? '#00ff88' : '#00d4ff'};
        color: ${type === 'success' || type === 'info' ? '#0a0a1a' : '#fff'};
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        gap: 1rem;
        animation: slideInRight 0.3s ease-out;
        font-weight: 600;
    `;
    
    const icon = type === 'error' ? 'fa-exclamation-circle' : 
                 type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
    notification.innerHTML = `
        <i class="fas ${icon}" style="font-size: 1.5rem;"></i>
        <p style="margin: 0;">${message}</p>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

function closeResults() {
    window.location.href = '/';
}

function analyzeAgain() {
    window.location.href = '/';
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (cameraActive) {
        navigator.sendBeacon('/stop_camera');
    }
});