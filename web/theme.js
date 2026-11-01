// Apply the saved preference before first paint. No network or account is needed.
try {
  const theme = localStorage.getItem('ascend-theme');
  if (theme === 'light' || theme === 'dark') document.documentElement.dataset.theme = theme;
} catch { /* System color preference remains available when storage is blocked. */ }
try {
  if (localStorage.getItem('ascend-motion') === 'off') document.documentElement.dataset.motion = 'off';
} catch { /* The device preference is still respected. */ }
