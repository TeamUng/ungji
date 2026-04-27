# Ungji Frontend

React + Vite + TypeScript + Tailwind CSS 기반 AI 학습코치 프론트엔드입니다.

## 로컬 실행

```bash
cd frontend
npm install
npm run dev
```

## 검증

```bash
npm run typecheck
npm run build
```

## Vercel 배포

Vercel 프로젝트 생성 시 Root Directory를 `frontend`로 지정합니다.

- Framework Preset: Vite
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: `dist`

브랜치는 먼저 `ay-front`로 Preview 배포를 확인하고, 이후 `dev`에 머지되면 Vercel Production 또는 dev 기준 Preview로 전환합니다.
