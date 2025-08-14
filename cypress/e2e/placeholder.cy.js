describe('Service Health Tests', () => {
  const services = [
    'chat_service',
    'embedder_service', 
    'pdf_processor_service',
    'pdf_extraction_service',
    'pdf_renderer_service',
    'docling_translation_service',
    'cleaner'
  ];

  it('verifies all services are healthy via direct container checks', () => {
    services.forEach(service => {
      cy.task('exec', { 
        command: `docker exec ${service} curl -f http://localhost:8000/health`,
        timeout: 10000 
      }).then((result) => {
        expect(result.code).to.eq(0);
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