module.exports = {
  transformIgnorePatterns: [
    "/node_modules/(?!axios)/"
  ],
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^react-router-dom$': '<rootDir>/node_modules/react-router-dom'
  },
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
};