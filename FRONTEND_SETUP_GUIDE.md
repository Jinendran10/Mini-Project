# Poison Guard UI - Setup & Deployment Guide

Complete guide for setting up, running, and deploying the Poison Guard frontend application.

## Quick Start

### Prerequisites
- Node.js 16.x or higher
- npm or yarn package manager

### Installation & Running

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Application opens at http://localhost:3000
```

The dev server automatically proxies API calls to `http://localhost:8000` (backend).

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js              # Axios API client with all endpoints
│   ├── components/
│   │   ├── Sidebar.jsx            # Navigation sidebar (4 pages)
│   │   ├── MetricCard.jsx         # KPI metric display component
│   │   ├── Charts.jsx             # Chart components (Line, Bar, Pie, Radar)
│   │   └── ChatInterface.jsx      # Chatbot UI with message history
│   ├── pages/
│   │   ├── Home.jsx               # Landing page with features
│   │   ├── Dashboard.jsx          # Main analytics dashboard
│   │   ├── Chatbot.jsx            # Chatbot page wrapper
│   │   └── Settings.jsx           # Configuration settings
│   ├── App.jsx                    # Main app routing
│   ├── App.css                    # App-level styles
│   ├── index.css                  # Global styles (from Tailwind)
│   └── main.jsx                   # React entry point
├── public/                        # Static assets
├── index.html                     # HTML template
├── vite.config.js                 # Vite configuration
├── tailwind.config.js             # Tailwind CSS config
├── package.json                   # Dependencies & scripts
├── .gitignore                     # Git ignore rules
└── README.md                      # Frontend documentation
```

## Features Overview

### 🏠 Home Page (`/`)
- System introduction and feature showcase
- JIE vs RLOD method comparison
- Combined defense capabilities
- System features and metrics
- Quick links to dashboard and chatbot

### 📊 Dashboard Page (`/dashboard`)
- **KPI Metrics**: 6 key performance indicators
  - Average JIE/RLOD/Combined scores
  - Suspicious sample counts
  - Poisoning rate percentage
- **Analytics Graphs**:
  - Detection scores over time (line chart)
  - Combined score trend analysis
  - Score distribution (pie chart)
  - Method comparison (radar chart)
- **Detection Summary**: Table of recent samples with scores and mitigation weights
- **Controls**: Refresh and export functionality

### 🤖 Chatbot Page (`/chatbot`)
- Real-time AI assistant interface
- Message history with timestamps
- Intelligent context-aware responses
- Copy-to-clipboard functionality
- Sample queries about detection results
- Typing indicator during processing

### ⚙️ Settings Page (`/settings`)
- **API Configuration**:
  - API URL configuration
  - API key management
- **Detection Settings**:
  - JIE/RLOD weight sliders (0-100%)
  - Suspicion threshold
  - Poisoning threshold
  - Real-time weight sum validation
- **UI Preferences**:
  - Auto-refresh interval
  - Dashboard auto-refresh toggle
  - Dark mode (coming soon)
  - Notifications toggle
- **Persistent Storage**: Settings saved to localStorage

### 🧭 Sidebar Navigation
- Active page highlighting
- Responsive mobile menu
- Collapsible navigation drawer
- Logo and branding

## Technology Stack

| Technology | Purpose | Version |
|---|---|---|
| **React** | UI Framework | 18.2.0 |
| **Vite** | Build Tool | 4.x |
| **React Router** | Navigation | 6.x |
| **Tailwind CSS** | Styling | 3.x |
| **Chart.js** | Data Visualization | 4.x |
| **react-chartjs-2** | React Chart.js wrapper | 5.x |
| **Plotly.js** | Advanced Charts | 2.x |
| **Axios** | HTTP Client | 1.x |
| **Lucide React** | Icons | 0.x |
| **date-fns** | Date Utilities | 2.x |

## API Integration

### Base Configuration

The API client is configured in `src/api/client.js`:

```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || localStorage.getItem('apiKey') || '';
```

### Environment Variables

Create `.env.local` in the frontend directory:

```
VITE_API_URL=http://localhost:8000
VITE_API_KEY=your-api-key-here
```

### Available Endpoints

#### Detection API

```javascript
// JIE Detection
await detectAPI.jieDetect(samples, targetSamples, 'async');

// RLOD Detection
await detectAPI.rlodDetect(samples, cleanSamples, 'async');

// Combined Detection (60% JIE + 40% RLOD)
await detectAPI.combinedDetect(samples, targetSamples, 'async');

// Job Status
await detectAPI.getJobStatus(jobId);

// System Health
await detectAPI.health();
await detectAPI.ready();
await detectAPI.metrics();
```

#### Chat API

```javascript
// Send Message
await chatAPI.sendMessage(message, conversationId);

// Get History
await chatAPI.getHistory(conversationId);

// Create Conversation
await chatAPI.createConversation();
```

## Styling

### Tailwind CSS

The application uses Tailwind CSS with custom configuration:

- **Primary**: #2563eb (Blue)
- **Secondary**: #1e40af (Dark Blue)
- **Success**: #16a34a (Green)
- **Warning**: #ea580c (Orange)
- **Danger**: #dc2626 (Red)

### Component Classes

Common utility classes defined in `src/index.css`:

- `.card` - Card container
- `.button` - Button styling
- `.input-field` - Form input
- `.metric-card` - KPI metric card
- `.chart-container` - Chart wrapper
- `.chat-messages` - Chat message list
- `.score-badge` - Score status badge

## Development

### Available Scripts

```bash
# Development server
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Format code
npm run format
```

### Development Workflow

1. **Start Backend**: Ensure backend is running on `http://localhost:8000`
2. **Start Frontend**: Run `npm run dev`
3. **Test Endpoints**: Use browser DevTools to verify API calls
4. **Check Console**: Monitor console for API logs and errors

### Debugging Tips

1. **API Issues**:
   - Check browser network tab for requests
   - Verify CORS headers from backend
   - Confirm API key is correctly set

2. **Chart Issues**:
   - Inspect Chart.js data format
   - Verify all required data points exist
   - Check console for missing dependencies

3. **Performance**:
   - Use React DevTools to identify re-renders
   - Monitor API response times
   - Check for memory leaks in chat component

## Building for Production

### Build Command

```bash
npm run build
```

Output is generated in `dist/` directory.

### Deployment Options

#### 1. Static Hosting (GitHub Pages, Netlify, Vercel)

```bash
# Build
npm run build

# Deploy dist/ folder to static hosting
```

#### 2. Docker

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Build and run:

```bash
docker build -t poison-guard-frontend .
docker run -p 3000:80 poison-guard-frontend
```

#### 3. Node.js Server

```bash
npm install express
npm run build

# Create server.js
```

```javascript
import express from 'express';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();

app.use(express.static(join(__dirname, 'dist')));
app.get('*', (req, res) => {
  res.sendFile(join(__dirname, 'dist', 'index.html'));
});

app.listen(3000, () => {
  console.log('Server running on http://localhost:3000');
});
```

Run: `node server.js`

## Performance Optimization

### Current Optimizations

- **Code Splitting**: Automatic with Vite
- **Tree Shaking**: Unused code removed in build
- **Lazy Loading**: Components split by route
- **Image Optimization**: Using SVG icons (Lucide)

### Recommended Future Optimizations

1. **API Response Caching**: Implement React Query
2. **State Management**: Add Redux for complex state
3. **Pagination**: Add to detection table for large datasets
4. **Virtual Scrolling**: For long message histories
5. **Web Workers**: Offload heavy computations

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **CORS Errors** | Ensure backend has CORS middleware configured |
| **API Connection Failed** | Check backend is running on :8000, verify API_URL in env |
| **Charts Not Rendering** | Verify chart data format, check Chart.js registration |
| **Styles Not Loading** | Run `npm run dev` to restart Vite, check Tailwind config |
| **Sidebar Not Responsive** | Clear browser cache, hard refresh (Ctrl+Shift+R) |

### Debug Mode

Enable verbose logging:

```javascript
// In src/api/client.js - uncomment interceptors
// In src/App.jsx - add console statements
```

## Contributing

### Code Style

- Use functional components with hooks
- Follow React naming conventions
- Comment complex logic
- Keep components focused and single-responsibility

### Adding New Features

1. Create component in `src/components/` or `src/pages/`
2. Update routing in `App.jsx`
3. Add navigation link in `Sidebar.jsx` if needed
4. Test with mock data before connecting to API
5. Add error handling for API calls

## Additional Resources

- [React Docs](https://react.dev)
- [Vite Docs](https://vitejs.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Chart.js](https://www.chartjs.org)
- [Axios Docs](https://axios-http.com)
- [React Router](https://reactrouter.com)

## License

This project is part of the Poison Guard AI Defense System.

## Support

For issues or questions:
1. Check existing documentation
2. Review console errors
3. Check API responses
4. Verify backend is running
5. Contact development team
