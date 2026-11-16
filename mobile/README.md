# SocialSpork mobile

Expo (React Native) app for the SocialSpork dashboard: **Stock-outs, Uptime, Reviews, Payouts (reconciliation)**.
It signs in at `POST /api/auth/mobile/login` and sends the returned token as `Authorization: Bearer ...`; the API applies
the same access rules as the website (a client sees only its own brands and outlets).

    npm install
    npm start            # then press i / a, or scan the QR code with Expo Go
    npm run web          # quick look in the browser

Point it at another server (for example Django on your Mac) with `EXPO_PUBLIC_API_URL=http://192.168.1.x:8000/api npm start`.
Type-check: `npx tsc --noEmit`.

## Giving it to a few people (no app stores)

You need a free Expo account (`npx eas-cli login`) and, once, `npx eas-cli init` in this folder.

**Android (APK, free):**

    npx eas-cli build --platform android --profile preview

When it finishes you get a link and QR code. Open it on the phone, download the APK, allow "install unknown apps", install.

**iPhone (TestFlight, needs an Apple Developer account, $99 a year):**

    npx eas-cli build --platform ios --profile production
    npx eas-cli submit --platform ios

Then in App Store Connect > TestFlight, add testers by email (up to 100 internal testers need no review). They install the
TestFlight app and accept the invite. Without a paid Apple account, iPhones can only run it through Expo Go or the simulator.

Updating: a new build for each release. Bump nothing by hand; `autoIncrement` raises the build number.

## On a phone through a link (no install)

The web build is served by the website at **https://app.socialspork.com/m**. Open it on the phone, sign in with your dashboard
login, then "Add to Home Screen" (Safari Share menu, or Chrome menu) to get an icon and full-screen mode.

After changing the app, rebuild that copy and push it:

    npm run build:web      # writes ../frontend/m
    git add ../frontend/m && git commit && git push
