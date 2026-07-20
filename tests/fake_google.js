// Minimal Google Identity Services + Drive Picker mock. It deliberately models
// only the browser APIs used by app.html and records calls in __googleLog.
(function () {
  window.__googleLog = window.__googleLog || [];
  window.__googleTokenResponse = window.__googleTokenResponse || {
    access_token: 'test-access-token', expires_in: 3600,
    scope: 'https://www.googleapis.com/auth/drive.file'
  };
  window.__googlePickerDoc = window.__googlePickerDoc || {
    id: 'privateDriveVideo01', name: 'Private Lecture.mp4',
    mimeType: 'video/mp4', sizeBytes: 1048576,
    url: 'https://drive.google.com/file/d/privateDriveVideo01/view'
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

  window.gapi = window.gapi || {
    load: function (name, options) {
      window.__googleLog.push('gapi-load:' + name);
      setTimeout(function () {
        if (window.__pickerLoadError && options.onerror) options.onerror();
        else if (typeof options === 'function') options();
        else options.callback();
      }, 0);
    }
  };

  google.picker = google.picker || {};
  google.picker.Action = { PICKED: 'picked', CANCEL: 'cancel' };
  google.picker.ViewId = { DOCS: 'docs' };
  google.picker.DocsViewMode = { LIST: 'list' };
  google.picker.DocsView = function () {
    this.setIncludeFolders = function () { return this; };
    this.setSelectFolderEnabled = function () { return this; };
    this.setMimeTypes = function (types) { window.__pickerMimeTypes = types; return this; };
    this.setMode = function () { return this; };
  };
  google.picker.PickerBuilder = function () {
    const state = {};
    this.addView = function () { return this; };
    this.setOAuthToken = function (v) { state.token = v; return this; };
    this.setDeveloperKey = function (v) { state.apiKey = v; return this; };
    this.setAppId = function (v) { state.appId = v; return this; };
    this.setOrigin = function (v) { state.origin = v; return this; };
    this.setCallback = function (v) { state.callback = v; return this; };
    this.build = function () {
      window.__lastPickerState = state;
      return {
        setVisible: function (visible) {
          window.__googleLog.push('picker-visible:' + visible);
          if (visible && window.__pickerAuto !== false) {
            setTimeout(function () {
              const action = window.__pickerAction || 'picked';
              state.callback({ action: action, docs: action === 'picked' ? [window.__googlePickerDoc] : [] });
            }, window.__pickerDelay || 0);
          }
        }
      };
    };
  };
})();
