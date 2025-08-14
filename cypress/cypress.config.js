const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:8501',
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: false,
    setupNodeEvents(on) {
      // Enable cy.exec() command for running shell commands
      on('task', {
        exec: ({ command, timeout = 10000 }) => {
          const { execSync } = require('child_process');
          try {
            const result = execSync(command, { 
              encoding: 'utf8', 
              timeout,
              stdio: 'pipe'
            });
            return { code: 0, stdout: result, stderr: '' };
          } catch (error) {
            return { 
              code: error.status || 1, 
              stdout: error.stdout || '', 
              stderr: error.stderr || error.message 
            };
          }
        }
      });
    },
  },
});
