// ─────────────────────────────────────────────────────────────
// Cross-device sync for the dashboard apps.
//
// Mirrors the apps' localStorage to Firestore so logging on one
// device shows up on every device. Sign in once per device; the
// session is remembered. The cloud copy is the source of truth —
// on a fresh device, sign in and it pulls your data down.
//
// Public Firebase web config (safe to ship in client code).
// ─────────────────────────────────────────────────────────────
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.16.0/firebase-app.js";
import {
  getAuth, onAuthStateChanged, signInWithEmailAndPassword, signOut,
  setPersistence, browserLocalPersistence
} from "https://www.gstatic.com/firebasejs/12.16.0/firebase-auth.js";
import {
  getFirestore, doc, onSnapshot, setDoc, serverTimestamp
} from "https://www.gstatic.com/firebasejs/12.16.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyA6Y6VW0Hzb7YUBC5qIr8blB6EVPMu-dl4",
  authDomain: "tom-dashboard-a06c3.firebaseapp.com",
  projectId: "tom-dashboard-a06c3",
  storageBucket: "tom-dashboard-a06c3.firebasestorage.app",
  messagingSenderId: "431395585463",
  appId: "1:431395585463:web:a77c0f1077e1ab2a8a3c32"
};

// Every localStorage key any of the apps uses.
const SYNC_KEYS = [
  'fuel-log-v1',          // Fuel — nutrition log
  'training-log-v1',      // Training log
  'meal-plan-v1',         // Meal planner — the week
  'meal-custom-v1',       // Meal planner — logged/custom meals
  'meal-shop-checked-v1'  // Shopping — ticked items
];
const REV_KEY = 'sync-rev';                       // last applied revision (per device, not synced)
const CLIENT_ID = Math.random().toString(36).slice(2) + Date.now().toString(36);

let auth, db, docRef, unsub = null;
let lastRev = parseInt(localStorage.getItem(REV_KEY) || '0', 10) || 0;
let applying = false;      // true while we write remote data locally (don't echo it back up)
let pushTimer = null;

boot();

function boot() {
  let app;
  try {
    app = initializeApp(firebaseConfig);
    auth = getAuth(app);
    db = getFirestore(app);
  } catch (e) {
    console.warn('[sync] init failed — running local-only', e);
    return; // app still works entirely from localStorage
  }
  setPersistence(auth, browserLocalPersistence).catch(function () {});
  patchLocalStorage();
  buildBar();
  onAuthStateChanged(auth, function (user) {
    if (user) { renderBar('on', user.email); startSync(user.uid); }
    else { if (unsub) { unsub(); unsub = null; } docRef = null; renderBar('off'); }
  });
}

// ── Firestore <-> localStorage ──
function startSync(uid) {
  docRef = doc(db, 'users', uid, 'state', 'v1');
  unsub = onSnapshot(docRef, function (snap) {
    if (!snap.exists()) { seed(); return; }
    const d = snap.data() || {};
    if (d.client === CLIENT_ID) {           // our own write echoing back
      lastRev = d.rev || lastRev;
      localStorage.setItem(REV_KEY, String(lastRev));
      return;
    }
    if ((d.rev || 0) > lastRev) {           // a newer copy from another device
      let changed = false;
      const remote = d.data || {};
      SYNC_KEYS.forEach(function (k) {
        const rv = (remote[k] !== undefined) ? remote[k] : null;
        if (rv !== null && rv !== localStorage.getItem(k)) {
          applying = true; localStorage.setItem(k, rv); applying = false;
          changed = true;
        }
      });
      lastRev = d.rev || 0;
      localStorage.setItem(REV_KEY, String(lastRev));
      if (changed) location.reload();       // simplest reliable way to re-render every app
    }
  }, function (err) {
    console.warn('[sync] snapshot error', err);
    renderBar('error', (err && err.code) || 'error');
  });
}

function currentData() {
  const data = {};
  SYNC_KEYS.forEach(function (k) {
    const v = localStorage.getItem(k);
    if (v !== null) data[k] = v;
  });
  return data;
}

function writeUp() {
  if (!docRef) return;
  const rev = (lastRev || 0) + 1;
  setDoc(docRef, { data: currentData(), rev: rev, client: CLIENT_ID, updatedAt: serverTimestamp() })
    .then(function () {
      lastRev = rev;
      localStorage.setItem(REV_KEY, String(rev));
      if (auth.currentUser) renderBar('on', auth.currentUser.email, true);
    })
    .catch(function (e) { console.warn('[sync] write failed', e); });
}

function seed() { writeUp(); }             // cloud was empty — push this device's data up

function schedulePush() {
  if (!docRef) return;
  clearTimeout(pushTimer);
  pushTimer = setTimeout(writeUp, 800);    // debounce bursts of taps into one write
}

// Catch every save the apps make, without changing their code.
function patchLocalStorage() {
  const orig = localStorage.setItem.bind(localStorage);
  localStorage.setItem = function (k, v) {
    orig(k, v);
    if (!applying && SYNC_KEYS.indexOf(k) !== -1) schedulePush();
  };
}

// ─────────────────────────────────────────────────────────────
// Minimal sync bar (fixed to the bottom of the screen)
// ─────────────────────────────────────────────────────────────
let bar;
function buildBar() {
  // spacer so the fixed bar never hides content
  const spacer = document.createElement('div');
  spacer.style.height = '54px';
  document.body.appendChild(spacer);

  bar = document.createElement('div');
  bar.style.cssText = [
    'position:fixed', 'bottom:0', 'left:50%', 'transform:translateX(-50%)',
    'width:100%', 'max-width:430px', 'box-sizing:border-box',
    'background:rgba(13,13,13,0.96)', 'border-top:1px solid #222',
    'font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif',
    'font-size:0.75rem', 'color:#666', 'padding:0.55rem 1rem',
    'z-index:9999', 'text-align:center', 'backdrop-filter:blur(6px)'
  ].join(';');
  document.body.appendChild(bar);
  renderBar('checking');
}

function el(tag, css, text) {
  const e = document.createElement(tag);
  if (css) e.style.cssText = css;
  if (text != null) e.textContent = text;
  return e;
}

const linkCss = 'color:#f59e0b;font-weight:600;cursor:pointer;-webkit-tap-highlight-color:transparent';
const inputCss = 'background:#0f0f0f;border:1px solid #222;border-radius:8px;color:#f0f0f0;font-family:inherit;font-size:16px;padding:0.45rem 0.55rem;width:100%;margin-bottom:0.4rem;box-sizing:border-box';
const btnCss = 'background:#f59e0b;color:#0d0d0d;border:none;border-radius:8px;font-family:inherit;font-weight:700;font-size:0.8rem;padding:0.5rem 0.9rem;cursor:pointer;-webkit-tap-highlight-color:transparent';

function renderBar(state, detail, flash) {
  if (!bar) return;
  bar.innerHTML = '';

  if (state === 'checking') { bar.appendChild(el('span', '', '☁︎ Sync…')); return; }

  if (state === 'off') {
    const wrap = el('span');
    wrap.appendChild(el('span', '', '☁︎ Sync is off — '));
    const a = el('span', linkCss, 'turn on sync');
    a.onclick = showSignIn;
    wrap.appendChild(a);
    bar.appendChild(wrap);
    return;
  }

  if (state === 'signin') { showSignInForm(detail); return; }

  if (state === 'on') {
    const wrap = el('span');
    wrap.appendChild(el('span', flash ? 'color:#22c55e' : '', (flash ? '☁︎ Saved · ' : '☁︎ Synced · ') + (detail || '')));
    wrap.appendChild(el('span', '', '  '));
    const out = el('span', 'color:#666;cursor:pointer;-webkit-tap-highlight-color:transparent;text-decoration:underline', 'sign out');
    out.onclick = function () { signOut(auth).catch(function () {}); };
    wrap.appendChild(out);
    bar.appendChild(wrap);
    return;
  }

  if (state === 'error') {
    bar.appendChild(el('span', 'color:#ef4444', '☁︎ Sync error (' + (detail || '') + ') — '));
    const a = el('span', linkCss, 'retry');
    a.onclick = showSignIn;
    bar.appendChild(a);
    return;
  }
}

function showSignIn() { renderBar('signin'); }

function showSignInForm(msg) {
  bar.innerHTML = '';
  const email = el('input', inputCss); email.type = 'email'; email.placeholder = 'Email';
  email.autocomplete = 'username';
  const pw = el('input', inputCss); pw.type = 'password'; pw.placeholder = 'Password';
  pw.autocomplete = 'current-password';
  const row = el('div', 'display:flex;gap:0.5rem;align-items:center;justify-content:center');
  const go = el('button', btnCss, 'Sign in');
  const cancel = el('span', 'color:#666;cursor:pointer;font-size:0.75rem', 'cancel');
  cancel.onclick = function () { renderBar('off'); };
  row.appendChild(go); row.appendChild(cancel);

  function submit() {
    go.disabled = true; go.textContent = '…';
    signInWithEmailAndPassword(auth, email.value.trim(), pw.value)
      .catch(function (e) {
        go.disabled = false; go.textContent = 'Sign in';
        showSignInForm(friendlyAuthError(e && e.code));
      });
  }
  go.onclick = submit;
  pw.onkeydown = function (ev) { if (ev.key === 'Enter') submit(); };

  bar.appendChild(email);
  bar.appendChild(pw);
  if (msg) bar.appendChild(el('div', 'color:#ef4444;font-size:0.7rem;margin-bottom:0.4rem', msg));
  bar.appendChild(row);
  email.focus();
}

function friendlyAuthError(code) {
  switch (code) {
    case 'auth/invalid-email': return 'That email doesn’t look right.';
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found': return 'Email or password not recognised.';
    case 'auth/too-many-requests': return 'Too many tries — wait a moment.';
    case 'auth/network-request-failed': return 'No connection — try again.';
    default: return code ? ('Sign-in failed (' + code + ').') : 'Sign-in failed.';
  }
}
