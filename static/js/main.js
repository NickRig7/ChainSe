let currentCategory = 'daily-news';

async function loadNews(category = 'daily-news') {
  currentCategory = category;
  const container = document.getElementById('news-container');
  container.innerHTML = '';

  const res = await fetch(`/news?category=${category}`);
  let articles = await res.json();

  const removed = JSON.parse(sessionStorage.getItem(`removed-${category}`)) || [];
  articles = articles.filter(article => !removed.includes(article.link));

  sessionStorage.setItem(`news-${category}`, JSON.stringify(articles));

  renderArticles(articles);
}

/*function renderArticles(articles) {
  const container = document.getElementById('news-container');

  // Hide intro text when cards load seo
  const introText = document.getElementById('intro-text');
  if (introText) {
    introText.style.display = 'none';
  }

  container.innerHTML = '';

  if (!articles.length) {
    container.innerHTML = '<div style="color:#ccc;padding:1rem;">No more news in this category.</div>';
    return;
  }

  articles.forEach((article, index) => {
    const card = document.createElement('div');
    card.className = 'card';

    /*const swipeHintHTML = (index === articles.length - 1) //swipe hint on last card even appears if the category is changed
      ? `<div class="swipe-hint">⇽ Swipe to explore ⇾</div>` : ''; 

    let swipeShown = sessionStorage.getItem(`swipe-shown-${currentCategory}`);
    const swipeHintHTML = (index === articles.length - 1 && !swipeShown)
      ? `<div class="swipe-hint">⇽ Swipe to explore ⇾</div>` : '';

    if (!swipeShown) {
      sessionStorage.setItem(`swipe-shown-${currentCategory}`, 'true');
    }

    card.innerHTML = `
      <img src="${article.image_url || 'https://via.placeholder.com/400x200'}" alt="${article.title}" />
      <div class="card-content">
        <h2 class="title">${article.title}</h2>
        <div class="summary">${article.summary}</div>
        ${swipeHintHTML}
        <div class="read-more">
          <a href="${article.link}" target="_blank">Read more</a>
        </div>
      </div>
      
      <button class="share-btn" data-link="${article.link}" data-title="${article.title}">
        <img src="/static/sharee.png" alt="Share" />
      </button>
    `;
    container.appendChild(card);
  });

  initSwipe();
}*/

function renderArticles(articles) {
  const container = document.getElementById('news-container');

  // Hide intro text when cards load (SEO)
  const introText = document.getElementById('intro-text');
  if (introText) introText.style.display = 'none';

  container.innerHTML = '';

  if (!articles.length) {
    container.innerHTML = '<div style="color:#ccc;padding:1rem;">No more news in this category.</div>';
    return;
  }

  // ✅ Only check and set once, outside the loop
  const swipeShown = sessionStorage.getItem(`swipe-shown-${currentCategory}`);
  const showHint = !swipeShown;
  if (showHint) {
    sessionStorage.setItem(`swipe-shown-${currentCategory}`, 'true');
  }

  articles.forEach((article, index) => {
    const card = document.createElement('div');
    card.className = 'card';

    const swipeHintHTML = (index === articles.length - 1 && showHint)
      ? `<div class="swipe-hint">⇽ Swipe to explore ⇾</div>` : '';

    card.innerHTML = `
      <img src="${article.image_url || 'https://via.placeholder.com/400x200'}" alt="${article.title}" />
      <div class="card-content">
        <h2 class="title">${article.title}</h2>
        <div class="summary">${article.summary}</div>
        ${swipeHintHTML}
        <div class="read-more">
          <a href="${article.link}" target="_blank">Read more</a>
        </div>
      </div>
      
      <button class="share-btn" data-link="${article.link}" data-title="${article.title}">
        <img src="/static/sharee.png" alt="Share" />
      </button>
    `;
    container.appendChild(card);
  });

  initSwipe();
}

function initSwipe() {
  const cards = document.querySelectorAll('.card');
  let topCard = cards[cards.length - 1];
  if (!topCard) return;

  topCard.addEventListener('mousedown', startDrag);
  topCard.addEventListener('touchstart', startDrag);

  let isDragging = false;
  let startX, currentX;

  function startDrag(e) {
    isDragging = true;
    currentX = undefined;
    startX = e.type === 'mousedown' ? e.clientX : e.touches[0].clientX;
    topCard.classList.add('swiping');
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('mouseup', endDrag);
    document.addEventListener('touchmove', onDrag);
    document.addEventListener('touchend', endDrag);
  }

  function onDrag(e) {
    if (!isDragging) return;
    currentX = e.type.includes('mouse') ? e.clientX : e.touches[0].clientX;
    const deltaX = currentX - startX;
    topCard.style.transform = `translateX(${deltaX}px) rotate(${deltaX / 10}deg)`;
  }

  function endDrag() {
    isDragging = false;
    topCard.classList.remove('swiping');
    const threshold = window.innerWidth < 480 ? 60 : 100;
    const deltaX = currentX !== undefined ? currentX - startX : 0;

    if (Math.abs(deltaX) > threshold) {
      topCard.style.transition = 'transform 0.4s ease, opacity 0.4s ease';
      topCard.style.transform = `translateX(${deltaX > 0 ? 1000 : -1000}px) rotate(${deltaX > 0 ? 20 : -20}deg)`;
      topCard.style.opacity = '0';

      setTimeout(() => {
        const link = topCard.querySelector('.read-more a').href;
        topCard.remove();

        const removedKey = `removed-${currentCategory}`;
        let removed = JSON.parse(sessionStorage.getItem(removedKey)) || [];
        removed.push(link);
        sessionStorage.setItem(removedKey, JSON.stringify(removed));

        const cached = JSON.parse(sessionStorage.getItem(`news-${currentCategory}`)) || [];
        const updated = cached.filter(article => article.link !== link);
        sessionStorage.setItem(`news-${currentCategory}`, JSON.stringify(updated));

        const newCards = document.querySelectorAll('.card');
        topCard = newCards[newCards.length - 1];

        if (topCard) {
          requestAnimationFrame(() => {
            topCard.addEventListener('mousedown', startDrag);
            topCard.addEventListener('touchstart', startDrag);
          });
        } else {
          setTimeout(() => {
            sessionStorage.removeItem(`removed-${currentCategory}`);
            loadNews(currentCategory);
          }, 300);
        }
      }, 400);
    } else {
      topCard.style.transition = 'transform 0.3s ease';
      topCard.style.transform = 'translateX(0px) rotate(0deg)';
    }

    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('mouseup', endDrag);
    document.removeEventListener('touchmove', onDrag);
    document.removeEventListener('touchend', endDrag);
  }
}

async function getShortLink(longUrl) {
  try {
    const res = await fetch(`https://tinyurl.com/api-create.php?url=${encodeURIComponent(longUrl)}`);
    return await res.text();
  } catch (error) {
    console.error('Shortening failed, using original URL:', error);
    return longUrl;
  }
}

document.addEventListener('click', async (e) => {
  const btn = e.target.closest('.share-btn');
  if (btn) {
    e.stopPropagation();
    const link = btn.getAttribute('data-link');
    const title = btn.getAttribute('data-title') || '';

    const shortLink = await getShortLink(link);

    const chainshotsUrl = "https://chainapp.onrender.com";
    const shareText = `${title}\n\nRead full article: ${shortLink}\n\nMore on [ChainShots]\n${chainshotsUrl}`;

    const shareData = {
      title: title,
      text: shareText,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch (err) {
        console.error('Share failed:', err);
      }
    } else {
      alert('Sharing not supported on this device.');
    }
  }
});

// Category Buttons
document.querySelectorAll('.category-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const selectedCategory = btn.getAttribute('data-category');
    loadNews(selectedCategory);
  });
});

// Clear sessionStorage on reload
const navType = performance.getEntriesByType("navigation")[0]?.type || performance.navigation.type;
if (navType === "reload") {
  Object.keys(sessionStorage)
    .filter(key => key.startsWith('news-') || key.startsWith('removed-'))
    .forEach(key => sessionStorage.removeItem(key));
}

loadNews();

// Hamburger Side Menu Toggle
const hamburger = document.querySelector('.hamburger-menu');
const sideMenu = document.getElementById('sideMenu');

hamburger.addEventListener('click', () => {
  sideMenu.classList.toggle('open');
});

document.addEventListener('click', (e) => {
  if (!sideMenu.contains(e.target) && !hamburger.contains(e.target)) {
    sideMenu.classList.remove('open');
  }
});

// Layout Height Fix for Mobile
function adjustLayoutHeight() {
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
  const mainContainer = document.querySelector('.main-container');
  const sideMenu = document.getElementById('sideMenu');

  if (!isStandalone) {
    const availableHeight = window.innerHeight;
    mainContainer.style.height = `${availableHeight}px`;
    sideMenu.style.height = `${availableHeight}px`;
  } else {
    mainContainer.style.height = '';
    sideMenu.style.height = '';
  }
}

window.addEventListener('load', adjustLayoutHeight);
window.addEventListener('resize', adjustLayoutHeight);
