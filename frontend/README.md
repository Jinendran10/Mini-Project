# Poison Guard Frontend

React-based analytical dashboard and chatbot interface for the Poison Guard AI Defense System.

## Features

- **📊 Real-time Detection Dashboard**: Visualize JIE and RLOD detection scores
- **📈 Analytical Graphs**: Multiple chart types for data visualization
- **🤖 AI Assistant Chatbot**: Interactive interface for system queries and analysis
- **⚡ Real-time Updates**: Live score monitoring and trend analysis
- **📤 Export Functionality**: Download detection reports and visualizations

## Technology Stack

- **React 18.2**: UI framework
- **Vite**: Next-generation build tool
- **Tailwind CSS**: Utility-first styling
- **Chart.js**: Data visualization
- **Plotly.js**: Advanced interactive charts
- **Axios**: HTTP client
- **Lucide React**: Icon library
- **React Router v6**: Navigation

## Installation

```bash
cd frontend
npm install
```

## Running the Development Server

```bash
npm run dev
```

The application will start on `http://localhost:3000` with API proxy to `http://localhost:8000`.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Sidebar.jsx          # Navigation sidebar
│   │   ├── MetricCard.jsx       # KPI metric display
│   │   ├── Charts.jsx           # Chart components
│   │   └── ChatInterface.jsx    # Chat UI
│   ├── pages/
│   │   ├── Home.jsx             # Landing page
│   │   ├── Dashboard.jsx        # Analytics dashboard
│   │   └── Chatbot.jsx          # Chatbot page
│   ├── api/
│   │   └── client.js            # API client
│   ├── App.jsx                  # Main app component
│   ├── App.css                  # App styles
│   ├── index.css                # Global styles
│   └── main.jsx                 # Entry point
├── package.json
├── vite.config.js
├── tailwind.config.js
└── index.html
```

## API Integration

The frontend communicates with the backend API at `http://localhost:8000`:

### Detection Endpoints

```javascript
// JIE Detection
const result = await detectAPI.jieDetect(samples, targetSamples, 'async');

// RLOD Detection
const result = await detectAPI.rlodDetect(samples, cleanSamples, 'async');

// Combined Detection (60% JIE + 40% RLOD)
const result = await detectAPI.combinedDetect(samples, targetSamples, 'async');

// Get Job Status
const status = await detectAPI.getJobStatus(jobId);
```

### Chat Endpoints

```javascript
// Send message
const response = await chatAPI.sendMessage(message, conversationId);

// Get conversation history
const history = await chatAPI.getHistory(conversationId);

// Create new conversation
const conversation = await chatAPI.createConversation();
```

## Features Detail

### Dashboard Page
- **KPI Metrics**: Average scores, suspicious sample counts, poisoning rates
- **Detection Trends**: Line charts tracking scores over time
- **Score Distribution**: Pie chart showing clean/suspicious/poisoned splits
- **Method Comparison**: Radar chart comparing JIE vs RLOD vs Combined
- **Recent Detections**: Table of latest samples with scores and mitigation weights

### Chatbot Page
- **Intelligent Responses**: Context-aware answers about detection results
- **Message History**: Persistent conversation tracking
- **Copy Functionality**: Easy sharing of assistant responses
- **Real-time Typing**: Animated typing indicator

### Home Page
- **Feature Showcase**: Information about JIE and RLOD methods
- **System Capabilities**: Overview of core features
- **Performance Metrics**: Accuracy, FPR, speed statistics

## Configuration

### Environment Variables

Create `.env.local` in the frontend directory:

```
VITE_API_URL=http://localhost:8000
VITE_API_KEY=your-api-key
```

### Build

```bash
npm run build
```

Output will be in `dist/` directory.

### Preview

```bash
npm run preview
```

## Styling

The application uses Tailwind CSS with custom configuration:

- **Primary Color**: #2563eb (Blue)
- **Secondary Color**: #1e40af (Dark Blue)
- **Success Color**: #16a34a (Green)
- **Warning Color**: #ea580c (Orange)
- **Danger Color**: #dc2626 (Red)

## Contributing

1. Create feature branches for new functionality
2. Update components with TypeScript types as needed
3. Test responsive design on mobile/tablet
4. Follow component naming conventions

## Performance Optimization

- **Code Splitting**: Route-based splitting automatically handled by Vite
- **Image Optimization**: Use Lucide icons instead of image files
- **Lazy Loading**: Charts load data on demand
- **API Caching**: Implement with React Query for larger scale

## Troubleshooting

### API Connection Issues

If receiving CORS errors:
1. Ensure backend is running on `http://localhost:8000`
2. Check backend has CORS middleware configured
3. Verify API key is correctly set

### Chart Rendering Issues

1. Ensure chart data is properly formatted
2. Check browser console for JavaScript errors
3. Verify Chart.js is properly registered

### Performance Issues

1. Reduce the number of data points displayed
2. Implement pagination for large tables
3. Use React.memo for components with heavy rendering
