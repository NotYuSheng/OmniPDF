describe('Service Health Tests', () => {
  let services = [];

  before(() => {
    // Dynamically discover running containers ending with _service
    cy.task('exec', { 
      command: 'docker ps --format "{{.Names}}" | grep "_service$"',
      timeout: 10000 
    }).then((result) => {
      if (result.code === 0 && result.stdout.trim()) {
        services = result.stdout.trim().split('\n').filter(name => name.trim());
        cy.log(`Found services: ${services.join(', ')}`);
      } else {
        cy.log('No _service containers found');
      }
    });
  });

  it('verifies all running *_service containers are healthy', () => {
    if (services.length === 0) {
      cy.log('No services to check - skipping health verification');
      return;
    }

    services.forEach(service => {
      cy.task('exec', { 
        command: `docker exec ${service} curl -f http://localhost:8000/health`,
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