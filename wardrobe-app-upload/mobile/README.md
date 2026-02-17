# Mobile Packaging (Capacitor)

This folder wraps the existing `frontend/` into native Android/iOS projects.

## 1) Prerequisites

- Node.js LTS
- npm
- Android Studio + Android SDK + JDK 17
- Xcode (for iOS, macOS only)

## 2) Install Dependencies

```bash
cd mobile
npm install
```

## 3) Create Native Projects (first time)

```bash
npm run cap:add:android
npm run cap:add:ios
```

Notes:
- `cap:add:ios` must be run on macOS.
- If your backend API is remote, set `frontend/assets/runtime-config.js` before sync.

## 4) Sync Web Assets + Open IDE

```bash
npm run cap:android
npm run cap:ios
```

## 5) Build for Tablets

- Android Tablet: use Android Studio to build `APK`/`AAB`.
- iPad: use Xcode archive flow to create `IPA`.

## API Base URL

- Web local mode default: `/api`
- Mobile mode recommended: `https://your-domain.com/api`

Edit this file:

- `frontend/assets/runtime-config.js`

Then run:

```bash
npm run cap:sync
```
