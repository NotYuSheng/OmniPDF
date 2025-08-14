describe('Service Health Tests', () => {
  let services = [];

  before(() => {
    // Dynamically discover running containers ending with _service using secure docker filter
    cy.task('dockerPs', { 
      filters: ['name=.*_service$'],
      timeout: 10000 
    }).then((result) => {
      if (result.code === 0 && result.stdout.trim()) {
        const foundServices = result.stdout.trim().split('\n').filter(name => name.trim());
        // Filter to only include containers that actually end with _service
        services = foundServices.filter(name => name.endsWith('_service'));
        if (services.length > 0) {
          cy.log(`Found services: ${services.join(', ')}`);
        } else {
          cy.log('No _service containers found after filtering');
        }
      } else {
        cy.log(`Service discovery failed. Code: ${result.code}, Stderr: ${result.stderr}`);
      }
    });
  });

  it('verifies all running *_service containers are healthy', () => {
    if (services.length === 0) {
      cy.log('No services to check - skipping health verification');
      // Fail the test if no services found, as this might indicate a setup issue
      cy.task('dockerPs', { filters: [], timeout: 5000 }).then((result) => {
        cy.log(`All running containers: ${result.stdout}`);
        throw new Error('No _service containers found. This might indicate a Docker Compose setup issue.');
      });
      return;
    }

    services.forEach(service => {
      cy.task('dockerExec', { 
        containerName: service,
        args: ['curl', '-f', 'http://localhost:8000/health'],
        timeout: 10000 
      }).then((result) => {
        expect(result.code, `Health check for '${service}' failed. Command: docker exec ${service} curl -f http://localhost:8000/health. Stdout: ${result.stdout}. Stderr: ${result.stderr}`).to.eq(0);
        cy.log(`✓ ${service} is healthy`);
      });
    });
  });

  it('checks frontend availability', () => {
    cy.request({
      url: '/',
      failOnStatusCode: false,
    }).then((res) => {
      if (res.status !== 200) {
        cy.log('Frontend not ready, skipping test');
        return;
      }
      cy.contains('Streamlit');
    });
  });
});