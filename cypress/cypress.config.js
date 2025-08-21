const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:8501',
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: false,
    setupNodeEvents(on) {
      // Enable secure command execution
      on('task', {
        dockerExec: ({ containerName, args = [], timeout = 10000 }) => {
          const { execFile } = require('child_process');
          return new Promise((resolve) => {
            // Validate container name to prevent injection
            if (!/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(containerName)) {
              resolve({
                code: 1,
                stdout: '',
                stderr: 'Invalid container name format',
              });
              return;
            }
            
            const dockerArgs = ['exec', containerName, ...args];
            execFile('docker', dockerArgs, { timeout, encoding: 'utf8' }, (error, stdout, stderr) => {
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
        },
        dockerPs: ({ filters = [], timeout = 10000 }) => {
          const { execFile } = require('child_process');
          return new Promise((resolve) => {
            const args = ['ps', '--format', '{{.Names}}'];
            filters.forEach(filter => {
              args.push('--filter', filter);
            });
            
            execFile('docker', args, { timeout, encoding: 'utf8' }, (error, stdout, stderr) => {
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
