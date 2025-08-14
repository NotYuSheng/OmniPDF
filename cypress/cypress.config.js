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
          const { exec } = require('child_process');
          return new Promise((resolve) => {
            exec(command, { timeout, encoding: 'utf8' }, (error, stdout, stderr) => {
              if (error) {
                resolve({
                  code: error.code || 1,
                  stdout: stdout || '',
                  stderr: stderr || error.message,
                });
                return;
              }
              resolve({ code: 0, stdout, stderr });
            });
          });
        }
      });
    },
  },
});
