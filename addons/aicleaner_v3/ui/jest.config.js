export default {
  testEnvironment: 'jest-environment-jsdom',
  extensionsToTreatAsEsm: ['.jsx'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx}',
    '!src/main.jsx',
    '!src/**/*.test.{js,jsx}',
    '!src/**/*.spec.{js,jsx}'
  ],
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx}',
    '<rootDir>/src/**/*.{test,spec}.{js,jsx}'
  ],
  transform: {
    '^.+\\.(js|jsx)$': ['babel-jest', { presets: [['@babel/preset-env', { targets: { node: 'current' }, modules: 'auto' }], '@babel/preset-react'] }]
  },
  transformIgnorePatterns: [
    'node_modules/(?!(@testing-library/.*)/)'
  ]
};