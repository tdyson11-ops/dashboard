// ─────────────────────────────────────────────────────────────
// Cloud Functions: keep WHOOP data live on the dashboard.
//
//   whoopScheduled  — runs at 07:00 Europe/London, every day. Cloud Scheduler
//                     fires on time (unlike GitHub's free cron), so the
//                     morning recovery score is up before you look at it.
//   whoopRefreshNow — callable from the dashboard's ↻ button, so you can pull
//                     today's numbers on demand instead of waiting.
//
// The refresh token lives in Firestore at system/whoop_token, which the
// security rules make unreadable to every client — only the Admin SDK here
// can touch it. The numbers go to system/whoop_latest, which any signed-in
// user can read.
// ─────────────────────────────────────────────────────────────
'use strict';

const { onSchedule } = require('firebase-functions/v2/scheduler');
const { onCall, HttpsError } = require('firebase-functions/v2/https');
const { defineSecret } = require('firebase-functions/params');
const logger = require('firebase-functions/logger');
const { initializeApp } = require('firebase-admin/app');
const { getFirestore, FieldValue } = require('firebase-admin/firestore');

const { refreshWhoop } = require('./whoop');

initializeApp();
const db = getFirestore();

const TOKEN_DOC = 'system/whoop_token';
const DATA_DOC = 'system/whoop_latest';

const WHOOP_CLIENT_ID = defineSecret('WHOOP_CLIENT_ID');
const WHOOP_CLIENT_SECRET = defineSecret('WHOOP_CLIENT_SECRET');
const WHOOP_REFRESH_TOKEN = defineSecret('WHOOP_REFRESH_TOKEN');

const SECRETS = [WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET, WHOOP_REFRESH_TOKEN];

function deps() {
  return {
    fetchImpl: fetch,                       // Node 20 global
    clientId: WHOOP_CLIENT_ID.value(),
    clientSecret: WHOOP_CLIENT_SECRET.value(),
    seedToken: WHOOP_REFRESH_TOKEN.value(),
    log: logger,

    async readToken() {
      const snap = await db.doc(TOKEN_DOC).get();
      return snap.exists ? (snap.data().refresh_token || null) : null;
    },
    async writeToken(token) {
      await db.doc(TOKEN_DOC).set({
        refresh_token: token,
        rotated_at: FieldValue.serverTimestamp()
      });
    },
    async readPrevious() {
      const snap = await db.doc(DATA_DOC).get();
      return snap.exists ? snap.data() : null;
    },
    async writeData(whoop) {
      await db.doc(DATA_DOC).set(whoop);
    }
  };
}

exports.whoopScheduled = onSchedule(
  {
    schedule: '0 7 * * *',
    timeZone: 'Europe/London',
    secrets: SECRETS,
    retryCount: 3,
    region: 'europe-west2'
  },
  async () => {
    await refreshWhoop(deps());
  }
);

exports.whoopRefreshNow = onCall(
  { secrets: SECRETS, region: 'europe-west2' },
  async (request) => {
    if (!request.auth) {
      throw new HttpsError('unauthenticated', 'Sign in to refresh WHOOP data.');
    }
    try {
      return await refreshWhoop(deps());
    } catch (err) {
      logger.error('[whoop] on-demand refresh failed', err);
      throw new HttpsError('internal', err.message || 'WHOOP refresh failed.');
    }
  }
);
