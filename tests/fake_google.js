// Minimal Google Identity Services token mock. Drive browsing itself is
// exercised through mocked REST responses in test_google_drive_auth.py.
(function () {
  window.__googleLog = window.__googleLog || [];
  window.__googleTokenResponse = window.__googleTokenResponse || {
    access_token: 'test-access-token', expires_in: 3600,
    scope: 'https://www.googleapis.com/auth/drive.readonly'
  };

  window.google = window.google || {};
  google.accounts = google.accounts || {};
  google.accounts.oauth2 = {
    initTokenClient: function (config) {
      window.__lastTokenConfig = config;
      window.__googleLog.push('init-token:' + config.scope);
      return {
        requestAccessToken: function (options) {
          window.__googleLog.push('request-token:' + ((options && options.prompt) || ''));
          setTimeout(function () {
            if (window.__googleTokenError) config.error_callback(window.__googleTokenError);
            else config.callback(window.__googleTokenResponse);
          }, window.__googleTokenDelay || 0);
        }
      };
    },
    hasGrantedAllScopes: function () { return window.__googleGrant !== false; },
    revoke: function (_token, callback) {
      window.__googleLog.push('revoke');
      if (callback) callback({ successful: true });
    }
  };
})();
