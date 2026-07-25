/**
 * URL Auditor — Client-side logic.
 * 
 * Handles form submission, loading states, error display,
 * and result rendering. No framework — plain JS.
 */

(function () {
  'use strict';

  // DOM elements
  const form = document.getElementById('audit-form');
  const urlInput = document.getElementById('url-input');
  const submitBtn = document.getElementById('submit-btn');
  const btnText = document.getElementById('btn-text');
  const spinner = document.getElementById('spinner');
  const errorBanner = document.getElementById('error-banner');
  const errorText = document.getElementById('error-text');
  const results = document.getElementById('results');

  // Result elements
  const resultUrl = document.getElementById('result-url');
  const resultStatusBadge = document.getElementById('result-status-badge');
  const resultStatus = document.getElementById('result-status');
  const resultTime = document.getElementById('result-time');
  const resultTitle = document.getElementById('result-title');
  const resultMeta = document.getElementById('result-meta');
  const resultH1 = document.getElementById('result-h1');
  const resultWords = document.getElementById('result-words');
  const resultImages = document.getElementById('result-images');
  const resultAlt = document.getElementById('result-alt');
  
  // Social Preview & Actions elements
  const socialSection = document.getElementById('social-preview-section');
  const socialImageContainer = document.getElementById('social-image-container');
  const socialImage = document.getElementById('social-image');
  const socialDomain = document.getElementById('social-domain');
  const socialTitle = document.getElementById('social-title');
  const socialDesc = document.getElementById('social-desc');
  const btnCsv = document.getElementById('btn-export-csv');
  const btnPdf = document.getElementById('btn-export-pdf');

  // State management
  function setLoading(loading) {
    submitBtn.disabled = loading;
    urlInput.disabled = loading;
    spinner.classList.toggle('spinner--visible', loading);
    btnText.textContent = loading ? 'Auditing…' : 'Audit';
  }

  function showError(message) {
    errorText.textContent = message;
    errorBanner.classList.add('error-banner--visible');
    results.classList.remove('results--visible');
  }

  function hideError() {
    errorBanner.classList.remove('error-banner--visible');
  }

  function getTrendBadge(current, previous, invert = false) {
    if (previous === undefined || previous === null) return '';
    const diff = current - previous;
    if (diff === 0) return `<span class="trend trend--neutral">No change</span>`;
    
    let isGood = diff > 0;
    if (invert) isGood = !isGood; // e.g. for errors/missing alt, lower is better
    
    const cls = isGood ? 'trend--up' : 'trend--down';
    const sign = diff > 0 ? '↑' : '↓';
    return `<span class="trend ${cls}">${sign} ${Math.abs(diff)}</span>`;
  }

  function showResults(data) {
    hideError();

    const prev = data.previous_audit || {};

    // URL
    resultUrl.textContent = data.url;

    // Status badge
    const statusCode = data.status_code;
    resultStatusBadge.textContent = `${statusCode}`;
    resultStatusBadge.className = 'results__status';
    if (statusCode >= 200 && statusCode < 300) {
      resultStatusBadge.classList.add('results__status--ok');
    } else if (statusCode >= 300 && statusCode < 400) {
      resultStatusBadge.classList.add('results__status--warn');
    } else {
      resultStatusBadge.classList.add('results__status--err');
    }

    // Metrics with trends
    resultStatus.innerHTML = `${statusCode} ${getTrendBadge(statusCode, prev.status_code, true)}`;
    resultTime.innerHTML = `${data.response_time_ms} ms ${getTrendBadge(data.response_time_ms, prev.response_ms, true)}`;
    resultTitle.textContent = data.title || '(no title found)';
    resultMeta.textContent = data.meta_description || '(no meta description found)';

    // H1 count with contextual color
    resultH1.innerHTML = `${data.h1_count} ${getTrendBadge(data.h1_count, prev.h1_count)}`;
    resultH1.className = 'results__value';
    if (data.h1_count === 1) {
      resultH1.classList.add('results__value--good');
    } else if (data.h1_count === 0 || data.h1_count > 1) {
      resultH1.classList.add('results__value--warn');
    }

    // Word count
    resultWords.innerHTML = `${data.word_count.toLocaleString()} ${getTrendBadge(data.word_count, prev.word_count)}`;

    // Images
    resultImages.innerHTML = `${data.total_images} ${getTrendBadge(data.total_images, prev.total_images)}`;

    // Missing alt — warn if any
    resultAlt.innerHTML = `${data.images_missing_alt} ${getTrendBadge(data.images_missing_alt, prev.images_missing_alt, true)}`;
    resultAlt.className = 'results__value';
    if (data.images_missing_alt > 0) {
      resultAlt.classList.add('results__value--warn');
    } else {
      resultAlt.classList.add('results__value--good');
    }
    
    // Social Preview
    if (data.og_image || data.title || data.meta_description) {
      socialSection.classList.add('social-preview-container--visible');
      try {
        socialDomain.textContent = new URL(data.url).hostname;
      } catch(e) {
        socialDomain.textContent = data.url;
      }
      socialTitle.textContent = data.title || data.url;
      socialDesc.textContent = data.meta_description || 'No description available for this page.';
      
      if (data.og_image) {
        socialImageContainer.style.display = 'flex';
        // Handle relative URLs for images
        let imgSrc = data.og_image;
        if (!imgSrc.startsWith('http')) {
            try { imgSrc = new URL(imgSrc, data.url).href; } catch(e){}
        }
        socialImage.src = imgSrc;
      } else {
        socialImageContainer.style.display = 'none';
      }
    } else {
      socialSection.classList.remove('social-preview-container--visible');
    }
    
    // Setup exports
    btnCsv.onclick = () => window.location.href = `/export/csv?url=${encodeURIComponent(data.url)}`;
    btnPdf.onclick = () => window.print();

    results.classList.add('results--visible');
  }

  // Form submission
  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    const url = urlInput.value.trim();
    if (!url) {
      showError('Please enter a URL to audit.');
      return;
    }

    hideError();
    setLoading(true);

    try {
      const response = await fetch('/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url }),
      });

      const body = await response.json();

      if (body.success) {
        showResults(body.data);
      } else {
        showError(body.error || 'Something went wrong. Please try again.');
      }
    } catch (err) {
      showError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  });

  // Auto-focus the input
  urlInput.focus();
})();
