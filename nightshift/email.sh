#!/usr/bin/env bash
# email.sh — email the human. Usage: email.sh "Subject" "Body"
#
# Transport: Gmail SMTP via curl, authenticated with an app password.
# Reads from nightshift/.env (gitignored — this repo is public, never
# commit credentials):
#   GMAIL_USER          sending Gmail address
#   GMAIL_APP_PASSWORD  app password from myaccount.google.com/apppasswords
#   EMAIL_TO            recipient address
#
# History: Web3Forms, ntfy.sh email, and FormSubmit all block anonymous
# server-side sending. Authenticated SMTP is the honest, reliable path.
# Best-effort: never fails the caller.

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$DIR/.env" ] && . "$DIR/.env"

if [ -z "${GMAIL_USER:-}" ] || [ -z "${GMAIL_APP_PASSWORD:-}" ] || [ -z "${EMAIL_TO:-}" ]; then
  echo "email.sh: GMAIL_USER / GMAIL_APP_PASSWORD / EMAIL_TO not set in nightshift/.env — skipping email" >&2
  exit 0
fi

SUBJECT="${1:-Night Shift}"
BODY="${2:-(no message provided)}"

if resp=$(curl -fsS -m 30 --url 'smtps://smtp.gmail.com:465' --ssl-reqd \
    --mail-from "$GMAIL_USER" \
    --mail-rcpt "$EMAIL_TO" \
    --user "$GMAIL_USER:$GMAIL_APP_PASSWORD" \
    -T - <<MAIL 2>&1
From: TokenBurnerGround Night Shift <$GMAIL_USER>
To: $EMAIL_TO
Subject: $SUBJECT
Content-Type: text/plain; charset=UTF-8

$BODY
MAIL
  ); then
  echo "email.sh: sent — $SUBJECT"
else
  echo "email.sh: send failed — $resp" >&2
fi
exit 0
