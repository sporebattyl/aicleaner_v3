
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  // Support Home Assistant ingress with relative base path
  base: './',
  plugins: [
    react(),
    visualizer({
      filename: './dist/bundle-analyzer.html',
      open: false, // Don't auto-open in HA addon environment
      gzipSize: true,
      brotliSize: true,
      template: 'treemap' // Use treemap for better visualization
    })
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false, // Disable sourcemaps for smaller production builds
    target: 'es2015', // Support older browsers in HA environment
    rollupOptions: {
      output: {
        // Enhanced manual chunking strategy for optimal loading
        manualChunks(id) {
          // Vendor libraries chunking - more granular for smaller chunks
          if (id.includes('node_modules')) {
            // React ecosystem
            if (id.includes('react/') || id.includes('react-dom/')) {
              return 'vendor-react'
            }
            // React Router
            if (id.includes('react-router')) {
              return 'vendor-router'
            }
            // Chart.js and visualization libraries  
            if (id.includes('chart.js') || id.includes('chartjs') || id.includes('react-chartjs')) {
              return 'vendor-charts'
            }
            // Bootstrap and UI libraries
            if (id.includes('bootstrap') || id.includes('react-bootstrap')) {
              return 'vendor-ui'
            }
            // Icons
            if (id.includes('react-icons')) {
              return 'vendor-icons'
            }
            // PDF generation libraries
            if (id.includes('jspdf') || id.includes('react-csv')) {
              return 'vendor-export'
            }
            // Date handling libraries
            if (id.includes('date-fns')) {
              return 'vendor-date'
            }
            // Prop types and utilities
            if (id.includes('prop-types') || id.includes('lodash')) {
              return 'vendor-utils'
            }
            // All other smaller vendor libraries
            return 'vendor-misc'
          }
          
          // App-specific chunking - component-based
          if (id.includes('src/components/config/') || id.includes('ConfigurationManager') || id.includes('UnifiedConfigurationPanel')) {
            return 'app-config'
          }
          if (id.includes('src/components/analytics') || id.includes('AnalyticsManager') || id.includes('MonitoringDashboard')) {
            return 'app-analytics'
          }
          if (id.includes('src/components/security') || id.includes('SecurityDashboard')) {
            return 'app-security'
          }
          if (id.includes('src/services/')) {
            return 'app-services'
          }
        },
        
        // Optimize chunk size limits
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    },
    
    // Increase chunk size warning limit for vendor chunks
    chunkSizeWarningLimit: 1000, // 1MB limit for chunks
    
    // Build optimization settings
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true
      }
    }
  }
})
