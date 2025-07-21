/**
 * Lazy-loaded chart components for better performance
 * Phase 5A: UI Performance Optimization - Component-based lazy loading
 */

import React, { lazy, Suspense } from 'react';
import { Spinner } from 'react-bootstrap';

// Lazy load heavy chart components
const AnalyticsManager = lazy(() => import('./AnalyticsManager').then(module => ({ default: module.AnalyticsManager })));

// Lightweight loading component for charts
const ChartLoadingSpinner = ({ height = '400px' }) => (
  <div 
    className="d-flex justify-content-center align-items-center border rounded bg-light" 
    style={{ minHeight: height }}
  >
    <div className="text-center">
      <Spinner animation="border" role="status" variant="primary" />
      <div className="mt-2 text-muted">Loading chart...</div>
    </div>
  </div>
);

// Lazy Analytics Manager wrapper
export const LazyAnalyticsManager = (props) => (
  <Suspense fallback={<ChartLoadingSpinner height="600px" />}>
    <AnalyticsManager {...props} />
  </Suspense>
);

// Reserved for future performance metrics component

// Generic lazy chart wrapper for dynamic components
export const LazyChartWrapper = ({ 
  componentPath, 
  componentName, 
  fallbackHeight = '300px',
  ...props 
}) => {
  const LazyComponent = lazy(() => 
    import(componentPath).then(module => ({ 
      default: module[componentName] || module.default 
    }))
  );

  return (
    <Suspense fallback={<ChartLoadingSpinner height={fallbackHeight} />}>
      <LazyComponent {...props} />
    </Suspense>
  );
};

export default LazyAnalyticsManager;