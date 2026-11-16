# SocialSpork mobile

Expo (React Native) app for the SocialSpork dashboard: **Stock-outs, Uptime, Reviews, Payouts (reconciliation)**.
It signs in at `POST /api/auth/mobile/login` and sends the returned token as `Authorization: Bearer ...`; the API applies
the same access rules as the website (a client sees only its own brands and outlets).

    npm install
    npm start            # then press i / a, or scan the QR code with Expo Go
    npm run web          # quick look in the browser

Point it at another server (for example Django on your Mac) with `EXPO_PUBLIC_API_URL=http://192.168.1.x:8000/api npm start`.
Type-check: `npx tsc --noEmit`.
