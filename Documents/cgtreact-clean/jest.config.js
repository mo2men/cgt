module.exports = {
  transformIgnorePatterns: [
    '/node_modules/(?!(axios)/)'
  ],
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
};