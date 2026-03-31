// ScrapMetalJr Jeeps - Main Script

document.addEventListener('DOMContentLoaded', function() {
  initLightbox();
  initSmoothScroll();
  initNavActive();
});

// ===== Lightbox =====
function initLightbox() {
  // Create lightbox overlay
  const overlay = document.createElement('div');
  overlay.className = 'lightbox-overlay';
  overlay.innerHTML = `
    <button class="lightbox-close" aria-label="Close">&times;</button>
    <button class="lightbox-prev" aria-label="Previous">&#8249;</button>
    <button class="lightbox-next" aria-label="Next">&#8250;</button>
    <img src="" alt="Full size photo">
    <div class="lightbox-counter"></div>
  `;
  document.body.appendChild(overlay);

  const img = overlay.querySelector('img');
  const counter = overlay.querySelector('.lightbox-counter');
  const closeBtn = overlay.querySelector('.lightbox-close');
  const prevBtn = overlay.querySelector('.lightbox-prev');
  const nextBtn = overlay.querySelector('.lightbox-next');

  let photos = [];
  let currentIndex = 0;

  function openLightbox(photoArray, index) {
    photos = photoArray;
    currentIndex = index;
    updateLightbox();
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  function updateLightbox() {
    if (photos.length === 0) return;
    img.src = photos[currentIndex];
    counter.textContent = `${currentIndex + 1} / ${photos.length}`;
    prevBtn.style.display = photos.length > 1 ? 'block' : 'none';
    nextBtn.style.display = photos.length > 1 ? 'block' : 'none';
  }

  function nextPhoto() {
    currentIndex = (currentIndex + 1) % photos.length;
    updateLightbox();
  }

  function prevPhoto() {
    currentIndex = (currentIndex - 1 + photos.length) % photos.length;
    updateLightbox();
  }

  closeBtn.addEventListener('click', closeLightbox);
  nextBtn.addEventListener('click', nextPhoto);
  prevBtn.addEventListener('click', prevPhoto);

  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) closeLightbox();
  });

  document.addEventListener('keydown', function(e) {
    if (!overlay.classList.contains('active')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowRight') nextPhoto();
    if (e.key === 'ArrowLeft') prevPhoto();
  });

  // Attach to gallery grid photos
  document.addEventListener('click', function(e) {
    const photoItem = e.target.closest('.photo-item, .gallery-grid img, .lightbox-trigger');
    if (photoItem) {
      const container = photoItem.closest('.gallery-grid, .photo-strip, #featured-gallery');
      if (!container) return;

      const allImgs = container.querySelectorAll('img');
      const photoArray = Array.from(allImgs).map(i => i.src);
      const idx = Array.from(allImgs).indexOf(photoItem.tagName === 'IMG' ? photoItem : photoItem.querySelector('img'));
      if (idx >= 0) openLightbox(photoArray, idx);
    }
  });

  // Expose for programmatic use
  window.openLightbox = openLightbox;
}

// ===== Smooth Scroll =====
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

// ===== Active Nav Highlight =====
function initNavActive() {
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
    const href = link.getAttribute('href');
    link.classList.remove('active');
    if (href === currentPage) {
      link.classList.add('active');
    }
  });
}

// ===== Gallery Grid Builder =====
function buildGalleryGrid(containerId, photos) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';
  container.className = 'gallery-grid';

  photos.forEach((src, idx) => {
    const item = document.createElement('div');
    item.className = 'photo-item';
    item.innerHTML = `<img src="${src}" alt="Photo ${idx + 1}" loading="lazy">`;
    container.appendChild(item);
  });
}

// ===== Lazy Load with Intersection Observer =====
if ('IntersectionObserver' in window) {
  const imgObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        if (img.dataset.src) {
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
        }
        imgObserver.unobserve(img);
      }
    });
  }, { rootMargin: '200px' });

  document.querySelectorAll('img[data-src]').forEach(img => {
    imgObserver.observe(img);
  });
}
