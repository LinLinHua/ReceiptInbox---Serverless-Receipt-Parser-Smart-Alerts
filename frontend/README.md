# Receipt Processing Frontend

React-based web application for receipt management with ML-powered categorization.

## Setup

```bash
npm install
npm start
```

Open http://localhost:3000

## Configuration

Update `src/constants.js` with your API Gateway URL:
```javascript
export const BASE_URL = "https://your-api-gateway-url";
```

## Build for Production

```bash
npm run build
```

## Features

- User authentication
- Receipt upload (drag-and-drop)
- Real-time processing status
- Analytics dashboard
- Anomaly alerts
- Email notifications

## Tech Stack

- React 18
- Ant Design
- Recharts
- Axios
- React Router
